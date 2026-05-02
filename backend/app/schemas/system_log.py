from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SystemLogBase(BaseModel):
    level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    category: Literal["SYSTEM", "MISSION", "PROP", "LORA", "WIFI", "AI", "UPDATE"] = "SYSTEM"
    source: str
    message: str


class SystemLogCreate(SystemLogBase):
    pass


class SystemLogRead(SystemLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
