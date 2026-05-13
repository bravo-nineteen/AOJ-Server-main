"""LoRa Settings Management - REST API for configuring LoRa hardware and testing.

Endpoints:
- GET /api/lora/settings - List all LoRa settings
- GET /api/lora/settings/{key} - Get specific setting
- PUT /api/lora/settings/{key} - Update setting
- DELETE /api/lora/settings/{key} - Delete setting
- POST /api/lora/test/ping - Send PING to device
- POST /api/lora/test/status - Get device status
- GET /api/lora/diagnostics - Get system diagnostics
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoRaSetting(BaseModel):
    """LoRa configuration setting."""
    
    key: str = Field(..., description="Setting key (e.g., 'lora_test_mode_enabled')")
    value: str = Field(..., description="Setting value")
    value_type: str = Field(
        default="string",
        description="Value type: string, int, bool, json"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )


class LoRaSettingUpdate(BaseModel):
    """Request to update a LoRa setting."""
    
    value: str = Field(..., description="New value")
    value_type: Optional[str] = Field(
        default=None,
        description="Optional: override value type"
    )


class LoRaTestMessage(BaseModel):
    """LoRa test message."""
    
    device_id: str = Field(..., description="Target device ID")
    command: str = Field(
        default="PING",
        description="Command type: PING, STATUS, CONFIG, etc."
    )
    value: Optional[str] = Field(
        default="",
        description="Optional command value"
    )


class LoRaDiagnostics(BaseModel):
    """System diagnostics for LoRa subsystem."""
    
    mode: str = Field(..., description="Current LoRa mode (mock, rpi_spi, usb_serial, test)")
    transport_started: bool = Field(..., description="Is transport active")
    pending_ack: int = Field(..., description="Messages pending ACK")
    tx_count: int = Field(..., description="Total transmitted messages")
    rx_count: int = Field(..., description="Total received messages")
    last_tx_at: Optional[float] = Field(..., description="Timestamp of last TX")
    last_rx_at: Optional[float] = Field(..., description="Timestamp of last RX")
    alive: bool = Field(..., description="Is device responsive (RX in last 60s)")
    last_error: Optional[str] = Field(..., description="Last error message")


class LoRaTestConfig(BaseModel):
    """LoRa test configuration."""
    
    test_mode_enabled: bool = Field(
        default=False,
        description="Enable simulated responses"
    )
    test_device_id: str = Field(
        default="TEST_DEVICE_001",
        description="Test device identifier"
    )
    auto_respond: bool = Field(
        default=True,
        description="Automatically respond with ACKs"
    )
    inject_errors: bool = Field(
        default=False,
        description="Inject simulated errors"
    )
    error_rate: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Error percentage when injection enabled"
    )
    latency_ms: int = Field(
        default=100,
        ge=0,
        le=5000,
        description="Simulated response latency in ms"
    )
    ping_interval: int = Field(
        default=30,
        ge=0,
        le=3600,
        description="Auto-PING interval in seconds (0 to disable)"
    )
