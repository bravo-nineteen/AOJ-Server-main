"""Player statistics and leaderboard models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlayerSession(Base):
    """Player participation in a game session."""
    __tablename__ = "player_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    squad_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("squads.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(
        String(50), default="rifleman", nullable=False
    )  # squad role
    participation_minutes: Mapped[int] = mapped_column(
        default=0, nullable=False
    )  # time in game
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PlayerStatistic(Base):
    """Aggregated player statistics (per session, season, lifetime)."""
    __tablename__ = "player_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    stat_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # session, season, lifetime
    period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Objective-based stats
    objectives_completed: Mapped[int] = mapped_column(default=0, nullable=False)
    objectives_captured: Mapped[int] = mapped_column(default=0, nullable=False)
    objectives_defended: Mapped[int] = mapped_column(default=0, nullable=False)
    # Scoring
    points_scored: Mapped[int] = mapped_column(default=0, nullable=False)
    points_against: Mapped[int] = mapped_column(default=0, nullable=False)
    # Participation
    sessions_participated: Mapped[int] = mapped_column(default=0, nullable=False)
    total_play_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    # Role-based
    medic_assists: Mapped[int] = mapped_column(default=0, nullable=False)
    squad_leader_commendations: Mapped[int] = mapped_column(default=0, nullable=False)
    # Custom points
    special_achievements: Mapped[str] = mapped_column(
        String(500), default="", nullable=False
    )  # comma-separated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_player_stat_type", "player_id", "stat_type"),)


class ObjectiveCompletion(Base):
    """Track which players completed which objectives."""
    __tablename__ = "objective_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    objective_name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # capture, defend, retrieve, etc
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    points_awarded: Mapped[int] = mapped_column(default=0, nullable=False)
