from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIAskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class AIResponsePayload(BaseModel):
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    used_context: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_admin_confirmation: bool = False


class AIAskResponse(AIResponsePayload):
    advisory_only: bool = True
    blocked_action: bool = False
    safety_notice: str
    model: str


class AIConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    mission_id: int | None = None
    user_id: int | None = None


class AIConversationRead(BaseModel):
    id: int
    user_id: int | None = None
    mission_id: int | None = None
    title: str | None = None
    status: str
    memory_summary: str = ""
    learned_trends: list[str] = Field(default_factory=list)
    correction_memory: dict[str, dict[str, str]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIMessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    user_id: int | None = None


class AIMessageRead(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    used_context: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_admin_confirmation: bool
    action_request_id: int | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime


class AIActionRequestRead(BaseModel):
    id: int
    conversation_id: int
    message_id: int | None = None
    requested_action: str
    action_payload: str
    status: str
    requires_admin_confirmation: bool
    created_by_user_id: int | None = None
    confirmed_by_user_id: int | None = None
    confirmation_note: str
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIChatReplyResponse(AIResponsePayload):
    conversation_id: int
    user_message: AIMessageRead
    assistant_message: AIMessageRead
    action_request: AIActionRequestRead | None = None


class AIConversationClearResponse(BaseModel):
    status: str
    conversation_id: int
    deleted_messages: int
    deleted_action_requests: int
    deleted_audit_logs: int
