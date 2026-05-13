import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db

logger = logging.getLogger(__name__)
from app.lora.service import lora_service
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning("Database health check failed: %s", str(e))
        db_status = "error"
    lora_diag = lora_service.diagnostics()
    return HealthResponse(status="ok", database=db_status, lora=lora_diag)
