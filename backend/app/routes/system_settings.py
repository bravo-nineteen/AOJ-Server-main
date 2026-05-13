"""Routes for system settings management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/system-settings", tags=["System Settings"])


@router.post("", response_model=schemas.SystemSettingRead)
def create_system_setting(
    payload: schemas.SystemSettingCreate,
    db: Session = Depends(get_db),
) -> schemas.SystemSettingRead:
    """Create or update a system setting."""
    setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.key == payload.key
    ).first()

    if setting:
        setting.value = payload.value
        setting.description = payload.description or setting.description
    else:
        setting = models.SystemSetting(**payload.model_dump())
        db.add(setting)

    db.commit()
    db.refresh(setting)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="settings",
        message=f"Setting updated: {payload.key}",
    )

    return setting


@router.get("", response_model=list[schemas.SystemSettingRead])
def list_system_settings(
    db: Session = Depends(get_db),
) -> list[schemas.SystemSettingRead]:
    """List all system settings."""
    settings = db.query(models.SystemSetting).all()
    return settings


@router.get("/{setting_key}", response_model=schemas.SystemSettingRead)
def get_system_setting(
    setting_key: str,
    db: Session = Depends(get_db),
) -> schemas.SystemSettingRead:
    """Get a specific system setting by key."""
    setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.key == setting_key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    return setting


@router.put("/{setting_key}", response_model=schemas.SystemSettingRead)
def update_system_setting(
    setting_key: str,
    payload: schemas.SystemSettingUpdate,
    db: Session = Depends(get_db),
) -> schemas.SystemSettingRead:
    """Update a system setting."""
    setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.key == setting_key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, key, value)

    db.commit()
    db.refresh(setting)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="settings",
        message=f"Setting updated: {setting_key}",
    )

    return setting


@router.delete("/{setting_key}", status_code=204)
def delete_system_setting(
    setting_key: str,
    db: Session = Depends(get_db),
) -> None:
    """Delete a system setting."""
    setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.key == setting_key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    db.delete(setting)
    db.commit()

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="settings",
        message=f"Setting deleted: {setting_key}",
    )
