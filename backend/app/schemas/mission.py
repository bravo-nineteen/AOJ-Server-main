from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MissionBase(BaseModel):
    title: str
    description: str = ""
    status: Literal["planned", "active", "complete"] = "planned"
    start_time: datetime | None = None
    end_time: datetime | None = None


class MissionCreate(MissionBase):
    pass


class MissionUpdate(MissionBase):
    pass


class MissionRead(MissionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
