from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Association table for many-to-many relationship between GameSession and Prop
game_session_props_association = Table(
    "game_session_props",
    Base.metadata,
    Column("game_session_id", Integer, ForeignKey("game_sessions.id"), primary_key=True),
    Column("prop_id", Integer, ForeignKey("props.id"), primary_key=True),
)


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    game_mode_id: Mapped[int | None] = mapped_column(ForeignKey("game_modes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    main_timer_seconds: Mapped[int] = mapped_column(Integer, default=1800, nullable=False)
    phase_timer_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    red_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blue_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    mission: Mapped["Mission"] = relationship(back_populates="game_sessions")
    game_mode: Mapped["GameMode | None"] = relationship(back_populates="game_sessions")
    teams: Mapped[list["Team"]] = relationship(back_populates="game_session")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="game_session")
    device_events: Mapped[list["DeviceEvent"]] = relationship(back_populates="game_session")
    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="game_session")
    game_results: Mapped[list["GameResult"]] = relationship(back_populates="game_session")
    logs: Mapped[list["SystemLog"]] = relationship(back_populates="game_session")
    props: Mapped[list["Prop"]] = relationship(
        "Prop",
        secondary=game_session_props_association,
        back_populates="game_sessions",
    )
