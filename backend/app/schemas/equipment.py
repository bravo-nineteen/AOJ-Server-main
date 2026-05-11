"""Schemas for equipment inventory and maintenance."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EquipmentTypeBase(BaseModel):
    name: str = Field(..., max_length=100, unique=True)
    category: str = Field(..., max_length=50)
    description: str = Field(default="", max_length=1000)


class EquipmentTypeCreate(EquipmentTypeBase):
    pass


class EquipmentTypeRead(EquipmentTypeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EquipmentBase(BaseModel):
    equipment_type_id: int
    name: str = Field(..., max_length=200)
    asset_id: str = Field(..., max_length=50, unique=True)
    status: str = Field(default="available", max_length=50)
    current_user: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=1000)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    status: str | None = None
    current_user: str | None = None
    location: str | None = None
    notes: str | None = None


class EquipmentRead(EquipmentBase):
    id: int
    purchased_at: datetime | None
    last_maintenance: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceRecordBase(BaseModel):
    maintenance_type: str = Field(..., max_length=100)
    description: str
    parts_replaced: str = Field(default="", max_length=1000)
    performed_by: str = Field(..., max_length=100)
    cost: float = Field(default=0.0, ge=0)
    notes: str = Field(default="", max_length=1000)


class MaintenanceRecordCreate(MaintenanceRecordBase):
    equipment_id: int


class MaintenanceRecordRead(MaintenanceRecordBase):
    id: int
    equipment_id: int
    maintenance_date: datetime
    next_maintenance_due: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EquipmentCheckoutBase(BaseModel):
    checked_out_by: str = Field(..., max_length=100)
    condition_before: str = Field(default="good", max_length=50)
    condition_after: str = Field(default="", max_length=50)
    notes: str = Field(default="", max_length=1000)


class EquipmentCheckoutCreate(EquipmentCheckoutBase):
    equipment_id: int
    game_session_id: int | None = None
    player_id: int | None = None


class EquipmentCheckoutRead(EquipmentCheckoutBase):
    id: int
    equipment_id: int
    game_session_id: int | None
    player_id: int | None
    checked_out_at: datetime
    checked_in_by: str
    checked_in_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
