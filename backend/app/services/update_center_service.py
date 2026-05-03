import json
import hashlib
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import BASE_DIR, DATABASE_URL
from app.lora.service import lora_service
from app.services.log_service import log_action
from app.services.system_service import BACKEND_VERSION

PROJECT_ROOT = BASE_DIR.parent
FRONTEND_PACKAGE_PATH = PROJECT_ROOT / "frontend" / "package.json"
DATABASE_FILE_PATH = BASE_DIR / "aoj_command_os.db"
BACKUP_DIR = BASE_DIR / "backups"
FIRMWARE_DIR = BASE_DIR / "firmware"
FIRMWARE_PACKAGE_DIR = FIRMWARE_DIR / "packages"
FIRMWARE_MANIFEST_PATH = FIRMWARE_DIR / "index.json"
SYSTEM_VERSION = "0.1.0"
CHANGELOG = [
    "0.1.0 - Initial AOJ Command OS modular backend and tactical frontend scaffold.",
    "0.1.0 - Mission Control, Schedule, Results Board, Prop Network, Logs, System Monitor, AI Assistant added.",
    "0.1.0 - Update Center safe placeholders added. No destructive file replacement is enabled.",
    "0.1.0 - Firmware package upload and in-place prop rollout flow added (no AOJ reinstall required).",
]


def _ensure_firmware_dirs() -> None:
    FIRMWARE_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)


def _load_firmware_manifest() -> list[dict]:
    _ensure_firmware_dirs()
    if not FIRMWARE_MANIFEST_PATH.exists():
        return []
    try:
        payload = json.loads(FIRMWARE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _save_firmware_manifest(packages: list[dict]) -> None:
    _ensure_firmware_dirs()
    FIRMWARE_MANIFEST_PATH.write_text(
        json.dumps(packages, indent=2),
        encoding="utf-8",
    )


def _to_firmware_package_read(item: dict) -> schemas.FirmwarePackageRead:
    return schemas.FirmwarePackageRead(
        id=str(item.get("id", "")),
        filename=str(item.get("filename", "")),
        version=str(item.get("version", "")),
        size_bytes=int(item.get("size_bytes", 0)),
        sha256=str(item.get("sha256", "")),
        uploaded_at=str(item.get("uploaded_at", "")),
        notes=str(item.get("notes", "")),
    )


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
    firmware_packages = _load_firmware_manifest()
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
        if backups:
            latest_backup = backups[0].name

    last_firmware_rollout = None
    if firmware_packages:
        last_firmware_rollout = str(firmware_packages[0].get("uploaded_at") or "") or None

    return schemas.UpdateCenterStatusResponse(
        system_version=SYSTEM_VERSION,
        frontend_version=_read_frontend_version(),
        backend_version=BACKEND_VERSION,
        database_version=_read_database_version(db),
        database_path=str(DATABASE_FILE_PATH),
        latest_backup=latest_backup,
        firmware_packages_count=len(firmware_packages),
        last_firmware_rollout=last_firmware_rollout,
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


def list_firmware_packages() -> list[schemas.FirmwarePackageRead]:
    packages = _load_firmware_manifest()
    return [_to_firmware_package_read(item) for item in packages]


def upload_firmware_package(
    db: Session,
    filename: str,
    content: bytes,
    version: str,
    notes: str = "",
) -> schemas.FirmwarePackageRead:
    if not filename:
        raise ValueError("Firmware filename is required.")
    if not content:
        raise ValueError("Firmware file is empty.")
    if not version.strip():
        raise ValueError("Firmware version is required.")

    _ensure_firmware_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = Path(filename).name
    stored_name = f"{timestamp}_{safe_filename}"
    stored_path = FIRMWARE_PACKAGE_DIR / stored_name
    stored_path.write_bytes(content)

    checksum = hashlib.sha256(content).hexdigest()
    package_entry = {
        "id": uuid.uuid4().hex[:12],
        "filename": safe_filename,
        "stored_name": stored_name,
        "version": version.strip(),
        "size_bytes": len(content),
        "sha256": checksum,
        "uploaded_at": datetime.utcnow().isoformat(),
        "notes": notes.strip(),
    }

    packages = _load_firmware_manifest()
    packages.insert(0, package_entry)
    _save_firmware_manifest(packages)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="update_center",
        message=(
            f"Firmware package uploaded: {safe_filename} "
            f"(version {package_entry['version']}, {package_entry['size_bytes']} bytes)"
        ),
    )
    return _to_firmware_package_read(package_entry)


def apply_firmware_package(
    db: Session,
    payload: schemas.FirmwareApplyRequest,
) -> schemas.FirmwareApplyResponse:
    packages = _load_firmware_manifest()
    package = next((item for item in packages if item.get("id") == payload.package_id), None)
    if package is None:
        raise ValueError("Firmware package not found.")

    if payload.apply_all or not payload.prop_ids:
        target_props = db.query(models.Prop).all()
    else:
        target_props = (
            db.query(models.Prop)
            .filter(models.Prop.id.in_(payload.prop_ids))
            .all()
        )

    if not target_props:
        raise ValueError("No target props found for firmware rollout.")

    target_ids: list[int] = []
    firmware_value = f"{package['version']}|{package['stored_name']}|{package['sha256'][:16]}"
    for item in target_props:
        lora_service.send_command(item.device_id, "FIRMWARE_UPDATE", firmware_value)
        item.status = "maintenance"
        item.firmware_version = str(package["version"])
        item.last_seen = datetime.utcnow()
        target_ids.append(item.id)

    db.commit()

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="update_center",
        message=(
            f"Firmware rollout queued: version {package['version']} to "
            f"{len(target_ids)} prop(s)."
        ),
    )

    package_read = _to_firmware_package_read(package)
    return schemas.FirmwareApplyResponse(
        status="ok",
        message=(
            f"Firmware version {package_read.version} queued for "
            f"{len(target_ids)} prop(s)."
        ),
        package=package_read,
        targeted_props=target_ids,
        targeted_count=len(target_ids),
    )
