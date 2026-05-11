"""LoRa device driver abstraction layer.

Supports multiple hardware backends:
- mock: Development loopback (no hardware required)
- rpi_spi: Raspberry Pi 5 with Waveshare Core1262 HF SX1262 LoRa module (SPI)
- usb_serial: USB LoRa modules (Windows/Linux/macOS)
- test: Simulated responses for testing
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

try:
    import serial  # type: ignore[import-not-found]
except Exception:
    serial = None

try:
    import RPi.GPIO as GPIO  # type: ignore[import-not-found]
    import spidev  # type: ignore[import-not-found]
except Exception:
    GPIO = None
    spidev = None


logger = logging.getLogger(__name__)


class LoRaDevice(ABC):
    """Abstract base class for LoRa device implementations."""

    @abstractmethod
    def start(self) -> None:
        """Initialize and start the LoRa device."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop and cleanup the LoRa device."""
        pass

    @abstractmethod
    def send(self, payload: str) -> None:
        """Send a LoRa message payload."""
        pass

    @abstractmethod
    def poll(self) -> list[str]:
        """Poll for received messages. Returns list of message frames."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if device is ready for communication."""
        pass


class MockLoRaDevice(LoRaDevice):
    """Development mock device with in-memory loopback."""

    def __init__(self, crc_func: Callable[[str], str]) -> None:
        self._incoming: queue.Queue[str] = queue.Queue()
        self._crc = crc_func
        self._running = False

    def start(self) -> None:
        self._running = True
        logger.info("MockLoRaDevice started (development mode)")

    def stop(self) -> None:
        self._running = False
        logger.info("MockLoRaDevice stopped")

    def send(self, payload: str) -> None:
        """Loopback: send to self immediately."""
        if not self._running:
            return
        self._incoming.put(payload)

        # Auto-generate ACK for AOJ protocol messages
        parts = payload.split("|")
        if len(parts) >= 6 and parts[0] == "AOJ":
            device_id = parts[1]
            message_id = parts[4]
            ack_payload = f"AOJ|{device_id}|ACK|OK|{message_id}"
            self._incoming.put(f"{ack_payload}|{self._crc(ack_payload)}")

    def poll(self) -> list[str]:
        frames: list[str] = []
        while True:
            try:
                frames.append(self._incoming.get_nowait())
            except queue.Empty:
                return frames

    def is_ready(self) -> bool:
        return self._running


