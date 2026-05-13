"""Schemas for tournament and bracket system."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TournamentBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=2000)
    format: str = Field(..., max_length=30)
    status: str = Field(default="planning", max_length=20)
    start_date: datetime
    end_date: datetime | None = None
    max_participants: int = Field(default=0, ge=0)
    rules: str = Field(default="{}", max_length=10000)


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    end_date: datetime | None = None


class TournamentRead(TournamentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentTeamBase(BaseModel):
    tournament_id: int
    team_id: int
    seed_position: int | None = None


class TournamentTeamCreate(TournamentTeamBase):
    pass


class TournamentTeamRead(TournamentTeamBase):
    id: int
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentMatchBase(BaseModel):
    tournament_id: int
    round_number: int
    match_number: int
    bracket_position: str = Field(default="", max_length=50)
    red_team_id: int | None = None
    blue_team_id: int | None = None
    game_session_id: int | None = None
    status: str = Field(default="pending", max_length=30)
    scheduled_at: datetime | None = None
    notes: str = Field(default="", max_length=1000)


class TournamentMatchCreate(TournamentMatchBase):
    pass


class TournamentMatchUpdate(BaseModel):
    status: str | None = None
    game_session_id: int | None = None
    winner_team_id: int | None = None
    scheduled_at: datetime | None = None
    notes: str | None = None


class TournamentMatchRead(TournamentMatchBase):
    id: int
    winner_team_id: int | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentStandingsBase(BaseModel):
    tournament_id: int
    team_id: int
    wins: int = 0
    losses: int = 0
    draws: int = 0
    points_for: int = 0
    points_against: int = 0
    tournament_points: int = 0
    rank: int | None = None


class TournamentStandingsRead(TournamentStandingsBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
