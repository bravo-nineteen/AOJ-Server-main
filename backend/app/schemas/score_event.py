from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreEventBase(BaseModel):
    game_session_id: int
    team_id: int
    device_id: int | None = None
    points: int = 0
    event_type: str


class ScoreEventCreate(ScoreEventBase):
    pass


class ScoreEventRead(ScoreEventBase):
    id: int
    happened_at: datetime

    model_config = ConfigDict(from_attributes=True)
