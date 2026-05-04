"""Pydantic schemas for announcement rules."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementRuleBase(BaseModel):
    name: str = Field(..., max_length=100)
    enabled: bool = True
    trigger_activity_types: str = Field(
        default="",
        description="Comma-separated activity types, e.g. 'Drop Off,Pickup'. Empty = all types.",
    )
    trigger_minutes_before: int = Field(default=15, ge=1, le=1440)
    message_template: str = Field(
        ...,
        description="Message text. Use {title}, {start_time}, {activity_type} as placeholders.",
    )


class AnnouncementRuleCreate(AnnouncementRuleBase):
    pass


class AnnouncementRuleUpdate(AnnouncementRuleBase):
    pass


class AnnouncementRuleRead(AnnouncementRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
