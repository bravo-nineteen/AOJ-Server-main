from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", database=db_status)
