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


# LoRa hardware configuration
# Supported modes:
#   - mock: In-memory loopback (development/CI, no hardware needed)
#   - rpi_spi: Raspberry Pi 5 + Waveshare Core1262 HF SX1262 via SPI
#   - usb_serial: USB LoRa modules (Windows/Linux/macOS via serial port)
#   - test: Simulated responses for automated testing

LORA_MODE = os.getenv("LORA_MODE", "mock").strip().lower()

# Raspberry Pi SPI configuration (for LORA_MODE=rpi_spi)
LORA_RPI_SPI_BUS = os.getenv("LORA_RPI_SPI_BUS", "1").strip()
LORA_RPI_SPI_DEVICE = os.getenv("LORA_RPI_SPI_DEVICE", "1").strip()
LORA_RPI_RST_PIN = os.getenv("LORA_RPI_RST_PIN", "17").strip()
LORA_RPI_DIO1_PIN = os.getenv("LORA_RPI_DIO1_PIN", "22").strip()
LORA_RPI_SPI_SPEED_HZ = os.getenv("LORA_RPI_SPI_SPEED_HZ", "8000000").strip()

# USB Serial LoRa configuration (for LORA_MODE=usb_serial)
# Windows: typically COM3, COM4, COM5, etc.
# Linux: typically /dev/ttyUSB0, /dev/ttyUSB1, etc.
# macOS: typically /dev/tty.usbserial-XXXXX
LORA_USB_PORT = os.getenv("LORA_USB_PORT", "COM3").strip()
LORA_USB_BAUDRATE = os.getenv("LORA_USB_BAUDRATE", "9600").strip()
LORA_USB_TIMEOUT = os.getenv("LORA_USB_TIMEOUT", "1.0").strip()

# Legacy serial config (kept for backward compatibility)
LORA_SERIAL_BAUDRATE = int(os.getenv("LORA_SERIAL_BAUDRATE", "115200"))
LORA_SERIAL_PORT = os.getenv("LORA_SERIAL_PORT", "/dev/ttyUSB0").strip()
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

