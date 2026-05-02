import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResultWinner(str, enum.Enum):
    red = "Red"
    blue = "Blue"
    draw = "Draw"
    cancelled = "Cancelled"


class GameResult(Base):
    __tablename__ = "game_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=True
    )
    session_name: Mapped[str] = mapped_column(String(120), nullable=False)
    winner: Mapped[ResultWinner] = mapped_column(
        Enum(ResultWinner), default=ResultWinner.draw, nullable=False
    )
    red_points: Mapped[int] = mapped_column(Integer, default=0)
    blue_points: Mapped[int] = mapped_column(Integer, default=0)
    red_penalties: Mapped[int] = mapped_column(Integer, default=0)
    blue_penalties: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_session: Mapped["GameSession"] = relationship(back_populates="game_results")
