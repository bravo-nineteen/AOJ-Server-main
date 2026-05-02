import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MissionStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    complete = "complete"


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus), default=MissionStatus.planned, nullable=False
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_sessions: Mapped[list["GameSession"]] = relationship(back_populates="mission")
    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="mission")
    objectives: Mapped[list["MissionObjective"]] = relationship(back_populates="mission")


class MissionObjective(Base):
    """Persisted objectives belonging to a Mission (mirrors in-memory state)."""

    __tablename__ = "mission_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    mission: Mapped["Mission"] = relationship(back_populates="objectives")
