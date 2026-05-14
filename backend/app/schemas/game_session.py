from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GameSessionBase(BaseModel):
    mission_id: int | None = None
    game_mode_id: int | None = None
    name: str
    is_active: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None


class GameSessionCreate(GameSessionBase):
    pass


class GameSessionRead(GameSessionBase):
    id: int


class GameSessionUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    game_mode_id: int | None = None
    main_timer_seconds: int | None = None
    phase_timer_seconds: int | None = None
    red_score: int | None = None
    blue_score: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
