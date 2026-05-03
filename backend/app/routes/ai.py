from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app import models, schemas
from app.database import get_db
from app.services.ai_chat_service import (
    clear_conversation,
    create_conversation,
    get_conversation,
    list_action_requests,
    list_conversations,
    list_messages,
    send_message,
    to_conversation_read,
)
from app.services.log_service import log_action

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


@router.post("/conversations", response_model=schemas.AIConversationRead)
def create_ai_conversation(
    payload: schemas.AIConversationCreateRequest,
    db: Session = Depends(get_db),
) -> schemas.AIConversationRead:
    row = create_conversation(db, payload)
    return to_conversation_read(row)


@router.get("/conversations", response_model=list[schemas.AIConversationRead])
def get_ai_conversations(db: Session = Depends(get_db)) -> list[schemas.AIConversationRead]:
    rows = list_conversations(db)
    return [to_conversation_read(row) for row in rows]


@router.get("/conversations/{conversation_id}", response_model=schemas.AIConversationRead)
def get_ai_conversation(conversation_id: int, db: Session = Depends(get_db)) -> schemas.AIConversationRead:
    row = get_conversation(db, conversation_id)
    return to_conversation_read(row)


@router.get("/conversations/{conversation_id}/messages", response_model=list[schemas.AIMessageRead])
def get_ai_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.AIMessageRead]:
    return list_messages(db, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.AIChatReplyResponse,
)
def post_ai_message(
    conversation_id: int,
    payload: schemas.AIMessageCreateRequest,
    db: Session = Depends(get_db),
) -> schemas.AIChatReplyResponse:
    reply = send_message(db, conversation_id, payload)

    # Store only summary metadata in system log. Prompt text is intentionally omitted.
    log_action(
        db,
        level=(
            models.LogLevel.warning
            if reply.requires_admin_confirmation
            else models.LogLevel.info
        ),
        category=models.LogCategory.ai,
        source="ai_chat",
        message=(
            f"AI chat reply generated; conversation_id={reply.conversation_id}; "
            f"requires_admin_confirmation={reply.requires_admin_confirmation}; "
            f"blocked_actions={len(reply.blocked_actions)}"
        ),
    )

    return reply


@router.get("/action-requests", response_model=list[schemas.AIActionRequestRead])
def get_ai_action_requests(db: Session = Depends(get_db)) -> list[schemas.AIActionRequestRead]:
    rows = list_action_requests(db)
    return [schemas.AIActionRequestRead.model_validate(row) for row in rows]


@router.post("/conversations/{conversation_id}/clear", response_model=schemas.AIConversationClearResponse)
def clear_ai_conversation(conversation_id: int, db: Session = Depends(get_db)) -> schemas.AIConversationClearResponse:
    return clear_conversation(db, conversation_id)


@router.post("/ask", response_model=schemas.AIAskResponse)
def ai_ask(payload: schemas.AIAskRequest, db: Session = Depends(get_db)) -> schemas.AIAskResponse:
    conversation = create_conversation(
        db,
        schemas.AIConversationCreateRequest(title="Quick Ask", mission_id=None, user_id=None),
    )
    reply = send_message(
        db,
        conversation.id,
        schemas.AIMessageCreateRequest(content=payload.prompt, user_id=None),
    )

    return schemas.AIAskResponse(
        answer=reply.answer,
        confidence=reply.confidence,
        used_context=reply.used_context,
        suggested_actions=reply.suggested_actions,
        blocked_actions=reply.blocked_actions,
        warnings=reply.warnings,
        requires_admin_confirmation=reply.requires_admin_confirmation,
        advisory_only=True,
        blocked_action=reply.requires_admin_confirmation,
        safety_notice=(
            "Advisory only. No hardware command is executed. "
            "Admin confirmation is required before any operational action."
        ),
        model=reply.assistant_message.model or "advisor",
    )
