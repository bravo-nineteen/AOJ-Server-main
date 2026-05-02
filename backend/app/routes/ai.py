import re

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app import models, schemas
from app.database import get_db
from app.services.ai_service import ask_ai
from app.services.log_service import log_action

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_for_log(text: str) -> str:
    """Strip control characters to prevent log injection."""
    return _CONTROL_CHARS.sub("", text)


@router.post("/ask", response_model=schemas.AIAskResponse)
def ai_ask(payload: schemas.AIAskRequest, db: Session = Depends(get_db)) -> schemas.AIAskResponse:
    response = ask_ai(payload.prompt)

    log_level = models.LogLevel.warning if response.requires_admin_confirmation else models.LogLevel.info
    safe_prompt = _sanitize_for_log(payload.prompt[:120])
    log_action(
        db,
        level=log_level,
        category=models.LogCategory.ai,
        source="ai_assistant",
        message=f"AI ask handled. blocked_action={response.blocked_action}; prompt={safe_prompt}",
    )

    return response
