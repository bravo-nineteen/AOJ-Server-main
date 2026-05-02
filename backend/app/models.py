import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class MissionStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    complete = "complete"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), default=DeviceStatus.offline, nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="device")


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


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus), default=MissionStatus.planned, nullable=False
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_sessions: Mapped[list["GameSession"]] = relationship(back_populates="mission")
    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="mission")
    objectives: Mapped[list["MissionObjective"]] = relationship(back_populates="mission")


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    mission: Mapped["Mission"] = relationship(back_populates="game_sessions")
    teams: Mapped[list["Team"]] = relationship(back_populates="game_session")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="game_session")
    game_results: Mapped[list["GameResult"]] = relationship(back_populates="game_session")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    callsign: Mapped[str] = mapped_column(String(40), nullable=False)

    game_session: Mapped["GameSession"] = relationship(back_populates="teams")
    score_events: Mapped[list["ScoreEvent"]] = relationship(back_populates="team")


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_session: Mapped["GameSession"] = relationship(back_populates="score_events")
    team: Mapped["Team"] = relationship(back_populates="score_events")
    device: Mapped["Device"] = relationship(back_populates="score_events")


class ResultWinner(str, enum.Enum):
    red = "Red"
    blue = "Blue"
    draw = "Draw"
    cancelled = "Cancelled"


class GameResult(Base):
    __tablename__ = "game_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=True
    )
    session_name: Mapped[str] = mapped_column(String(120), nullable=False)
    winner: Mapped[ResultWinner] = mapped_column(
        Enum(ResultWinner), default=ResultWinner.draw, nullable=False
    )
    red_points: Mapped[int] = mapped_column(Integer, default=0)
    blue_points: Mapped[int] = mapped_column(Integer, default=0)
    red_penalties: Mapped[int] = mapped_column(Integer, default=0)
    blue_penalties: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game_session: Mapped["GameSession"] = relationship(back_populates="game_results")


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    activity_type: Mapped[str] = mapped_column(String(32), default="Custom", nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    mission: Mapped["Mission"] = relationship(back_populates="schedule_items")


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


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    permissions: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MissionObjective(Base):
    """Persisted objectives belonging to a Mission (mirrors in-memory state)."""

    __tablename__ = "mission_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based display order
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    mission: Mapped["Mission"] = relationship(back_populates="objectives")
