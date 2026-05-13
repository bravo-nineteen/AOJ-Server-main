import json
import hashlib
import hmac
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import UPDATE_CENTER_SHARED_SECRET
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

_ALLOWED_UPDATE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".bin", ".img")
_MAX_UPDATE_PACKAGE_BYTES = 1_500_000_000  # 1.5 GB guardrail


def _validate_update_placeholder_payload(payload: schemas.UpdatePackagePlaceholderRequest) -> None:
    name = Path(payload.filename or "").name
    if not name or name != payload.filename:
        raise ValueError("Invalid filename. Path segments are not allowed.")
    if not any(name.lower().endswith(sfx) for sfx in _ALLOWED_UPDATE_SUFFIXES):
        raise ValueError("Unsupported package extension.")
    if payload.size_bytes <= 0:
        raise ValueError("Package size must be greater than zero.")
    if payload.size_bytes > _MAX_UPDATE_PACKAGE_BYTES:
        raise ValueError("Package size exceeds allowed limit.")


def _verify_update_signature(payload: schemas.UpdatePackagePlaceholderRequest) -> bool:
    secret = UPDATE_CENTER_SHARED_SECRET.strip()
    if not secret:
        return True

    signature = (payload.signature or "").strip().lower()
    if not signature:
        return False

    signed_blob = f"{payload.filename}:{payload.size_bytes}:{payload.manifest_sha256}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_blob, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


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


def _deserialize_targets(raw_targets: str) -> list[dict]:
    try:
        payload = json.loads(raw_targets)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _serialize_targets(targets: list[dict]) -> str:
    return json.dumps(targets, ensure_ascii=True)


def _rollout_status_from_counts(
    targeted_count: int,
    acknowledged_count: int,
    failed_count: int,
) -> str:
    if targeted_count <= 0:
        return "queued"
    if acknowledged_count >= targeted_count:
        return "completed"
    if failed_count >= targeted_count:
        return "failed"
    if acknowledged_count > 0 and failed_count > 0:
        return "partial"
    if acknowledged_count > 0:
        return "in_progress"
    if failed_count > 0:
        return "in_progress"
    return "queued"


def _to_rollout_job_read(job: models.FirmwareRolloutJob) -> schemas.FirmwareRolloutJobRead:
    targets = _deserialize_targets(job.targets_json)
    target_reads = [
        schemas.FirmwareRolloutTargetRead(
            prop_id=int(item.get("prop_id", 0)),
            device_id=str(item.get("device_id", "")),
            name=str(item.get("name", "")),
            status=str(item.get("status", "queued")),
            message=str(item.get("message", "")),
            updated_at=str(item.get("updated_at", "")),
        )
        for item in targets
    ]
    return schemas.FirmwareRolloutJobRead(
        id=job.id,
        package_id=job.package_id,
        package_version=job.package_version,
        package_filename=job.package_filename,
        status=job.status,
        targeted_count=job.targeted_count,
        acknowledged_count=job.acknowledged_count,
        failed_count=job.failed_count,
        targets=target_reads,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
    _validate_update_placeholder_payload(payload)
    if not _verify_update_signature(payload):
        raise ValueError("Invalid package signature for placeholder metadata.")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="update_center",
        message=(
            f"Offline update package placeholder received: {payload.filename} "
            f"({payload.size_bytes} bytes, sha256={payload.manifest_sha256[:12] or 'n/a'})"
        ),
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message=(
            f"Package '{payload.filename}' metadata verified and acknowledged. "
            "File replacement is disabled in placeholder mode."
        ),
        placeholder=True,
    )


def restore_database_placeholder(db: Session) -> schemas.UpdateCenterActionResponse:
    latest_backup = None
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            latest_backup = backups[0].name

    if latest_backup is None:
        raise ValueError("No backup found. Create a backup before restore placeholder requests.")

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="update_center",
        message=f"Database restore placeholder requested. latest_backup={latest_backup}",
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message=(
            "Restore placeholder acknowledged after precheck. "
            "No database files were modified."
        ),
        placeholder=True,
    )


