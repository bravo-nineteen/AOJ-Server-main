from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    permissions: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
