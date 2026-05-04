from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GameResultBase(BaseModel):
    game_session_id: int | None = None
    schedule_item_id: int | None = None
    session_name: str
    winner: Literal["Red", "Blue", "Draw", "Cancelled"]
    red_points: int = 0
    blue_points: int = 0
    red_penalties: int = 0
    blue_penalties: int = 0
    notes: str = ""


class GameResultCreate(GameResultBase):
    pass


class GameResultRead(GameResultBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResultsSummaryResponse(BaseModel):
    total_red_wins: int
    total_blue_wins: int
    total_draws: int
    total_cancelled: int
    total_red_points: int
    total_blue_points: int
