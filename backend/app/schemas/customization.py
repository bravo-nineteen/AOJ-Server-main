from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CustomTeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    short_name: str = Field(default="", max_length=20)
    color: str = Field(default="#ffffff", min_length=3, max_length=32)
    icon: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=4000)
    active: bool = True


class CustomTeamCreate(CustomTeamBase):
    pass


class CustomTeamUpdate(CustomTeamBase):
    pass


class CustomTeamRead(CustomTeamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CustomGameModeBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=4000)
    rules_text: str = Field(default="", max_length=20000)
    default_duration_minutes: int = Field(default=30, ge=1, le=720)
    scoring_rules_json: dict[str, Any] = Field(default_factory=dict)
    objective_rules_json: dict[str, Any] = Field(default_factory=dict)
    respawn_rules_text: str = Field(default="", max_length=10000)
    active: bool = True


class CustomGameModeCreate(CustomGameModeBase):
    pass


class CustomGameModeUpdate(CustomGameModeBase):
    pass


class CustomGameModeRead(CustomGameModeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CustomKnowledgeEntryBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    category: str = Field(default="", max_length=80)
    content: str = Field(min_length=1, max_length=30000)
    tags: list[str] = Field(default_factory=list)
    active: bool = True


class CustomKnowledgeEntryCreate(CustomKnowledgeEntryBase):
    pass


class CustomKnowledgeEntryUpdate(CustomKnowledgeEntryBase):
    pass


class CustomKnowledgeEntryRead(CustomKnowledgeEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisualThemeBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_active: bool = False
    primary_color: str = Field(default="#0057ff", min_length=3, max_length=32)
    secondary_color: str = Field(default="#00b894", min_length=3, max_length=32)
    accent_color: str = Field(default="#f4b400", min_length=3, max_length=32)
    background_color: str = Field(default="#10151f", min_length=3, max_length=32)
    panel_color: str = Field(default="#172233", min_length=3, max_length=32)
    text_color: str = Field(default="#f3f6ff", min_length=3, max_length=32)
    warning_color: str = Field(default="#f39c12", min_length=3, max_length=32)
    danger_color: str = Field(default="#e74c3c", min_length=3, max_length=32)
    success_color: str = Field(default="#2ecc71", min_length=3, max_length=32)
    font_family: str = Field(default="Sora, sans-serif", max_length=120)
    border_radius: str = Field(default="10px", max_length=32)
    density: str = Field(default="comfortable", max_length=32)
    background_style: str = Field(default="gradient", max_length=80)
    logo_url: str = Field(default="", max_length=512)


class VisualThemeCreate(VisualThemeBase):
    pass


class VisualThemeUpdate(VisualThemeBase):
    pass


class VisualThemeRead(VisualThemeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ActiveThemeSetRequest(BaseModel):
    theme_id: int = Field(ge=1)


class AIAssistantSettingsBase(BaseModel):
    enabled: bool = True
    provider: str = Field(default="mock", min_length=1, max_length=50)
    model: str = Field(default="local-advisor", min_length=1, max_length=120)
    voice_enabled: bool = False
    speech_to_text_enabled: bool = False
    text_to_speech_enabled: bool = False
    system_personality: str = Field(default="", max_length=10000)
    response_style: str = Field(default="concise", min_length=1, max_length=50)
    max_context_entries: int = Field(default=24, ge=1, le=500)
    safety_mode: str = Field(default="strict", min_length=1, max_length=50)


class AIAssistantSettingsUpdate(AIAssistantSettingsBase):
    pass


class AIAssistantSettingsRead(AIAssistantSettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
