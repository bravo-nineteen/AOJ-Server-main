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
    status: Literal["offline", "online", "armed", "disarmed", "alarm", "maintenance"] = "offline"
    battery_level: int = Field(default=100, ge=0, le=100)
    signal_strength: int = Field(default=100, ge=0, le=100)
    last_seen: datetime | None = None
    firmware_version: str = ""


class PropCreate(PropBase):
    pass


class PropUpdate(PropBase):
    pass


class PropRead(PropBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropCommandRequest(BaseModel):
    command: Literal["arm", "disarm", "reset", "status_request", "trigger_alarm"]
