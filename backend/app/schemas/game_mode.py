"""Schemas for game modes."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GameModeBase(BaseModel):
    name: str = Field(..., max_length=80)
    description: str = Field(default="", max_length=1000)
    default_main_timer_seconds: int = Field(default=1800, ge=60, le=3600)
    default_phase_timer_seconds: int = Field(default=300, ge=60, le=1800)
    rules: str = Field(default="{}", description="JSON rules configuration")


class GameModeCreate(GameModeBase):
    pass


class GameModeUpdate(GameModeBase):
    pass


class GameModeRead(GameModeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
