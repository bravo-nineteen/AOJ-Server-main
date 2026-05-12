import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LogLevel(str, enum.Enum):
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"


class LogCategory(str, enum.Enum):
    system = "SYSTEM"
    mission = "MISSION"
    prop = "PROP"
    lora = "LORA"
    wifi = "WIFI"
    ai = "AI"
    update = "UPDATE"


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[LogLevel] = mapped_column(
        Enum(
            LogLevel,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=LogLevel.info,
    )
    category: Mapped[LogCategory] = mapped_column(
        Enum(
            LogCategory,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=LogCategory.system,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional context links
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    game_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=True
    )
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    mission: Mapped["Mission | None"] = relationship(back_populates="logs")
    game_session: Mapped["GameSession | None"] = relationship(back_populates="logs")
    device: Mapped["Device | None"] = relationship(back_populates="logs")
    user: Mapped["User | None"] = relationship(back_populates="logs")
