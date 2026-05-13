"""Player squad and team assignment models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SquadRole(str, Enum):
    """Player role within a squad."""
    commander = "commander"
    medic = "medic"
    pointman = "pointman"
    support = "support"
    scout = "scout"
    rifleman = "rifleman"


class Squad(Base):
    """Squad/fireteam grouping within a game session."""
    __tablename__ = "squads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    callsign: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    squad_members: Mapped[list["SquadMember"]] = relationship(back_populates="squad")


class SquadMember(Base):
    """Player assignment to squad with role."""
    __tablename__ = "squad_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    squad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("squads.id"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    role: Mapped[SquadRole] = mapped_column(
        String(30), default=SquadRole.rifleman, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    squad: Mapped["Squad"] = relationship(back_populates="squad_members")


class PlayerTeamAssignment(Base):
    """Direct player-to-team assignment for a session (simpler alternative to squads)."""
    __tablename__ = "player_team_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
