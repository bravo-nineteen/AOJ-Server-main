from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MemberProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    callsign: str | None = Field(None, max_length=60)
    gender: str | None = Field(None, max_length=20)
    team: str | None = Field(None, max_length=80)
    skill_level: str | None = Field(None, max_length=40)
    strengths: str = Field(default="", max_length=2000)
    weaknesses: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=4000)


class MemberProfileUpdate(BaseModel):
    callsign: str | None = Field(None, max_length=60)
    gender: str | None = Field(None, max_length=20)
    team: str | None = Field(None, max_length=80)
    skill_level: str | None = Field(None, max_length=40)
    strengths: str | None = Field(None, max_length=2000)
    weaknesses: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=4000)
    christy_memory: str | None = Field(None, max_length=8000)


class MemberProfileOut(BaseModel):
    id: int
    name: str
    callsign: str | None
    gender: str | None
    team: str | None
    skill_level: str | None
    strengths: str
    weaknesses: str
    notes: str
    christy_memory: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
