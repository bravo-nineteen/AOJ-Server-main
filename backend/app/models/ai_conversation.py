import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    mission_id: Mapped[int | None] = mapped_column(
        ForeignKey("missions.id"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    memory_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    learned_trends: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User | None"] = relationship(back_populates="conversations")
    mission: Mapped["Mission | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation", order_by="AIMessage.created_at"
    )
    action_requests: Mapped[list["AIActionRequest"]] = relationship(
        back_populates="conversation"
    )
    audit_logs: Mapped[list["AIAuditLog"]] = relationship(back_populates="conversation")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole), default=MessageRole.user, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    used_context: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    suggested_actions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_actions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    warnings: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_action: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_admin_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_action_requests.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")
    action_requests: Mapped[list["AIActionRequest"]] = relationship(
        back_populates="message",
        foreign_keys="AIActionRequest.message_id",
    )
    linked_action_request: Mapped["AIActionRequest | None"] = relationship(
        foreign_keys=[action_request_id]
    )
    audit_logs: Mapped[list["AIAuditLog"]] = relationship(back_populates="message")
