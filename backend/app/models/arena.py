"""Field/arena management - locations, objectives, respawn points."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Arena(Base):
    """Field/arena definition for a location."""
    __tablename__ = "arenas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    field_map_url: Mapped[str] = mapped_column(
        String(500), default="", nullable=False
    )  # URL to map image/file
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ArenaLocation(Base):
    """Named location/bunker/waypoint within an arena."""
    __tablename__ = "arena_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    arena_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arenas.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # bunker, objective, waypoint, safe_zone
    x_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    y_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RespawnPoint(Base):
    """Respawn/spawn point assignment for teams."""
    __tablename__ = "respawn_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    arena_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arenas.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    x_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    y_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    respawn_delay_seconds: Mapped[int] = mapped_column(default=0, nullable=False)
    max_simultaneous_respawns: Mapped[int] = mapped_column(
        default=0, nullable=False
    )  # 0 = unlimited
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NoFireZone(Base):
    """Restricted fire area for safety."""
    __tablename__ = "no_fire_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    arena_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arenas.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    x_center: Mapped[float] = mapped_column(default=0.0, nullable=False)
    y_center: Mapped[float] = mapped_column(default=0.0, nullable=False)
    radius_meters: Mapped[float] = mapped_column(default=10.0, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ObjectiveMarker(Base):
    """Objective location marker for game sessions."""
    __tablename__ = "objective_markers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    arena_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arenas.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    objective_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # capture, defend, retrieve, plant, etc
    x_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    y_coord: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="neutral", nullable=False
    )  # neutral, red_controlled, blue_controlled, contested
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
