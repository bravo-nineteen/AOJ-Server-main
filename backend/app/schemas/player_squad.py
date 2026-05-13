"""Schemas for player squad and team assignment."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SquadMemberBase(BaseModel):
    player_id: int
    role: str = Field(default="rifleman", max_length=30)


class SquadMemberCreate(SquadMemberBase):
    pass


class SquadMemberRead(SquadMemberBase):
    id: int
    squad_id: int
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SquadBase(BaseModel):
    name: str = Field(..., max_length=100)
    callsign: str = Field(default="", max_length=50)
    game_session_id: int
    team_id: int


class SquadCreate(SquadBase):
    pass


class SquadUpdate(BaseModel):
    name: str | None = None
    callsign: str | None = None


class SquadRead(SquadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    squad_members: list[SquadMemberRead] = []

    model_config = ConfigDict(from_attributes=True)


class PlayerTeamAssignmentBase(BaseModel):
    player_id: int
    team_id: int


class PlayerTeamAssignmentCreate(PlayerTeamAssignmentBase):
    pass


class PlayerTeamAssignmentRead(PlayerTeamAssignmentBase):
    id: int
    game_session_id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
