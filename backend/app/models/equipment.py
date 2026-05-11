"""Equipment inventory and maintenance tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EquipmentType(Base):
    """Categories of equipment (props, weapons, comms, etc)."""
    __tablename__ = "equipment_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # prop, weapon, comm, protective, ammo
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Equipment(Base):
    """Inventory of physical equipment items."""
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    equipment_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment_types.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # serial/barcode
    status: Mapped[str] = mapped_column(
        String(50), default="available", nullable=False
    )  # available, in_use, maintenance, retired
    current_user: Mapped[str] = mapped_column(
        String(100), default="", nullable=False
    )  # player or staff name
    location: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_maintenance: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MaintenanceRecord(Base):
    """History of maintenance actions on equipment."""
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id"), nullable=False, index=True
    )
    maintenance_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # battery_replacement, cleaning, repair, calibration
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parts_replaced: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )  # comma-separated list
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    maintenance_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_maintenance_due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cost: Mapped[float] = mapped_column(default=0.0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EquipmentCheckout(Base):
    """Equipment checkout/check-in log for accountability."""
    __tablename__ = "equipment_checkouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id"), nullable=False, index=True
    )
    game_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("game_sessions.id"), nullable=True
    )
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    checked_out_by: Mapped[str] = mapped_column(String(100), nullable=False)
    checked_out_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    checked_in_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    condition_before: Mapped[str] = mapped_column(
        String(50), default="good", nullable=False
    )  # good, damaged, needs_repair
    condition_after: Mapped[str] = mapped_column(
        String(50), default="", nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
