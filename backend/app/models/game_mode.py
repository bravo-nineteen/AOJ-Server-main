from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameMode(Base):
    __tablename__ = "game_modes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    default_main_timer_seconds: Mapped[int] = mapped_column(Integer, default=1800, nullable=False)
    default_phase_timer_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    rules: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    missions: Mapped[list["Mission"]] = relationship(back_populates="game_mode")
    game_sessions: Mapped[list["GameSession"]] = relationship(back_populates="game_mode")
