import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceCategory(str, enum.Enum):
    prop = "prop"
    sensor = "sensor"
    controller = "controller"
    display = "display"
    network = "network"
    custom = "custom"


class DeviceType(Base):
    __tablename__ = "device_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[DeviceCategory] = mapped_column(
        Enum(DeviceCategory), default=DeviceCategory.custom, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    default_commands: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    devices: Mapped[list["Device"]] = relationship(back_populates="device_type")
