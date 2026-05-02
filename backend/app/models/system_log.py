import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel), default=LogLevel.info)
    category: Mapped[LogCategory] = mapped_column(
        Enum(LogCategory), default=LogCategory.system
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
