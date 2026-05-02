from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GameSessionBase(BaseModel):
    mission_id: int | None = None
    name: str
    is_active: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None


class GameSessionCreate(GameSessionBase):
    pass


class GameSessionRead(GameSessionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
