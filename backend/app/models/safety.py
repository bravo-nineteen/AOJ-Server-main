"""Safety and compliance tracking - chrono checks, medical incidents, waivers."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChronoCheck(Base):
    """Weapon chronograph (FPS) verification before game."""
    __tablename__ = "chrono_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    weapon_name: Mapped[str] = mapped_column(String(200), nullable=False)
    weapon_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # rifle, pistol, sniper, etc
    fps_reading: Mapped[int] = mapped_column(Integer, nullable=False)
    max_allowed_fps: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    checked_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    __table_args__ = (("ix_chrono_player_session", "player_id", "game_session_id"),)


class MedicalIncident(Base):
    """Medical incident log for liability and safety tracking."""
    __tablename__ = "medical_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default="minor", nullable=False
    )  # minor, moderate, severe
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, default="", nullable=False)
    witnessed_by: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    incident_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SafetyViolation(Base):
    """Safety rule violation documentation."""
    __tablename__ = "safety_violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True
    )
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default="warning", nullable=False
    )  # warning, suspension, elimination
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reported_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    violation_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Waiver(Base):
    """Player liability waiver/consent tracking."""
    __tablename__ = "waivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False, index=True, unique=True
    )
    waiver_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by_proxy: Mapped[str] = mapped_column(
        String(200), default="", nullable=False
    )  # parent name if minor
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
