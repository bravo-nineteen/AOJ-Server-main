from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_session: Mapped["GameSession"] = relationship(back_populates="score_events")
    team: Mapped["Team | None"] = relationship(back_populates="score_events")
    device: Mapped["Device | None"] = relationship(back_populates="score_events")
    player: Mapped["Player | None"] = relationship(back_populates="score_events")
