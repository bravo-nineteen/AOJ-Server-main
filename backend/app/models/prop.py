import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PropType(str, enum.Enum):
    bomb = "Bomb"
    domination_point = "Domination Point"
    respawn_station = "Respawn Station"
    alarm = "Alarm"
    sensor = "Sensor"
    custom = "Custom"


class Prop(Base):
    __tablename__ = "props"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    prop_type: Mapped[PropType] = mapped_column(
        Enum(PropType), default=PropType.custom, nullable=False
    )
    location: Mapped[str] = mapped_column(String(140), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="offline", nullable=False)
    battery_level: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    signal_strength: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
