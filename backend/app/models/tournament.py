"""Tournament and bracket system for multi-round competitions."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TournamentFormat(str, Enum):
    """Tournament bracket formats."""
    single_elimination = "single_elimination"
    double_elimination = "double_elimination"
    round_robin = "round_robin"
    swiss_system = "swiss_system"
    ladder = "ladder"


class TournamentStatus(str, Enum):
    """Tournament status."""
    planning = "planning"
    registration = "registration"
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class Tournament(Base):
    """Tournament/league definition."""
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    format: Mapped[TournamentFormat] = mapped_column(String(30), nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(
        String(20), default=TournamentStatus.planning, nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_participants: Mapped[int] = mapped_column(default=0, nullable=False)  # 0 = unlimited
    rules: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False
    )  # JSON configuration
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class TournamentTeam(Base):
    """Team registration for a tournament."""
    __tablename__ = "tournament_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    seed_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class TournamentMatch(Base):
    """Single match in tournament bracket."""
    __tablename__ = "tournament_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False, index=True
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_position: Mapped[str] = mapped_column(
        String(50), default="", nullable=False
    )  # e.g., "A1", "Winners Finals"
    red_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    blue_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    game_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, in_progress, completed, bye
    winner_team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class TournamentStandings(Base):
    """Aggregate standings/rankings during tournament."""
    __tablename__ = "tournament_standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    wins: Mapped[int] = mapped_column(default=0, nullable=False)
    losses: Mapped[int] = mapped_column(default=0, nullable=False)
    draws: Mapped[int] = mapped_column(default=0, nullable=False)
    points_for: Mapped[int] = mapped_column(default=0, nullable=False)
    points_against: Mapped[int] = mapped_column(default=0, nullable=False)
    tournament_points: Mapped[int] = mapped_column(default=0, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
