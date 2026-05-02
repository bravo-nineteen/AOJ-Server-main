import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.websocket import websocket_manager
from app.schemas import SystemStatusResponse

STARTED_AT = datetime.now(tz=timezone.utc)
BACKEND_VERSION = "0.1.0"
_CPU_SAMPLE: dict[str, int] | None = None


def _is_raspberry_pi() -> bool:
    model_path = Path("/proc/device-tree/model")
    if not model_path.exists():
        return False
    try:
        model = model_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "Raspberry Pi" in model


def _read_cpu_temperature() -> float:
    temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if not temp_path.exists():
        return 0.0
    try:
        milli_c = int(temp_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0.0
    return round(milli_c / 1000.0, 2)


def _sample_cpu() -> dict[str, int]:
    stat_path = Path("/proc/stat")
    first_line = stat_path.read_text(encoding="utf-8").splitlines()[0]
    values = [int(part) for part in first_line.split()[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return {"idle": idle, "total": total}


def _read_cpu_usage_percent() -> float:
    global _CPU_SAMPLE
    try:
        current = _sample_cpu()
    except (OSError, ValueError, IndexError):
        return 0.0

    if _CPU_SAMPLE is None:
        _CPU_SAMPLE = current
        return 0.0

    delta_total = current["total"] - _CPU_SAMPLE["total"]
    delta_idle = current["idle"] - _CPU_SAMPLE["idle"]
    _CPU_SAMPLE = current
    if delta_total <= 0:
        return 0.0
    usage = 100.0 * (1.0 - (delta_idle / delta_total))
    return round(max(0.0, min(100.0, usage)), 2)


def _read_ram_usage_percent() -> float:
    meminfo_path = Path("/proc/meminfo")
    content = meminfo_path.read_text(encoding="utf-8")
    fields: dict[str, int] = {}
    for line in content.splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        value_part = parts[1].strip().split()[0]
        try:
            fields[key] = int(value_part)
        except ValueError:
            continue

    total = fields.get("MemTotal", 0)
    available = fields.get("MemAvailable", 0)
    if total <= 0:
        return 0.0
    used_ratio = (total - available) / total
    return round(max(0.0, min(100.0, used_ratio * 100.0)), 2)


def _read_disk_usage_percent() -> float:
    usage = shutil.disk_usage("/")
    if usage.total <= 0:
        return 0.0
    return round((usage.used / usage.total) * 100.0, 2)


def _read_system_uptime_seconds() -> float:
    uptime_path = Path("/proc/uptime")
    if uptime_path.exists():
        try:
            return float(uptime_path.read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            pass
    return (datetime.now(tz=timezone.utc) - STARTED_AT).total_seconds()


def _get_database_status(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "error"


def _get_lora_service_status() -> str:
    try:
        from app.lora.service import lora_service

        mode = "mock" if lora_service.mock_mode else "hardware"
        pending = lora_service.pending_ack_count
        return f"online:{mode}:pending_ack={pending}"
    except Exception:
        return "unavailable"


def get_system_status(db: Session) -> SystemStatusResponse:
    now = datetime.now(tz=timezone.utc)
    running_on_pi = _is_raspberry_pi()

    entity_counts = {
        "devices": db.query(func.count(models.Device.id)).scalar() or 0,
        "missions": db.query(func.count(models.Mission.id)).scalar() or 0,
        "game_sessions": db.query(func.count(models.GameSession.id)).scalar() or 0,
        "teams": db.query(func.count(models.Team.id)).scalar() or 0,
        "score_events": db.query(func.count(models.ScoreEvent.id)).scalar() or 0,
        "schedule_items": db.query(func.count(models.ScheduleItem.id)).scalar() or 0,
        "system_logs": db.query(func.count(models.SystemLog.id)).scalar() or 0,
        "user_roles": db.query(func.count(models.UserRole.id)).scalar() or 0,
    }

    active_game_sessions = (
        db.query(func.count(models.GameSession.id))
        .filter(models.GameSession.is_active.is_(True))
        .scalar()
        or 0
    )

    if running_on_pi:
        cpu_temperature_c = _read_cpu_temperature()
        cpu_usage_percent = _read_cpu_usage_percent()
        ram_usage_percent = _read_ram_usage_percent()
        disk_usage_percent = _read_disk_usage_percent()
        uptime_seconds = _read_system_uptime_seconds()
        platform_mode = "raspberry_pi"
    else:
        uptime_seconds = (now - STARTED_AT).total_seconds()
        cpu_temperature_c = 51.4
        cpu_usage_percent = 22.8
        ram_usage_percent = 37.6
        disk_usage_percent = 43.2
        platform_mode = "mock"

    return SystemStatusResponse(
        status="online",
        uptime_seconds=uptime_seconds,
        connected_clients=websocket_manager.connected_count,
        active_game_sessions=active_game_sessions,
        entity_counts=entity_counts,
        backend_version=BACKEND_VERSION,
        platform_mode=platform_mode,
        cpu_temperature_c=cpu_temperature_c,
        cpu_usage_percent=cpu_usage_percent,
        ram_usage_percent=ram_usage_percent,
        disk_usage_percent=disk_usage_percent,
        lora_service_status=_get_lora_service_status(),
        database_status=_get_database_status(db),
    )
