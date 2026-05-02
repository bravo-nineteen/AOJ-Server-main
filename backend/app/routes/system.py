from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import SystemStatusResponse
from app.services.system_service import get_system_status

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    return get_system_status(db)
