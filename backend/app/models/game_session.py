from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    mission: Mapped["Mission"] = relationship(back_populates="game_sessions")
    teams: Mapped[list["Team"]] = relationship(back_populates="game_session")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="game_session")
    game_results: Mapped[list["GameResult"]] = relationship(back_populates="game_session")
