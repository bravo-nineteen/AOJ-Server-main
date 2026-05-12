from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomTeam(Base):
    __tablename__ = "custom_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#ffffff", nullable=False)
    icon: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CustomGameMode(Base):
    __tablename__ = "custom_game_modes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rules_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    team_setup_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    objectives_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    scoring_rules_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    objective_rules_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    respawn_rules_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    win_conditions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    required_props_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    briefing_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    marshal_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CustomKnowledgeEntry(Base):
    __tablename__ = "custom_knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class VisualTheme(Base):
    __tablename__ = "visual_themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primary_color: Mapped[str] = mapped_column(String(32), default="#0057ff", nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(32), default="#00b894", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(32), default="#f4b400", nullable=False)
    background_color: Mapped[str] = mapped_column(String(32), default="#10151f", nullable=False)
    panel_color: Mapped[str] = mapped_column(String(32), default="#172233", nullable=False)
    text_color: Mapped[str] = mapped_column(String(32), default="#f3f6ff", nullable=False)
    warning_color: Mapped[str] = mapped_column(String(32), default="#f39c12", nullable=False)
    danger_color: Mapped[str] = mapped_column(String(32), default="#e74c3c", nullable=False)
    success_color: Mapped[str] = mapped_column(String(32), default="#2ecc71", nullable=False)
    font_family: Mapped[str] = mapped_column(String(120), default="Sora, sans-serif", nullable=False)
    border_radius: Mapped[str] = mapped_column(String(32), default="10px", nullable=False)
    density: Mapped[str] = mapped_column(String(32), default="comfortable", nullable=False)
    background_style: Mapped[str] = mapped_column(String(80), default="gradient", nullable=False)
    logo_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)


class AIAssistantSettings(Base):
    __tablename__ = "ai_assistant_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="local-advisor", nullable=False)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    speech_to_text_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text_to_speech_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    system_personality: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_style: Mapped[str] = mapped_column(String(50), default="concise", nullable=False)
    max_context_entries: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    safety_mode: Mapped[str] = mapped_column(String(50), default="strict", nullable=False)
