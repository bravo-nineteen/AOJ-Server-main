import json
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import BASE_DIR, DATABASE_URL
from app.services.log_service import log_action
from app.services.system_service import BACKEND_VERSION

PROJECT_ROOT = BASE_DIR.parent
FRONTEND_PACKAGE_PATH = PROJECT_ROOT / "frontend" / "package.json"
DATABASE_FILE_PATH = BASE_DIR / "aoj_command_os.db"
BACKUP_DIR = BASE_DIR / "backups"
SYSTEM_VERSION = "0.1.0"
CHANGELOG = [
    "0.1.0 - Initial AOJ Command OS modular backend and tactical frontend scaffold.",
    "0.1.0 - Mission Control, Schedule, Results Board, Prop Network, Logs, System Monitor, AI Assistant added.",
    "0.1.0 - Update Center safe placeholders added. No destructive file replacement is enabled.",
]


def _read_frontend_version() -> str:
    if not FRONTEND_PACKAGE_PATH.exists():
        return "unknown"
    try:
        payload = json.loads(FRONTEND_PACKAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return str(payload.get("version", "unknown"))


def _read_database_version(db: Session) -> str:
    try:
        version = db.execute(text("PRAGMA user_version")).scalar()
    except Exception:
        return "unknown"
    return str(version or 0)


def get_update_center_status(db: Session) -> schemas.UpdateCenterStatusResponse:
    latest_backup = None
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
        if backups:
            latest_backup = backups[0].name

    return schemas.UpdateCenterStatusResponse(
        system_version=SYSTEM_VERSION,
        frontend_version=_read_frontend_version(),
        backend_version=BACKEND_VERSION,
        database_version=_read_database_version(db),
        database_path=str(DATABASE_FILE_PATH),
        latest_backup=latest_backup,
        changelog=CHANGELOG,
    )


def backup_database(db: Session) -> schemas.UpdateCenterActionResponse:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"aoj_command_os_backup_{timestamp}.db"
    shutil.copy2(DATABASE_FILE_PATH, backup_path)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="update_center",
        message=f"Database backup created: {backup_path.name}",
    )
    return schemas.UpdateCenterActionResponse(
        status="ok",
        message=f"Database backup created at {backup_path.name}",
        placeholder=False,
    )


def upload_update_package_placeholder(
    db: Session, payload: schemas.UpdatePackagePlaceholderRequest
) -> schemas.UpdateCenterActionResponse:
    # TODO: Validate package signature and manifest before any future install support.
    # TODO: Store package safely outside runtime directories before verification.
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="update_center",
        message=(
            f"Offline update package placeholder received: {payload.filename} "
            f"({payload.size_bytes} bytes)"
        ),
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message=(
            f"Package '{payload.filename}' acknowledged. File replacement is disabled. "
            "TODO: implement verified offline installer flow."
        ),
        placeholder=True,
    )


def restore_database_placeholder(db: Session) -> schemas.UpdateCenterActionResponse:
    # TODO: Require explicit operator approval and pre-restore validation.
    # TODO: Restore into a staged copy and verify schema compatibility before swap.
    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="update_center",
        message="Database restore placeholder requested.",
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message="Restore placeholder acknowledged. No database files were modified.",
        placeholder=True,
    )


def rollback_placeholder(db: Session) -> schemas.UpdateCenterActionResponse:
    # TODO: Implement versioned release manifest and rollback safety checks.
    # TODO: Require admin approval and backup verification before enabling rollback.
    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="update_center",
        message="Rollback placeholder requested.",
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message="Rollback placeholder acknowledged. No files were changed.",
        placeholder=True,
    )
