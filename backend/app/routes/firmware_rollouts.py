"""Routes for firmware rollout management."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/firmware-rollouts", tags=["Firmware Rollouts"])


@router.post("", response_model=schemas.FirmwareRolloutJobRead)
def create_firmware_rollout(
    payload: dict,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Create a new firmware rollout job."""
    rollout = models.FirmwareRolloutJob(**payload)
    db.add(rollout)
    db.commit()
    db.refresh(rollout)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="firmware",
        message=f"Firmware rollout created: v{payload.get('package_version')}",
    )

    return rollout


@router.get("", response_model=list[schemas.FirmwareRolloutJobRead])
def list_firmware_rollouts(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[schemas.FirmwareRolloutJobRead]:
    """List firmware rollouts."""
    query = db.query(models.FirmwareRolloutJob)

    if status:
        query = query.filter(models.FirmwareRolloutJob.status == status)

    rollouts = query.order_by(models.FirmwareRolloutJob.created_at.desc()).all()
    return rollouts


@router.get("/{rollout_id}", response_model=schemas.FirmwareRolloutJobRead)
def get_firmware_rollout(
    rollout_id: int,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Get firmware rollout by ID."""
    rollout = db.query(models.FirmwareRolloutJob).get(rollout_id)
    if not rollout:
        raise HTTPException(status_code=404, detail="Firmware rollout not found")
    return rollout


@router.put("/{rollout_id}", response_model=schemas.FirmwareRolloutJobRead)
def update_firmware_rollout(
    rollout_id: int,
    payload: dict,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Update firmware rollout status."""
    rollout = db.query(models.FirmwareRolloutJob).get(rollout_id)
    if not rollout:
        raise HTTPException(status_code=404, detail="Firmware rollout not found")

    for key, value in payload.items():
        if hasattr(rollout, key):
            setattr(rollout, key, value)

    db.commit()
    db.refresh(rollout)
    return rollout


@router.post("/{rollout_id}/start", response_model=schemas.FirmwareRolloutJobRead)
def start_firmware_rollout(
    rollout_id: int,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Start a firmware rollout."""
    rollout = db.query(models.FirmwareRolloutJob).get(rollout_id)
    if not rollout:
        raise HTTPException(status_code=404, detail="Firmware rollout not found")

    rollout.status = "in_progress"

    db.commit()
    db.refresh(rollout)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="firmware",
        message=f"Firmware rollout started: v{rollout.package_version}",
    )

    return rollout


@router.post("/{rollout_id}/complete", response_model=schemas.FirmwareRolloutJobRead)
def complete_firmware_rollout(
    rollout_id: int,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Complete a firmware rollout."""
    rollout = db.query(models.FirmwareRolloutJob).get(rollout_id)
    if not rollout:
        raise HTTPException(status_code=404, detail="Firmware rollout not found")

    rollout.status = "completed"

    db.commit()
    db.refresh(rollout)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="firmware",
        message=f"Firmware rollout completed: v{rollout.package_version}",
    )

    return rollout


@router.post("/{rollout_id}/cancel", response_model=schemas.FirmwareRolloutJobRead)
def cancel_firmware_rollout(
    rollout_id: int,
    db: Session = Depends(get_db),
) -> schemas.FirmwareRolloutJobRead:
    """Cancel a firmware rollout."""
    rollout = db.query(models.FirmwareRolloutJob).get(rollout_id)
    if not rollout:
        raise HTTPException(status_code=404, detail="Firmware rollout not found")

    rollout.status = "cancelled"

    db.commit()
    db.refresh(rollout)

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.system,
        source="firmware",
        message=f"Firmware rollout cancelled: v{rollout.package_version}",
    )

    return rollout