def rollback_placeholder(db: Session) -> schemas.UpdateCenterActionResponse:
    if not DATABASE_FILE_PATH.exists():
        raise ValueError("Active database file is missing. Rollback placeholder is blocked.")

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="update_center",
        message="Rollback placeholder requested with safety precheck pass.",
    )
    return schemas.UpdateCenterActionResponse(
        status="placeholder",
        message="Rollback placeholder acknowledged after precheck. No files were changed.",
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
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
    rollout_targets: list[dict] = []
    for item in target_props:
        lora_service.send_command(item.device_id, "FIRMWARE_UPDATE", firmware_value)
        item.status = "maintenance"
        item.firmware_version = str(package["version"])
        item.last_seen = datetime.now(timezone.utc)
        target_ids.append(item.id)

        rollout_targets.append(
            {
                "prop_id": item.id,
                "device_id": item.device_id,
                "name": item.name,
                "status": "queued",
                "message": "Firmware update command queued.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    rollout_job = models.FirmwareRolloutJob(
        package_id=str(package["id"]),
        package_version=str(package["version"]),
        package_filename=str(package["filename"]),
        status="queued",
        targeted_count=len(target_ids),
        acknowledged_count=0,
        failed_count=0,
        targets_json=_serialize_targets(rollout_targets),
    )
    db.add(rollout_job)

    db.commit()
    db.refresh(rollout_job)

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
        rollout_job_id=rollout_job.id,
    )


def list_firmware_rollout_jobs(db: Session) -> list[schemas.FirmwareRolloutJobRead]:
    rows = (
        db.query(models.FirmwareRolloutJob)
        .order_by(models.FirmwareRolloutJob.id.desc())
        .limit(30)
        .all()
    )
    return [_to_rollout_job_read(item) for item in rows]


def get_firmware_rollout_job(db: Session, job_id: int) -> schemas.FirmwareRolloutJobRead | None:
    row = db.query(models.FirmwareRolloutJob).filter(models.FirmwareRolloutJob.id == job_id).first()
    if row is None:
        return None
    return _to_rollout_job_read(row)


def update_firmware_rollout_progress(
    db: Session,
    job_id: int,
    payload: schemas.FirmwareRolloutProgressUpdateRequest,
) -> schemas.FirmwareRolloutJobRead:
    row = db.query(models.FirmwareRolloutJob).filter(models.FirmwareRolloutJob.id == job_id).first()
    if row is None:
        raise ValueError("Firmware rollout job not found.")

    targets = _deserialize_targets(row.targets_json)
    target = next((item for item in targets if int(item.get("prop_id", 0)) == payload.prop_id), None)
    if target is None:
        raise ValueError("Target prop is not part of this rollout job.")

    target["status"] = payload.status
    target["message"] = payload.message.strip()
    target["updated_at"] = datetime.now(timezone.utc).isoformat()

    acknowledged_count = sum(1 for item in targets if item.get("status") == "acked")
    failed_count = sum(1 for item in targets if item.get("status") == "failed")
    row.acknowledged_count = acknowledged_count
    row.failed_count = failed_count
    row.status = _rollout_status_from_counts(row.targeted_count, acknowledged_count, failed_count)
    row.targets_json = _serialize_targets(targets)

    if payload.status == "acked":
        prop = db.query(models.Prop).filter(models.Prop.id == payload.prop_id).first()
        if prop is not None:
            prop.status = "online"
            prop.last_seen = datetime.now(timezone.utc)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="update_center",
        message=(
            f"Firmware rollout #{row.id} progress: prop {payload.prop_id} -> "
            f"{payload.status.upper()}"
        ),
    )

    db.commit()
    db.refresh(row)
    return _to_rollout_job_read(row)


def handle_firmware_ack_event(
    db: Session,
    device_id: str,
    ack_value: str,
    message_id: str,
) -> None:
    """Auto-update rollout target progress when a firmware ACK is received from a prop.
    
    This callback is invoked by the LoRa service when an ACK message arrives.
    It looks up the device, finds active rollout jobs, and marks targets as acked.
    
    Args:
        db: Database session.
        device_id: Device ID from the ACK message (e.g., "PROP_001").
        ack_value: ACK value from the message (e.g., "OK").
        message_id: Message ID that was acked.
    """
    try:
        prop = db.query(models.Prop).filter(models.Prop.device_id == device_id).first()
        if prop is None:
            # Device not found in database; log and continue.
            return

        # Find all non-completed rollout jobs that have this prop as a target.
        rollout_jobs = (
            db.query(models.FirmwareRolloutJob)
            .filter(models.FirmwareRolloutJob.status.notin_(["completed", "failed"]))
            .all()
        )

        for job in rollout_jobs:
            targets = _deserialize_targets(job.targets_json)
            target = next((item for item in targets if int(item.get("prop_id", 0)) == prop.id), None)
            if target is None:
                continue

            # Skip if already acked or failed.
            if target.get("status") in ["acked", "failed"]:
                continue

            # Update target status to acked.
            target["status"] = "acked"
            target["message"] = f"Acknowledged via LoRa message {message_id}: {ack_value}"
            target["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Recalculate job aggregate status from all targets.
            acknowledged_count = sum(1 for item in targets if item.get("status") == "acked")
            failed_count = sum(1 for item in targets if item.get("status") == "failed")
            job.acknowledged_count = acknowledged_count
            job.failed_count = failed_count
            job.status = _rollout_status_from_counts(job.targeted_count, acknowledged_count, failed_count)
            job.targets_json = _serialize_targets(targets)

            # Update prop status.
            prop.status = "online"
            prop.last_seen = datetime.now(timezone.utc)

            log_action(
                db,
                level=models.LogLevel.info,
                category=models.LogCategory.update,
                source="update_center",
                message=(
                    f"Firmware rollout #{job.id} auto-progressed: prop {prop.id} "
                    f"({prop.name}) -> acked via LoRa."
                ),
            )

        db.commit()

    except Exception as e:
        # Log but don't raise to avoid breaking the LoRa service.
        import traceback
        traceback.print_exc()
