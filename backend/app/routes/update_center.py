from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import (
    UpdateCenterActionResponse,
    UpdateCenterStatusResponse,
    UpdatePackagePlaceholderRequest,
)
from app.services.update_center_service import (
    backup_database,
    get_update_center_status,
    restore_database_placeholder,
    rollback_placeholder,
    upload_update_package_placeholder,
)

router = APIRouter(prefix="/api/update-center", tags=["Update Center"])


@router.get("/status", response_model=UpdateCenterStatusResponse)
def update_center_status(db: Session = Depends(get_db)) -> UpdateCenterStatusResponse:
    return get_update_center_status(db)


@router.post("/backup", response_model=UpdateCenterActionResponse)
def create_database_backup(db: Session = Depends(get_db)) -> UpdateCenterActionResponse:
    return backup_database(db)


@router.post("/upload-placeholder", response_model=UpdateCenterActionResponse)
def upload_package_placeholder(
    payload: UpdatePackagePlaceholderRequest, db: Session = Depends(get_db)
) -> UpdateCenterActionResponse:
    return upload_update_package_placeholder(db, payload)


@router.post("/restore-placeholder", response_model=UpdateCenterActionResponse)
def restore_placeholder(db: Session = Depends(get_db)) -> UpdateCenterActionResponse:
    return restore_database_placeholder(db)


@router.post("/rollback-placeholder", response_model=UpdateCenterActionResponse)
def rollback_update_placeholder(db: Session = Depends(get_db)) -> UpdateCenterActionResponse:
    return rollback_placeholder(db)
