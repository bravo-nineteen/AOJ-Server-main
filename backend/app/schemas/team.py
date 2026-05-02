from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    game_session_id: int
    name: str
    callsign: str


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
