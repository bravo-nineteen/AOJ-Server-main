import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamSide(str, enum.Enum):
    red = "red"
    blue = "blue"
    neutral = "neutral"
    custom = "custom"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    callsign: Mapped[str] = mapped_column(String(40), nullable=False)
    side: Mapped[TeamSide] = mapped_column(
        Enum(TeamSide), default=TeamSide.custom, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    game_session: Mapped["GameSession"] = relationship(back_populates="teams")
    players: Mapped[list["Player"]] = relationship(back_populates="team")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="team")
