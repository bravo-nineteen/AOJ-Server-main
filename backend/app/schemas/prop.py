from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PropBase(BaseModel):
    device_id: str
    name: str
    prop_type: Literal[
        "Bomb", "Domination Point", "Respawn Station", "Alarm", "Sensor", "Custom"
    ] = "Custom"
    location: str = ""
    firmware_version: str = ""


class PropCreate(PropBase):
    auth_token: str | None = Field(default=None, min_length=8, max_length=128)


class PropUpdate(PropBase):
    auth_token: str | None = Field(default=None, min_length=8, max_length=128)


class PropStatusReport(BaseModel):
    device_id: str
    status: Literal["offline", "online", "armed", "disarmed", "alarm", "maintenance"] = "online"
    battery_level: int = Field(ge=0, le=100)
    signal_strength: int = Field(ge=0, le=100)
    firmware_version: str = ""
    transport: Literal["lora", "wifi"] = "lora"


class PropRead(PropBase):
    id: int
    status: Literal["offline", "online", "armed", "disarmed", "alarm", "maintenance"] = "offline"
    battery_level: int = Field(default=100, ge=0, le=100)
    signal_strength: int = Field(default=100, ge=0, le=100)
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropCommandRequest(BaseModel):
    command: Literal[
        "arm",
        "disarm",
        "reset",
        "status_request",
        "trigger_alarm",
        "game_start",
        "game_end",
        "ready",
        "test_buzz",
    ]
