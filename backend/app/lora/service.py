"""LoRa messaging service – mock transport with ACK/retry handling.

Message format:  AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC

TODO: Replace mock transport with a real SX1262 driver once hardware is wired.
      Initialize SPI bus, GPIO chip-select, and radio parameters
      (frequency, spreading factor, bandwidth, coding rate) in LoRaService.__init__.
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class QueuedCommand:
    device_id: str
    command: str
    value: str
    message_id: str
    payload: str
    retries: int = 0
    last_sent_at: float = 0.0


class LoRaService:
    """LoRa messaging with mock transport and ACK/retry handling."""

    def __init__(
        self,
        ack_timeout_seconds: float = 3.0,
        max_retries: int = 3,
        mock_mode: bool = True,
    ) -> None:
        self.ack_timeout_seconds = ack_timeout_seconds
        self.max_retries = max_retries
        self.mock_mode = mock_mode

        self._command_queue: queue.Queue[QueuedCommand] = queue.Queue()
        self._incoming_queue: queue.Queue[str] = queue.Queue()
        self._pending_acks: dict[str, QueuedCommand] = {}
        self._device_status: dict[str, dict[str, Any]] = {}

        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None
        self._running = False

        # TODO: Initialize SX1262 driver, SPI bus, and GPIO pins here.
        # TODO: Configure LoRa radio params (frequency, spreading factor, BW, CR).

    @property
    def device_status(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {key: value.copy() for key, value in self._device_status.items()}

    @property
    def pending_ack_count(self) -> int:
        with self._lock:
            return len(self._pending_acks)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

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
            self._process_ack_timeouts()
            time.sleep(0.1)

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

        if self.mock_mode:
            # In mock mode: loop message back and auto-ACK.
            self._incoming_queue.put(queued.payload)
            ack_payload = f"AOJ|{queued.device_id}|ACK|OK|{queued.message_id}"
            ack_crc = self.calculate_crc(ack_payload)
            self._incoming_queue.put(f"{ack_payload}|{ack_crc}")

        # TODO: Replace mock block above with SX1262 send() call.

    def _process_ack_timeouts(self) -> None:
        now = time.time()
        resend: list[QueuedCommand] = []
        failed: list[QueuedCommand] = []

        with self._lock:
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
            # TODO: Emit failure event through WebSocket/logging integration.
            _ = queued


# Singleton instance – started by main.py on_startup, not at import time.
lora_service = LoRaService()
