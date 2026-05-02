from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    callsign: Mapped[str] = mapped_column(String(40), nullable=False)

    game_session: Mapped["GameSession"] = relationship(back_populates="teams")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="team")