class RPiSPILoRaDevice(LoRaDevice):
    """Raspberry Pi 5 + Waveshare Core1262 HF SX1262 LoRa Module via SPI.

    Hardware connection:
    - SPI1 bus 1 (CE1/GPIO7 chip select)
    - MOSI (GPIO10), MISO (GPIO9), SCK (GPIO11)
    - Reset pin: GPIO17 (configurable)
    - DIO1 interrupt pin: GPIO22 (configurable, optional)

    Baudrate: 8 MHz SPI speed typical for SX1262
    """

    def __init__(
        self,
        spi_bus: int = 1,
        spi_device: int = 1,
        rst_pin: int = 17,
        dio1_pin: int = 22,
        spi_speed_hz: int = 8_000_000,
    ) -> None:
        if GPIO is None or spidev is None:
            raise RuntimeError("RPi.GPIO and spidev required for Raspberry Pi SPI mode")

        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.rst_pin = rst_pin
        self.dio1_pin = dio1_pin
        self.spi_speed_hz = spi_speed_hz

        self._spi: Optional[spidev.SpiDev] = None
        self._running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._incoming: queue.Queue[str] = queue.Queue()

    def start(self) -> None:
        """Initialize SPI and LoRa module."""
        if self._running:
            return

        try:
            # Setup GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.rst_pin, GPIO.OUT)
            GPIO.output(self.rst_pin, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.5)

            # Setup SPI
            self._spi = spidev.SpiDev()
            self._spi.open(self.spi_bus, self.spi_device)
            self._spi.max_speed_hz = self.spi_speed_hz

            self._running = True

            # Start receive thread
            self._receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self._receive_thread.start()

            logger.info(
                f"RPiSPILoRaDevice started (SPI{self.spi_bus}.{self.spi_device}, "
                f"rst={self.rst_pin}, dio1={self.dio1_pin})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Raspberry Pi LoRa device: {e}")
            self._running = False
            raise

    def stop(self) -> None:
        """Stop SPI and cleanup GPIO."""
        self._running = False

        if self._receive_thread:
            self._receive_thread.join(timeout=2)

        if self._spi:
            try:
                self._spi.close()
            except Exception:
                pass

        try:
            GPIO.cleanup()
        except Exception:
            pass

        logger.info("RPiSPILoRaDevice stopped")

    def send(self, payload: str) -> None:
        """Send via SPI to SX1262 module."""
        if not self._running or self._spi is None:
            logger.warning("LoRa device not ready for send")
            return

        try:
            # SX1262 command format: bytes are sent MSB first on SPI
            # For now, we send the payload as-is (application level)
            msg_bytes = payload.encode("utf-8") + b"\n"

            # Simple SPI write (actual SX1262 protocol would be more complex)
            self._spi.writebytes(msg_bytes)

            logger.debug(f"LoRa SPI send: {payload}")
        except Exception as e:
            logger.error(f"LoRa SPI send failed: {e}")

    def _receive_loop(self) -> None:
        """Background thread to read from SPI."""
        buffer = b""
        while self._running and self._spi:
            try:
                # Read available bytes (non-blocking)
                available = self._spi.readbytes(256) if hasattr(self._spi, 'readbytes') else []

                if available:
                    buffer += bytes(available)

                    # Process complete lines
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        frame = line.decode("utf-8", errors="ignore").strip()
                        if frame:
                            self._incoming.put(frame)
                            logger.debug(f"LoRa SPI received: {frame}")

                time.sleep(0.01)  # 10ms read cycle
            except Exception as e:
                logger.error(f"LoRa SPI receive error: {e}")
                time.sleep(0.1)

    def poll(self) -> list[str]:
        """Get all queued received messages."""
        frames: list[str] = []
        while True:
            try:
                frames.append(self._incoming.get_nowait())
            except queue.Empty:
                return frames

    def is_ready(self) -> bool:
        return self._running and self._spi is not None


