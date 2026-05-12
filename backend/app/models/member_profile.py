"""Member profile model — stores player identity and characteristics for Christy."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MemberProfile(Base):
    __tablename__ = "member_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    callsign: Mapped[str | None] = mapped_column(String(60), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)   # male/female/other

    # Team affiliation
    team: Mapped[str | None] = mapped_column(String(80), nullable=True)     # e.g. "Red Team"

    # Skill assessment (free text, e.g. "intermediate", "expert", "new player")
    skill_level: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Free-text strengths, weaknesses, notes (comma-separated tags or paragraphs)
    strengths: Mapped[str] = mapped_column(Text, default="", nullable=False)
    weaknesses: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Christy's accumulated memory about this member
    christy_memory: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
