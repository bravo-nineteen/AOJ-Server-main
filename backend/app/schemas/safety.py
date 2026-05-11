"""Schemas for safety and compliance tracking."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChronoCheckBase(BaseModel):
    weapon_name: str = Field(..., max_length=200)
    weapon_type: str = Field(..., max_length=50)
    fps_reading: int
    max_allowed_fps: int = 500
    passed: bool = False
    notes: str = Field(default="", max_length=500)
    checked_by: str = Field(..., max_length=100)


class ChronoCheckCreate(ChronoCheckBase):
    player_id: int
    game_session_id: int | None = None


class ChronoCheckRead(ChronoCheckBase):
    id: int
    player_id: int
    game_session_id: int | None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalIncidentBase(BaseModel):
    incident_type: str = Field(..., max_length=100)
    severity: str = Field(default="minor", max_length=20)
    description: str
    action_taken: str = Field(default="", max_length=2000)
    witnessed_by: str = Field(default="", max_length=200)


class MedicalIncidentCreate(MedicalIncidentBase):
    player_id: int
    game_session_id: int | None = None


class MedicalIncidentRead(MedicalIncidentBase):
    id: int
    player_id: int
    game_session_id: int | None
    incident_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SafetyViolationBase(BaseModel):
    violation_type: str = Field(..., max_length=100)
    severity: str = Field(default="warning", max_length=20)
    description: str
    action_taken: str = Field(default="", max_length=2000)
    reported_by: str = Field(..., max_length=100)


class SafetyViolationCreate(SafetyViolationBase):
    player_id: int
    game_session_id: int | None = None


class SafetyViolationRead(SafetyViolationBase):
    id: int
    player_id: int
    game_session_id: int | None
    violation_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WaiverBase(BaseModel):
    waiver_version: str = Field(default="1.0", max_length=20)
    acknowledged: bool = False
    acknowledged_by_proxy: str = Field(default="", max_length=200)


class WaiverCreate(WaiverBase):
    player_id: int


class WaiverRead(WaiverBase):
    id: int
    player_id: int
    acknowledged_at: datetime | None
    expiry_date: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WaiverUpdate(BaseModel):
    acknowledged: bool
    ignored_by_proxy: str | None = None