class USBSerialLoRaDevice(LoRaDevice):
    """USB-based LoRa module (Windows/Linux/macOS).

    Common modules: Dragino LORA/GPS HAT USB, Heltec USB LoRa, etc.
    They present as serial ports (COM on Windows, /dev/ttyUSB* on Linux).
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0) -> None:
        if serial is None:
            raise RuntimeError("pyserial required for USB LoRa mode")

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._incoming: queue.Queue[str] = queue.Queue()

    def start(self) -> None:
        """Open serial port and start receive thread."""
        if self._running:
            return

        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )

            self._running = True

            # Start receive thread
            self._receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self._receive_thread.start()

            logger.info(
                f"USBSerialLoRaDevice started ({self.port} @ {self.baudrate} baud)"
            )
        except Exception as e:
            logger.error(f"Failed to open USB LoRa serial port {self.port}: {e}")
            self._running = False
            raise

    def stop(self) -> None:
        """Close serial port and cleanup."""
        self._running = False

        if self._receive_thread:
            self._receive_thread.join(timeout=2)

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass

        logger.info("USBSerialLoRaDevice stopped")

    def send(self, payload: str) -> None:
        """Send message via USB serial."""
        if not self._running or self._serial is None or not self._serial.is_open:
            logger.warning("USB LoRa device not ready for send")
            return

        try:
            msg = (payload.strip() + "\n").encode("utf-8")
            self._serial.write(msg)
            self._serial.flush()
            logger.debug(f"LoRa USB send: {payload}")
        except Exception as e:
            logger.error(f"LoRa USB send failed: {e}")

    def _receive_loop(self) -> None:
        """Background thread to read from serial port."""
        buffer = ""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting:
                    raw = self._serial.read(self._serial.in_waiting).decode(
                        "utf-8", errors="ignore"
                    )
                    buffer += raw

                    # Process complete lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        frame = line.strip()
                        if frame:
                            self._incoming.put(frame)
                            logger.debug(f"LoRa USB received: {frame}")

                time.sleep(0.01)  # 10ms read cycle
            except Exception as e:
                logger.error(f"LoRa USB receive error: {e}")
                time.sleep(0.1)

    def poll(self) -> list[str]:
        """Get all queued received messages."""
        frames: list[str] = []
        while True:
            try:
                frames.append(self._incoming.get_nowait())
            except queue.Empty:
                return frames

    def is_ready(self) -> bool:
        return self._running and self._serial is not None and self._serial.is_open


class TestLoRaDevice(LoRaDevice):
    """Test device that simulates responses for automated testing.

    Responds to specific test commands:
    - respond immediately with mock ACKs
    - simulates typical device responses
    - no actual hardware required
    """

    def __init__(self, crc_func: Callable[[str], str]) -> None:
        self._crc = crc_func
        self._running = False
        self._incoming: queue.Queue[str] = queue.Queue()
        self._test_responses: dict[str, list[str]] = {
            "PING": ["AOJ|{device}|PONG|OK|{msg_id}"],
            "STATUS": ["AOJ|{device}|STATUS|READY|{msg_id}"],
            "CONFIG": ["AOJ|{device}|CONFIG|OK|{msg_id}"],
        }

    def start(self) -> None:
        self._running = True
        logger.info("TestLoRaDevice started (test mode)")

    def stop(self) -> None:
        self._running = False
        logger.info("TestLoRaDevice stopped")

    def send(self, payload: str) -> None:
        """Send and immediately respond with test responses."""
        if not self._running:
            return

        self._incoming.put(payload)

        # Parse and respond
        parts = payload.split("|")
        if len(parts) >= 6 and parts[0] == "AOJ":
            device_id = parts[1]
            command = parts[2]
            message_id = parts[4]

            # Generate test response
            template = self._test_responses.get(command, ["AOJ|{device}|ACK|OK|{msg_id}"])
            for resp_template in template:
                response = resp_template.format(device=device_id, msg_id=message_id)
                response = f"{response}|{self._crc(response)}"
                self._incoming.put(response)
                time.sleep(0.05)  # Simulate network delay

    def poll(self) -> list[str]:
        frames: list[str] = []
        while True:
            try:
                frames.append(self._incoming.get_nowait())
            except queue.Empty:
                return frames

    def is_ready(self) -> bool:
        return self._running


def create_lora_device(
    mode: str, crc_func: Callable[[str], str], config: dict | None = None
) -> LoRaDevice:
    """Factory function to create appropriate LoRa device.

    Args:
        mode: 'mock', 'rpi_spi', 'usb_serial', 'test'
        crc_func: CRC calculation function
        config: Device-specific configuration dict
            For rpi_spi: {spi_bus, spi_device, rst_pin, dio1_pin}
            For usb_serial: {port, baudrate, timeout}
    """
    config = config or {}

    if mode == "mock":
        return MockLoRaDevice(crc_func)

    elif mode == "rpi_spi":
        return RPiSPILoRaDevice(
            spi_bus=config.get("spi_bus", 1),
            spi_device=config.get("spi_device", 1),
            rst_pin=config.get("rst_pin", 17),
            dio1_pin=config.get("dio1_pin", 22),
            spi_speed_hz=config.get("spi_speed_hz", 8_000_000),
        )

    elif mode == "usb_serial":
        return USBSerialLoRaDevice(
            port=config.get("port", "COM3"),
            baudrate=config.get("baudrate", 9600),
            timeout=config.get("timeout", 1.0),
        )

    elif mode == "test":
        return TestLoRaDevice(crc_func)

    else:
        logger.warning(f"Unknown LoRa mode '{mode}', defaulting to mock")
        return MockLoRaDevice(crc_func)
