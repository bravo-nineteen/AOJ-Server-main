"""AnnouncementRule – configurable timed announcement before a schedule activity type."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnnouncementRule(Base):
    __tablename__ = "announcement_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Comma-separated list of activity_type values that trigger this rule,
    # e.g. "Drop Off,Pickup" or "Game". Empty string means all types.
    trigger_activity_types: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    # How many minutes before the scheduled start_time this fires
    trigger_minutes_before: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    # The message to broadcast. Supports {title}, {start_time}, {activity_type} placeholders.
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
