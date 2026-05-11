"""LoRa Test Settings - Initialize testing configuration in database.

Run this migration to add LoRa-related test settings to the system database.
"""

from datetime import datetime
from app.models.system_setting import SystemSetting


LORA_SETTINGS = [
    {
        "key": "lora_test_mode_enabled",
        "value": "false",
        "value_type": "bool",
        "description": "Enable LoRa test mode with simulated responses",
    },
    {
        "key": "lora_test_device_id",
        "value": "TEST_DEVICE_001",
        "value_type": "string",
        "description": "Test device ID for simulated LoRa devices",
    },
    {
        "key": "lora_test_auto_respond",
        "value": "true",
        "value_type": "bool",
        "description": "Automatically respond to test messages with mock ACKs",
    },
    {
        "key": "lora_test_inject_errors",
        "value": "false",
        "value_type": "bool",
        "description": "Inject simulated errors and timeouts for testing",
    },
    {
        "key": "lora_test_error_rate",
        "value": "5",
        "value_type": "int",
        "description": "Percentage of messages to fail when error injection is enabled (0-100)",
    },
    {
        "key": "lora_test_latency_ms",
        "value": "100",
        "value_type": "int",
        "description": "Simulated latency in milliseconds for test responses (0-5000)",
    },
    {
        "key": "lora_hardware_mode",
        "value": "mock",
        "value_type": "string",
        "description": "Active LoRa hardware mode: mock, rpi_spi, usb_serial, test",
    },
    {
        "key": "lora_rpi_spi_enabled",
        "value": "false",
        "value_type": "bool",
        "description": "Enable Raspberry Pi SPI mode (Waveshare Core1262 HF SX1262)",
    },
    {
        "key": "lora_rpi_spi_bus",
        "value": "1",
        "value_type": "int",
        "description": "SPI bus number (1 = SPI1 on RPi 5)",
    },
    {
        "key": "lora_rpi_spi_device",
        "value": "1",
        "value_type": "int",
        "description": "SPI chip select device (0 or 1)",
    },
    {
        "key": "lora_rpi_rst_pin",
        "value": "17",
        "value_type": "int",
        "description": "GPIO pin number for LoRa reset (default: GPIO17)",
    },
    {
        "key": "lora_rpi_dio1_pin",
        "value": "22",
        "value_type": "int",
        "description": "GPIO pin number for DIO1 interrupt (default: GPIO22)",
    },
    {
        "key": "lora_usb_enabled",
        "value": "false",
        "value_type": "bool",
        "description": "Enable USB LoRa serial mode",
    },
    {
        "key": "lora_usb_port",
        "value": "COM3",
        "value_type": "string",
        "description": "USB LoRa serial port (COM3 on Windows, /dev/ttyUSB0 on Linux)",
    },
    {
        "key": "lora_usb_baudrate",
        "value": "9600",
        "value_type": "int",
        "description": "USB LoRa serial baud rate (9600, 19200, 115200, etc.)",
    },
    {
        "key": "lora_usb_timeout",
        "value": "1.0",
        "value_type": "string",
        "description": "USB LoRa serial read timeout in seconds",
    },
    {
        "key": "lora_diagnostics_enabled",
        "value": "true",
        "value_type": "bool",
        "description": "Enable LoRa diagnostics and statistics collection",
    },
    {
        "key": "lora_max_retries",
        "value": "3",
        "value_type": "int",
        "description": "Maximum number of retries for failed LoRa messages",
    },
    {
        "key": "lora_ack_timeout_seconds",
        "value": "3.0",
        "value_type": "string",
        "description": "ACK timeout in seconds",
    },
    {
        "key": "lora_test_ping_interval",
        "value": "30",
        "value_type": "int",
        "description": "Interval in seconds for test PING messages (0 to disable)",
    },
]


def add_lora_settings(session) -> None:
    """Add LoRa test and configuration settings to the database.
    
    Args:
        session: SQLAlchemy session instance
    """
    now = datetime.utcnow()
    added = 0

    for setting_data in LORA_SETTINGS:
        # Check if setting already exists
        existing = session.query(SystemSetting).filter_by(key=setting_data["key"]).first()
        if existing:
            continue

        setting = SystemSetting(
            key=setting_data["key"],
            value=setting_data["value"],
            value_type=setting_data["value_type"],
            description=setting_data["description"],
            created_at=now,
            updated_at=now,
        )
        session.add(setting)
        added += 1

    if added > 0:
        session.commit()
        print(f"Added {added} LoRa settings to database")
    else:
        print("LoRa settings already exist in database")
