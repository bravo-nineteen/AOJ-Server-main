"""Schemas for game event timeline."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GameEventBase(BaseModel):
    event_type: str
    description: str = Field(default="", max_length=1000)
    event_metadata: str = Field(
        default="{}",
        alias="metadata",
        serialization_alias="metadata",
        max_length=5000,
    )

    model_config = ConfigDict(populate_by_name=True)


class GameEventCreate(GameEventBase):
    game_session_id: int
    team_id: int | None = None
    player_id: int | None = None
    squad_id: int | None = None
    device_id: int | None = None
    prop_id: int | None = None


class GameEventRead(GameEventBase):
    id: int
    game_session_id: int
    team_id: int | None
    player_id: int | None
    squad_id: int | None
    device_id: int | None
    prop_id: int | None
    happened_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class GameEventFilter(BaseModel):
    game_session_id: int
    event_type: str | None = None
    team_id: int | None = None
    player_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
