"""LoRa messaging service with hardware abstraction.

Message format: AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC

Supported modes:
- mock: in-memory loopback (default, no hardware required)
- rpi_spi: Raspberry Pi 5 + Waveshare Core1262 HF SX1262 (SPI interface)
- usb_serial: USB LoRa modules (Windows/Linux/macOS, COM or /dev/ttyUSB*)
- test: Simulated responses for automated testing

Set env vars for production:
    # Raspberry Pi with Waveshare Core1262 SPI
    LORA_MODE=rpi_spi
    LORA_RPI_SPI_BUS=1
    LORA_RPI_SPI_DEVICE=1
    LORA_RPI_RST_PIN=17
    LORA_RPI_DIO1_PIN=22

    # Windows/Linux/macOS USB LoRa module
    LORA_MODE=usb_serial
    LORA_USB_PORT=COM3          # or /dev/ttyUSB0 on Linux
    LORA_USB_BAUDRATE=9600
    LORA_USB_TIMEOUT=1.0

    # Testing
    LORA_MODE=test
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Optional
import logging

from app import config
from app.lora.device_drivers import create_lora_device, LoRaDevice


@dataclass
class QueuedCommand:
    device_id: str
    command: str
    value: str
    message_id: str
    payload: str
    retries: int = 0
    last_sent_at: float = 0.0


@dataclass
class LoRaIncomingFrame:
    device_id: str
    command: str
    value: str
    message_id: str
    raw_frame: str


class LoRaService:
    """LoRa messaging service with transport abstraction and ACK/retry handling."""

    def __init__(
        self,
        ack_timeout_seconds: float = 3.0,
        max_retries: int = 3,
        mock_mode: bool = True,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self.ack_timeout_seconds = ack_timeout_seconds
        self.max_retries = max_retries
        self.mock_mode = mock_mode or config.LORA_MODE == "mock"

        self._command_queue: queue.Queue[QueuedCommand] = queue.Queue()
        self._incoming_queue: queue.Queue[str] = queue.Queue()
        self._pending_acks: dict[str, QueuedCommand] = {}
        self._device_status: dict[str, dict[str, Any]] = {}
        self._recent_inbound_by_device: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=100)
        )

        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._transport: LoRaTransport = self._build_transport()

        self._configured_mode = config.LORA_MODE.lower().strip()
        self._transport_started = False
        self._tx_count = 0
        self._rx_count = 0
        self._last_tx_at = 0.0
        self._last_rx_at = 0.0
        self._last_error: str | None = None
        
        # ACK callback: called when an ACK is successfully processed.
        # Receives (device_id: str, ack_value: str, message_id: str) -> None
        self._on_ack_callback: Optional[Callable[[str, str, str], None]] = None
        self._on_incoming_callback: Optional[Callable[[LoRaIncomingFrame], None]] = None
        self._on_timeout_callback: Optional[Callable[[str, str, int], None]] = None

    def _build_transport(self) -> LoRaDevice:
        """Factory method to build appropriate LoRa device based on config."""
        mode = config.LORA_MODE.lower().strip()

        # Build config dict from environment variables
        device_config: dict[str, Any] = {}

        if mode == "rpi_spi":
            self.mock_mode = False
            device_config = {
                "spi_bus": int(config.LORA_RPI_SPI_BUS),
                "spi_device": int(config.LORA_RPI_SPI_DEVICE),
                "rst_pin": int(config.LORA_RPI_RST_PIN),
                "dio1_pin": int(config.LORA_RPI_DIO1_PIN),
                "spi_speed_hz": int(config.LORA_RPI_SPI_SPEED_HZ),
            }

        elif mode == "usb_serial":
            self.mock_mode = False
            device_config = {
                "port": config.LORA_USB_PORT,
                "baudrate": int(config.LORA_USB_BAUDRATE),
                "timeout": float(config.LORA_USB_TIMEOUT),
            }

        elif mode == "test":
            # Test mode for automated testing
            self.mock_mode = False

        # Create device using factory
        device = create_lora_device(mode, self.calculate_crc, device_config)
        self._logger.info(f"Built LoRa device: {mode} -> {type(device).__name__}")
        return device

    @property
    def device_status(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {key: value.copy() for key, value in self._device_status.items()}

    @property
    def pending_ack_count(self) -> int:
        with self._lock:
            return len(self._pending_acks)

    def set_on_ack_callback(self, callback: Optional[Callable[[str, str, str], None]]) -> None:
        """Register a callback to be invoked when an ACK is successfully processed.
        
        Args:
            callback: Function with signature (device_id: str, ack_value: str, message_id: str) -> None
                     or None to unregister.
        """
        with self._lock:
            self._on_ack_callback = callback

    def set_on_incoming_callback(self, callback: Optional[Callable[[LoRaIncomingFrame], None]]) -> None:
        """Register callback for valid non-ACK incoming frames."""
        with self._lock:
            self._on_incoming_callback = callback

    def set_on_timeout_callback(self, callback: Optional[Callable[[str, str, int], None]]) -> None:
        """Register callback for ACK timeout after retries are exhausted.

        Signature: (device_id: str, message_id: str, retries: int) -> None
        """
        with self._lock:
            self._on_timeout_callback = callback

    def diagnostics(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            return {
                "mode": self._configured_mode,
                "transport_started": self._transport_started,
                "serial_port": config.LORA_SERIAL_PORT,
                "serial_baudrate": config.LORA_SERIAL_BAUDRATE,
                "pending_ack": len(self._pending_acks),
                "tx_count": self._tx_count,
                "rx_count": self._rx_count,
                "last_tx_at": self._last_tx_at or None,
                "last_rx_at": self._last_rx_at or None,
                "alive": (now - self._last_rx_at) < 60 if self._last_rx_at else False,
                "last_error": self._last_error,
            }

    def recent_inbound_frames(self, device_id: str | None = None, limit: int = 25) -> dict[str, list[dict[str, Any]]]:
        limit = max(1, min(limit, 200))
        with self._lock:
            if device_id:
                items = list(self._recent_inbound_by_device.get(device_id, []))[-limit:]
                return {device_id: items}

            return {
                did: list(frames)[-limit:]
                for did, frames in self._recent_inbound_by_device.items()
            }

    def device_summary(self) -> list[dict[str, Any]]:
        """Return one summary row per known device: last seen command, value, and age."""
        now = time.time()
        with self._lock:
            result: list[dict[str, Any]] = []
            for device_id, status in self._device_status.items():
                last_seen = status.get("last_seen") or status.get("last_ack_at")
                age_seconds = round(now - last_seen, 1) if last_seen else None
                result.append(
                    {
                        "device_id": device_id,
                        "state": status.get("state"),
                        "last_command": status.get("last_incoming_command"),
                        "last_value": status.get("last_incoming_value"),
                        "last_seen": last_seen,
                        "age_seconds": age_seconds,
                    }
                )
        result.sort(key=lambda r: r["age_seconds"] if r["age_seconds"] is not None else float("inf"))
        return result

    def start(self) -> None:
        if self._running:
            return

        try:
            self._transport.start()
            self._transport_started = True
        except Exception as exc:
            self._last_error = str(exc)
            raise

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="lora-worker")
        self._worker_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        self._transport.stop()
        with self._lock:
            self._transport_started = False

    def send_command(self, device_id: str, command: str, value: str = "") -> str:
        message_id = uuid.uuid4().hex[:10].upper()
        payload_wo_crc = f"AOJ|{device_id}|{command}|{value}|{message_id}"
        crc = self.calculate_crc(payload_wo_crc)
        payload = f"{payload_wo_crc}|{crc}"

        queued = QueuedCommand(
            device_id=device_id,
            command=command,
            value=value,
            message_id=message_id,
            payload=payload,
        )
        self._command_queue.put(queued)

        with self._lock:
            self._device_status.setdefault(device_id, {})
            self._device_status[device_id].update(
                {
                    "last_command": command,
                    "last_message_id": message_id,
                    "last_enqueued_at": time.time(),
                    "state": "queued",
                }
            )

        return message_id

    def receive_message(self) -> str | None:
        """Read one incoming raw message frame if available."""
        try:
            return self._incoming_queue.get_nowait()
        except queue.Empty:
            return None

    def handle_ack(self, raw_message: str) -> bool:
        """Parse ACK message and clear pending retry state.

        Expected ACK payload:  AOJ|DEVICE_ID|ACK|VALUE|MESSAGE_ID|CRC
        """
        parts = raw_message.strip().split("|")
        if len(parts) != 6:
            return False

        header, device_id, command, value, message_id, rx_crc = parts
        if header != "AOJ" or command != "ACK":
            return False

        payload_wo_crc = "|".join(parts[:-1])
        if self.calculate_crc(payload_wo_crc) != rx_crc:
            return False

        callback: Optional[Callable[[str, str, str], None]] = None
        with self._lock:
            pending = self._pending_acks.pop(message_id, None)
            self._device_status.setdefault(device_id, {})
            self._device_status[device_id].update(
                {
                    "state": "acknowledged",
                    "ack_value": value,
                    "last_seen": time.time(),
                    "last_message_id": message_id,
                    "last_ack_at": time.time(),
                }
            )
            callback = self._on_ack_callback

            self._recent_inbound_by_device[device_id].append(
                {
                    "received_at": time.time(),
                    "command": command,
                    "value": value,
                    "message_id": message_id,
                    "raw_frame": raw_message,
                }
            )

        # Invoke callback outside the lock to avoid deadlocks.
        if callback is not None and pending is not None:
            try:
                callback(device_id, value, message_id)
            except Exception:
                self._logger.exception("ACK callback failed for device_id=%s", device_id)

        return pending is not None

    def request_device_status(self, device_id: str) -> str:
        return self.send_command(device_id, "STATUS_REQUEST", "")

    def broadcast_message(self, command: str, value: str = "") -> list[str]:
        """Queue the same command for all known devices."""
        with self._lock:
            device_ids = list(self._device_status.keys())

        message_ids: list[str] = []
        for device_id in device_ids:
            message_ids.append(self.send_command(device_id, command, value))
        return message_ids

    def calculate_crc(self, payload: str) -> str:
        """XOR checksum for message integrity."""
        checksum = 0
        for ch in payload.encode("utf-8"):
            checksum ^= ch
        return f"{checksum:02X}"

    def _worker_loop(self) -> None:
        while self._running:
            self._flush_command_queue()
            self._poll_incoming_transport()
            self._drain_incoming_queue()
            self._process_ack_timeouts()
            time.sleep(0.05)

    def _poll_incoming_transport(self) -> None:
        try:
            frames = self._transport.poll()
        except Exception as exc:
            with self._lock:
                self._last_error = f"poll_failed:{exc}"
            self._logger.exception("LoRa transport poll failed")
            return

        for frame in frames:
            with self._lock:
                self._rx_count += 1
                self._last_rx_at = time.time()
            self._incoming_queue.put(frame)

    def _drain_incoming_queue(self) -> None:
        while True:
            raw = self.receive_message()
            if raw is None:
                return
            self._process_incoming(raw)

    def _process_incoming(self, raw_message: str) -> None:
        parts = raw_message.strip().split("|")
        if len(parts) != 6:
            return

        header, device_id, command, value, message_id, rx_crc = parts
        if header != "AOJ":
            return

        payload_wo_crc = "|".join(parts[:-1])
        if self.calculate_crc(payload_wo_crc) != rx_crc:
            return

        if command == "ACK":
            self.handle_ack(raw_message)
            return

        callback: Optional[Callable[[LoRaIncomingFrame], None]] = None

        # Generic inbound frame update (STATUS/DEFUSED/EXPLODED/RESPAWN/etc).
        with self._lock:
            self._device_status.setdefault(device_id, {})
            self._device_status[device_id].update(
                {
                    "last_seen": time.time(),
                    "last_message_id": message_id,
                    "last_incoming_command": command,
                    "last_incoming_value": value,
                    "last_incoming_frame": raw_message,
                }
            )

            self._recent_inbound_by_device[device_id].append(
                {
                    "received_at": time.time(),
                    "command": command,
                    "value": value,
                    "message_id": message_id,
                    "raw_frame": raw_message,
                }
            )

            if command == "STATUS":
                status_parts = value.split(":")
                if status_parts:
                    self._device_status[device_id]["state"] = status_parts[0]

            callback = self._on_incoming_callback

        if callback is not None:
            try:
                callback(
                    LoRaIncomingFrame(
                        device_id=device_id,
                        command=command,
                        value=value,
                        message_id=message_id,
                        raw_frame=raw_message,
                    )
                )
            except Exception:
                self._logger.exception("Incoming frame callback failed for device_id=%s", device_id)

    def _flush_command_queue(self) -> None:
        while True:
            try:
                queued = self._command_queue.get_nowait()
            except queue.Empty:
                return
            self._transmit(queued)

    def _transmit(self, queued: QueuedCommand) -> None:
        queued.last_sent_at = time.time()

        with self._lock:
            self._pending_acks[queued.message_id] = queued
            self._device_status.setdefault(queued.device_id, {})
            self._device_status[queued.device_id].update(
                {
                    "state": "awaiting_ack",
                    "last_sent_at": queued.last_sent_at,
                    "last_payload": queued.payload,
                    "retries": queued.retries,
                }
            )

        try:
            self._transport.send(queued.payload)
            with self._lock:
                self._tx_count += 1
                self._last_tx_at = time.time()
        except Exception as exc:
            with self._lock:
                self._last_error = f"send_failed:{exc}"
            self._logger.exception("LoRa transport send failed for message_id=%s", queued.message_id)

    def _process_ack_timeouts(self) -> None:
        now = time.time()
        resend: list[QueuedCommand] = []
        failed: list[QueuedCommand] = []
        timeout_callback: Optional[Callable[[str, str, int], None]] = None

        with self._lock:
            timeout_callback = self._on_timeout_callback
            for queued in list(self._pending_acks.values()):
                elapsed = now - queued.last_sent_at
                if elapsed < self.ack_timeout_seconds:
                    continue

                if queued.retries >= self.max_retries:
                    failed.append(queued)
                    self._pending_acks.pop(queued.message_id, None)
                    self._device_status.setdefault(queued.device_id, {})
                    self._device_status[queued.device_id].update(
                        {
                            "state": "ack_timeout",
                            "last_message_id": queued.message_id,
                            "failed_at": now,
                        }
                    )
                else:
                    queued.retries += 1
                    resend.append(queued)
                    self._pending_acks.pop(queued.message_id, None)

        for queued in resend:
            self._command_queue.put(queued)

        for queued in failed:
            if timeout_callback is not None:
                try:
                    timeout_callback(queued.device_id, queued.message_id, queued.retries)
                except Exception:
                    self._logger.exception(
                        "Timeout callback failed for device_id=%s", queued.device_id
                    )


# Singleton instance – started by main.py on_startup, not at import time.
lora_service = LoRaService()
