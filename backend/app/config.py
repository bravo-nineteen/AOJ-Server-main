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


# API auth settings.
# Enable AOJ_AUTH_ENABLED=true and set AOJ_API_KEYS as comma-separated key:role pairs.
# Example: AOJ_API_KEYS="viewer-key:viewer,operator-key:operator,admin-key:admin"
AOJ_AUTH_ENABLED = os.getenv("AOJ_AUTH_ENABLED", "false").strip().lower()
AOJ_API_KEYS = os.getenv("AOJ_API_KEYS", "").strip()


# Update Center hardening settings.
# Optional HMAC shared secret used for placeholder package metadata verification.
UPDATE_CENTER_SHARED_SECRET = os.getenv("UPDATE_CENTER_SHARED_SECRET", "").strip()
