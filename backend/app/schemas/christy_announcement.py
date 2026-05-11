"""Schemas for Christy announcements."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChristyAnnouncementBase(BaseModel):
    type: str = Field(default="general", max_length=50)
    content: str = Field(..., max_length=5000)
    message: str | None = Field(default=None, max_length=5000)


class ChristyAnnouncementCreate(ChristyAnnouncementBase):
    pass


class ChristyAnnouncementRead(ChristyAnnouncementBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
