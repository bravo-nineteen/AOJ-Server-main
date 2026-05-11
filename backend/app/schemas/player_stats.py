"""Schemas for player statistics and leaderboards."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerSessionBase(BaseModel):
    player_id: int
    game_session_id: int
    team_id: int
    squad_id: int | None = None
    role: str = Field(default="rifleman", max_length=50)
    participation_minutes: int = 0


class PlayerSessionCreate(PlayerSessionBase):
    pass


class PlayerSessionRead(PlayerSessionBase):
    id: int
    joined_at: datetime
    left_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PlayerStatisticBase(BaseModel):
    player_id: int
    stat_type: str = Field(..., max_length=50)
    period_start: datetime | None = None
    period_end: datetime | None = None
    objectives_completed: int = 0
    objectives_captured: int = 0
    objectives_defended: int = 0
    points_scored: int = 0
    points_against: int = 0
    sessions_participated: int = 0
    total_play_minutes: int = 0
    medic_assists: int = 0
    squad_leader_commendations: int = 0
    special_achievements: str = Field(default="", max_length=500)


class PlayerStatisticCreate(PlayerStatisticBase):
    pass


class PlayerStatisticUpdate(BaseModel):
    objectives_completed: int | None = None
    objectives_captured: int | None = None
    points_scored: int | None = None
    total_play_minutes: int | None = None
    special_achievements: str | None = None


class PlayerStatisticRead(PlayerStatisticBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObjectiveCompletionBase(BaseModel):
    game_session_id: int
    player_id: int
    objective_name: str = Field(..., max_length=200)
    objective_type: str = Field(..., max_length=50)
    points_awarded: int = 0


class ObjectiveCompletionCreate(ObjectiveCompletionBase):
    pass


class ObjectiveCompletionRead(ObjectiveCompletionBase):
    id: int
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlayerLeaderboardEntry(BaseModel):
    """Leaderboard view of player stats."""
    player_id: int
    player_name: str
    rank: int
    points_total: int
    objectives_completed: int
    sessions_participated: int
    average_points_per_session: float
    win_rate: float | None = None


class TeamLeaderboardEntry(BaseModel):
    """Team leaderboard view."""
    team_id: int
    team_name: str
    rank: int
    total_wins: int
    total_losses: int
    win_rate: float
    total_points: int
    tournament_points: int | None = None
