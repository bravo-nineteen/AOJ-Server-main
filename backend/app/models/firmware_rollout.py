from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FirmwareRolloutJob(Base):
    __tablename__ = "firmware_rollout_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    package_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    package_version: Mapped[str] = mapped_column(String(50), nullable=False)
    package_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False)
    targeted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    acknowledged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    targets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )