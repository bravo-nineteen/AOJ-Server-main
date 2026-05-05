"""Application-level settings and constants."""

import os

APP_TITLE = "AOJ Command OS API"
APP_VERSION = "0.1.0"

CORS_ORIGIN_REGEX = (
    r"https?://(localhost|127\.0\.0\.1"
    r"|192\.168\.\d+\.\d+"
    r"|10\.\d+\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)"
    r"(:\d+)?"
)


# LoRa transport settings.
# LORA_MODE options: mock | serial-single
# Raspberry Pi 5 deployment: set LORA_MODE=serial-single, LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_MODE = os.getenv("LORA_MODE", "mock").strip().lower()
LORA_SERIAL_BAUDRATE = int(os.getenv("LORA_SERIAL_BAUDRATE", "115200"))
LORA_SERIAL_PORT = os.getenv("LORA_SERIAL_PORT", "/dev/ttyUSB0").strip()
# Legacy alias kept for backward-compat with older env files.
_LORA_TX_SERIAL_PORT = os.getenv("LORA_TX_SERIAL_PORT", "").strip()
if _LORA_TX_SERIAL_PORT and not os.getenv("LORA_SERIAL_PORT"):
    LORA_SERIAL_PORT = _LORA_TX_SERIAL_PORT
