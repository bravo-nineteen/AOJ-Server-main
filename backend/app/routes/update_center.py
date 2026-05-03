from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.database import get_db
from app.schemas import (
    FirmwareApplyRequest,
    FirmwareApplyResponse,
    FirmwarePackageRead,
    FirmwareRolloutJobRead,
    FirmwareRolloutProgressUpdateRequest,
    UpdateCenterActionResponse,
    UpdateCenterStatusResponse,
    UpdatePackagePlaceholderRequest,
)
from app.services.update_center_service import (
    apply_firmware_package,
    backup_database,
    get_firmware_rollout_job,
    get_update_center_status,
    list_firmware_packages,
    list_firmware_rollout_jobs,
    restore_database_placeholder,
    rollback_placeholder,
    update_firmware_rollout_progress,
    upload_firmware_package,
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


@router.get("/firmware-packages", response_model=list[FirmwarePackageRead])
def get_firmware_packages() -> list[FirmwarePackageRead]:
    return list_firmware_packages()


@router.post("/firmware-upload", response_model=FirmwarePackageRead)
async def upload_firmware(
    file: UploadFile = File(...),
    version: str = Form(...),
    notes: str = Form(default=""),
    db: Session = Depends(get_db),
) -> FirmwarePackageRead:
    content = await file.read()
    try:
        return upload_firmware_package(
            db,
            filename=file.filename or "firmware.bin",
            content=content,
            version=version,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/firmware-apply", response_model=FirmwareApplyResponse)
def apply_firmware(
    payload: FirmwareApplyRequest,
    db: Session = Depends(get_db),
) -> FirmwareApplyResponse:
    try:
        return apply_firmware_package(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/firmware-rollouts", response_model=list[FirmwareRolloutJobRead])
def get_firmware_rollouts(db: Session = Depends(get_db)) -> list[FirmwareRolloutJobRead]:
    return list_firmware_rollout_jobs(db)


@router.get("/firmware-rollouts/{job_id}", response_model=FirmwareRolloutJobRead)
def get_firmware_rollout(job_id: int, db: Session = Depends(get_db)) -> FirmwareRolloutJobRead:
    row = get_firmware_rollout_job(db, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Firmware rollout job not found.")
    return row


@router.post("/firmware-rollouts/{job_id}/progress", response_model=FirmwareRolloutJobRead)
def update_rollout_progress(
    job_id: int,
    payload: FirmwareRolloutProgressUpdateRequest,
    db: Session = Depends(get_db),
) -> FirmwareRolloutJobRead:
    try:
        return update_firmware_rollout_progress(db, job_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
