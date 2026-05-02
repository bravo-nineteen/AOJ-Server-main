import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIActionStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    expired = "expired"


class AIAuditDecision(str, enum.Enum):
    allow = "allow"
    requires_confirmation = "requires_confirmation"
    blocked = "blocked"


class AIRiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AIActionRequest(Base):
    __tablename__ = "ai_action_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id"), nullable=False, index=True
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_messages.id"), nullable=True, index=True
    )
    requested_action: Mapped[str] = mapped_column(String(160), nullable=False)
    action_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[AIActionStatus] = mapped_column(
        Enum(AIActionStatus), default=AIActionStatus.pending, nullable=False
    )
    requires_admin_confirmation: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    confirmation_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    conversation: Mapped["AIConversation"] = relationship(back_populates="action_requests")
    message: Mapped["AIMessage | None"] = relationship(
        back_populates="action_requests",
        foreign_keys=[message_id],
    )
    audit_logs: Mapped[list["AIAuditLog"]] = relationship(back_populates="action_request")


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id"), nullable=False, index=True
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_messages.id"), nullable=True, index=True
    )
    action_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_action_requests.id"), nullable=True, index=True
    )
    policy_name: Mapped[str] = mapped_column(String(80), default="advisory_only_v1", nullable=False)
    decision: Mapped[AIAuditDecision] = mapped_column(
        Enum(AIAuditDecision), default=AIAuditDecision.allow, nullable=False
    )
    risk_level: Mapped[AIRiskLevel] = mapped_column(
        Enum(AIRiskLevel), default=AIRiskLevel.low, nullable=False
    )
    prompt_excerpt: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    response_excerpt: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    used_context: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_actions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["AIConversation"] = relationship(back_populates="audit_logs")
    message: Mapped["AIMessage | None"] = relationship(back_populates="audit_logs")
    action_request: Mapped["AIActionRequest | None"] = relationship(back_populates="audit_logs")
