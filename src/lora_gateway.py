"""USB serial gateway client for Heltec WiFi LoRa 32 V3 gateway firmware.

Protocol summary:
- PING -> PONG
- STATUS -> STATUS:READY
- SEND:<message> -> TX_OK:<message> or TX_FAIL:<error_code>
- RESET_RADIO -> RADIO_RESET_OK or RADIO_RESET_FAIL:<error_code>
- Async receive indications from gateway: RX:<message>
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import serial
from serial import SerialException
from serial.tools import list_ports


DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 0.25


@dataclass
class GatewayConfig:
    port: Optional[str] = None
    baudrate: int = DEFAULT_BAUDRATE
    timeout: float = DEFAULT_TIMEOUT


class HeltecLoRaGateway:
    """Client for Heltec V3 USB serial LoRa gateway firmware."""

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self._serial: Optional[serial.Serial] = None

    # ------------------------------------------------------------------
    # Logging and safety helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [LoRaGateway] {message}")

    def _close_on_error(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

    def _is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Port discovery and connection
    # ------------------------------------------------------------------

    @staticmethod
    def _candidate_score(port_info: list_ports.ListPortInfo) -> int:
        """Rank likely Heltec/ESP32-S3 serial devices higher."""

        text = " ".join(
            [
                port_info.device or "",
                port_info.description or "",
                port_info.manufacturer or "",
                port_info.hwid or "",
            ]
        ).lower()

        score = 0

        keywords = [
            "heltec",
            "esp32",
            "esp32-s3",
            "cp210",
            "usb jtag",
            "ch340",
            "wch",
            "silicon labs",
        ]
        for kw in keywords:
            if kw in text:
                score += 1

        # Common vendor IDs seen with ESP32 dev boards.
        if "vid:pid=10c4:ea60" in text:
            score += 3  # CP210x
        if "vid:pid=303a:" in text:
            score += 3  # Espressif USB/JTAG serial
        if "vid:pid=1a86:7523" in text:
            score += 2  # CH340

        return score

    def _detect_port(self) -> Optional[str]:
        ports = list(list_ports.comports())
        if not ports:
            self._log("No serial ports detected.")
            return None

        scored = sorted(ports, key=self._candidate_score, reverse=True)
        best = scored[0]

        if self._candidate_score(best) <= 0:
            self._log("No obvious Heltec/ESP32 serial match found.")
            self._log(
                "Available ports: "
                + ", ".join(f"{p.device} ({p.description})" for p in ports)
            )
            return None

        self._log(f"Auto-detected serial port: {best.device} ({best.description})")
        return best.device

    def connect(self, port: Optional[str] = None) -> bool:
        """Open serial connection to the gateway.

        Args:
            port: Optional explicit serial port (for example '/dev/ttyACM0').

        Returns:
            True when connected, otherwise False.
        """

        if self._is_open():
            self._log(f"Already connected on {self._serial.port}")
            return True

        target_port = port or self.config.port or self._detect_port()
        if not target_port:
            self._log("Connect failed: no serial port selected.")
            return False

        try:
            self._serial = serial.Serial(
                port=target_port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
                write_timeout=2.0,
            )
            self._log(f"Connected to {target_port} at {self.config.baudrate} baud")

            # Clear stale startup text or previous command responses.
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            return True
        except (SerialException, OSError) as exc:
            self._log(f"Connect failed on {target_port}: {exc}")
            self._close_on_error()
            return False

    def disconnect(self) -> None:
        if self._is_open():
            port = self._serial.port
            self._serial.close()
            self._log(f"Disconnected from {port}")
        self._serial = None

    # ------------------------------------------------------------------
    # Protocol I/O
    # ------------------------------------------------------------------

    def _write_command(self, command: str) -> bool:
        if not self._is_open():
            self._log("Write aborted: not connected.")
            return False

        try:
            payload = (command + "\n").encode("utf-8")
            self._serial.write(payload)
            self._serial.flush()
            return True
        except (SerialException, OSError) as exc:
            self._log(f"Serial write failed: {exc}")
            self._close_on_error()
            return False

    def _read_line(self) -> Optional[str]:
        if not self._is_open():
            return None

        try:
            raw = self._serial.readline()
            if not raw:
                return None
            return raw.decode("utf-8", errors="replace").strip()
        except (SerialException, OSError) as exc:
            self._log(f"Serial read failed: {exc}")
            self._close_on_error()
            return None

    def _request_response(
        self,
        command: str,
        accepted_prefixes: List[str],
        timeout: float = 2.0,
    ) -> Optional[str]:
        if not self._write_command(command):
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._read_line()
            if line is None:
                continue

            # RX lines are asynchronous; leave those for read_messages().
            if line.startswith("RX:"):
                self._log(f"Async RX observed during request: {line}")
                continue

            for prefix in accepted_prefixes:
                if line.startswith(prefix):
                    return line

            self._log(f"Ignoring unexpected response line: {line}")

        self._log(f"Timeout waiting for response to command '{command}'")
        return None

    # ------------------------------------------------------------------
    # Public API requested by project task
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        line = self._request_response("PING", ["PONG"])
        ok = line == "PONG"
        self._log("Ping OK" if ok else "Ping failed")
        return ok

    def status(self) -> Optional[str]:
        line = self._request_response("STATUS", ["STATUS:"])
        if line:
            self._log(f"Status response: {line}")
        return line

    def reset_radio(self) -> bool:
        line = self._request_response(
            "RESET_RADIO",
            ["RADIO_RESET_OK", "RADIO_RESET_FAIL:"],
            timeout=3.0,
        )
        if line is None:
            return False
        if line.startswith("RADIO_RESET_OK"):
            self._log("Radio reset successful")
            return True

        self._log(f"Radio reset failed: {line}")
        return False

    def send_message(self, message: str) -> bool:
        line = self._request_response(
            f"SEND:{message}",
            ["TX_OK:", "TX_FAIL:"],
            timeout=3.0,
        )
        if line is None:
            return False
        if line.startswith("TX_OK:"):
            self._log(f"Transmit success: {line}")
            return True

        self._log(f"Transmit failed: {line}")
        return False

    def read_messages(self) -> List[str]:
        """Read any pending RX:<message> lines.

        Returns:
            List of LoRa payload strings (without 'RX:' prefix).
        """

        messages: List[str] = []
        if not self._is_open():
            return messages

        while True:
            line = self._read_line()
            if line is None:
                break

            if line.startswith("RX:"):
                payload = line[3:]
                messages.append(payload)
                self._log(f"Received LoRa payload: {payload}")
            else:
                self._log(f"Non-RX line while reading messages: {line}")

        return messages


# ----------------------------------------------------------------------
# Optional module-level convenience wrappers
# ----------------------------------------------------------------------

_default_gateway = HeltecLoRaGateway()


def connect(port: Optional[str] = None) -> bool:
    return _default_gateway.connect(port=port)


def send_message(message: str) -> bool:
    return _default_gateway.send_message(message)


def read_messages() -> List[str]:
    return _default_gateway.read_messages()


def ping() -> bool:
    return _default_gateway.ping()


def status() -> Optional[str]:
    return _default_gateway.status()


def reset_radio() -> bool:
    return _default_gateway.reset_radio()
