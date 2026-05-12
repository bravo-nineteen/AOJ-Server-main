import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceEventType(str, enum.Enum):
    status_change = "status_change"
    trigger = "trigger"
    alarm = "alarm"
    battery_low = "battery_low"
    offline = "offline"
    online = "online"
    command_ack = "command_ack"
    custom = "custom"


class DeviceEvent(Base):
    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=True, index=True
    )
    event_type: Mapped[DeviceEventType] = mapped_column(
        Enum(DeviceEventType), default=DeviceEventType.custom, nullable=False
    )
    payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    device: Mapped["Device"] = relationship(back_populates="events")
    game_session: Mapped["GameSession | None"] = relationship(back_populates="device_events")
