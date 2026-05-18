from datetime import datetime
from typing import Literal
import json

from pydantic import BaseModel, ConfigDict, field_validator


class ScheduleItemBase(BaseModel):
    mission_id: int | None = None
    title: str
    details: str = ""
    activity_type: Literal[
        "Safety Brief", "Game", "Break", "Lunch", "Setup", "Pack Down", "Pickup", "Drop Off", "Custom"
    ] = "Custom"
    start_time: datetime
    end_time: datetime | None = None
    game_mode: str = ""
    props_needed: list[str] = []


class ScheduleItemCreate(ScheduleItemBase):
    pass


class ScheduleItemRead(ScheduleItemBase):
    id: int
    is_complete: bool
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('props_needed', mode='before')
    @classmethod
    def deserialize_props(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []


class ScheduleItemUpdate(BaseModel):
    mission_id: int | None = None
    title: str
    details: str = ""
    activity_type: Literal[
        "Safety Brief", "Game", "Break", "Lunch", "Setup", "Pack Down", "Pickup", "Drop Off", "Custom"
    ] = "Custom"
    start_time: datetime
    end_time: datetime | None = None
    game_mode: str = ""
    is_complete: bool = False
    props_needed: list[str] = []


class ScheduleOverviewResponse(BaseModel):
    current_activity: ScheduleItemRead | None = None
    next_activity: ScheduleItemRead | None = None
    delay_warning: str | None = None
