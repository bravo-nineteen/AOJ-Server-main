from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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


class ScheduleItemCreate(ScheduleItemBase):
    pass


class ScheduleItemRead(ScheduleItemBase):
    id: int
    is_complete: bool
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


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


class ScheduleOverviewResponse(BaseModel):
    current_activity: ScheduleItemRead | None = None
    next_activity: ScheduleItemRead | None = None
    delay_warning: str | None = None
