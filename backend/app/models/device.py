import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    armed = "armed"
    disarmed = "disarmed"
    alarm = "alarm"
    maintenance = "maintenance"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_types.id"), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, unique=True)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), default=DeviceStatus.offline, nullable=False
    )
    battery_level: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    signal_strength: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(140), default="", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    device_type: Mapped["DeviceType | None"] = relationship(back_populates="devices")
    commands: Mapped[list["DeviceCommand"]] = relationship(back_populates="device")
    events: Mapped[list["DeviceEvent"]] = relationship(back_populates="device")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="device")
    logs: Mapped[list["SystemLog"]] = relationship(back_populates="device")
