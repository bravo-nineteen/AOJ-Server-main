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
# LORA_MODE options: mock | serial-single | serial-dual
LORA_MODE = os.getenv("LORA_MODE", "mock").strip().lower()
LORA_SERIAL_BAUDRATE = int(os.getenv("LORA_SERIAL_BAUDRATE", "115200"))
LORA_TX_SERIAL_PORT = os.getenv("LORA_TX_SERIAL_PORT", "/dev/ttyUSB0").strip()
LORA_RX_SERIAL_PORT = os.getenv("LORA_RX_SERIAL_PORT", "/dev/ttyUSB1").strip()
LORA_FALLBACK_TO_SINGLE = os.getenv("LORA_FALLBACK_TO_SINGLE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LORA_SINGLE_FALLBACK_PORT = os.getenv("LORA_SINGLE_FALLBACK_PORT", "").strip()
