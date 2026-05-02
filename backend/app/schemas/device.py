from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    name: str
    device_type: str
    ip_address: str
    status: Literal["online", "offline", "maintenance"] = "offline"


class DeviceCreate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    id: int
    last_seen: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
