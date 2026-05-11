"""Game event timeline - records objectives, equipment, and game events."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GameEventType(str, Enum):
    """Types of events that occur during gameplay."""
    objective_captured = "objective_captured"
    objective_lost = "objective_lost"
    objective_completed = "objective_completed"
    respawn_activated = "respawn_activated"
    equipment_deployed = "equipment_deployed"
    equipment_recovered = "equipment_recovered"
    ammo_resupply = "ammo_resupply"
    medic_assist = "medic_assist"
    squad_formed = "squad_formed"
    custom = "custom"


class GameEvent(Base):
    """Records discrete events happening during an active game session."""
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    event_type: Mapped[GameEventType] = mapped_column(String(40), nullable=False)
    team_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    squad_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("squads.id"), nullable=True
    )
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=True
    )
    prop_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("props.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    event_metadata: Mapped[str] = mapped_column(
        "metadata", Text, default="{}", nullable=False
    )  # JSON for extensibility
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Index for common queries during game playback
        Index("ix_game_event_session_time", "game_session_id", "happened_at"),
    )
