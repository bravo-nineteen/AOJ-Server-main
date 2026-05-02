from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_session: Mapped["GameSession"] = relationship(back_populates="score_events")
    team: Mapped["Team"] = relationship(back_populates="score_events")
    device: Mapped["Device"] = relationship(back_populates="score_events")
