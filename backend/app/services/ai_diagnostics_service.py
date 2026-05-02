import re
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models

_LAST_SEEN_STALE_MINUTES = 10
_MAX_LOG_SCAN = 50


def _find_device_in_prompt(db: Session, prompt: str) -> models.Device | None:
    text = prompt.lower()

    # Try explicit device code patterns first (e.g., B01, D12, PROP-3).
    token_match = re.search(r"\b([a-z]{1,5}[-_]?\d{1,4})\b", text)
    if token_match:
        token = token_match.group(1).upper()
        device = (
            db.query(models.Device)
            .filter(models.Device.device_id == token)
            .first()
        )
        if device is not None:
            return device

    # Fallback: any device id mentioned in text.
    candidates = db.query(models.Device).all()
    for item in candidates:
        if item.device_id.lower() in text or item.name.lower() in text:
            return item

    return None


def analyze_device_status(db: Session, prompt: str) -> dict:
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(minutes=_LAST_SEEN_STALE_MINUTES)

    target = _find_device_in_prompt(db, prompt)
    all_devices = db.query(models.Device).all()

    offline_devices = [d for d in all_devices if d.status == models.DeviceStatus.offline]
    stale_devices = [
        d for d in all_devices if d.last_seen is None or d.last_seen < stale_cutoff
    ]

    warnings: list[str] = []
    facts: list[str] = []
    suggestions: list[str] = []

    facts.append(f"Devices online={len(all_devices) - len(offline_devices)} offline={len(offline_devices)}.")

    if target is None and ("bomb" in prompt.lower() or "device" in prompt.lower() or "prop" in prompt.lower()):
        warnings.append("Requested device could not be identified from the prompt.")
        suggestions.append("Specify exact device_id (example: B01) to run targeted diagnostics.")
        return {
            "facts": facts,
            "warnings": warnings,
            "suggestions": suggestions,
            "issues": [],
            "target_device": None,
        }

    issues: list[str] = []
    if target is not None:
        facts.append(f"Target device {target.device_id} status={target.status.value}.")
        if target.last_seen is None:
            issues.append("Device has never reported last_seen telemetry.")
            warnings.append(f"{target.device_id} has no last_seen timestamp.")
        else:
            facts.append(f"Target last_seen={target.last_seen.isoformat()}Z.")
            if target.last_seen < stale_cutoff:
                issues.append("Device telemetry is stale.")
                warnings.append(
                    f"{target.device_id} last_seen is older than {_LAST_SEEN_STALE_MINUTES} minutes."
                )

        if target.status == models.DeviceStatus.offline:
            issues.append("Device is offline.")
            warnings.append(f"{target.device_id} is offline.")
            suggestions.append("Check power, battery, and LoRa/Wi-Fi link before retrying commands.")

        recent_logs = (
            db.query(models.SystemLog)
            .filter(
                models.SystemLog.device_id == target.id,
                models.SystemLog.level.in_([models.LogLevel.error, models.LogLevel.critical]),
            )
            .order_by(models.SystemLog.created_at.desc(), models.SystemLog.id.desc())
            .limit(5)
            .all()
        )
        if recent_logs:
            issues.append("Recent error/critical device logs exist.")
            warnings.append(
                f"{target.device_id} has {len(recent_logs)} recent error/critical logs."
            )
            suggestions.append("Review latest device log events and verify ACK/retry status.")

    if stale_devices:
        warnings.append(f"{len(stale_devices)} device(s) have stale telemetry.")

    return {
        "facts": facts,
        "warnings": warnings,
        "suggestions": suggestions,
        "issues": issues,
        "target_device": target.device_id if target is not None else None,
    }


def analyze_logs(db: Session) -> dict:
    rows = db.execute(
        text(
            "SELECT level, category, message, created_at "
            "FROM system_logs "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT :limit_rows"
        ),
        {"limit_rows": _MAX_LOG_SCAN},
    ).fetchall()

    critical = [row for row in rows if str(row[0]).upper() == "CRITICAL"]
    errors = [row for row in rows if str(row[0]).upper() == "ERROR"]

    warnings: list[str] = []
    facts: list[str] = [
        f"Recent logs scanned={len(rows)} critical={len(critical)} error={len(errors)}."
    ]
    suggestions: list[str] = []

    if critical:
        warnings.append(f"Critical logs present: {len(critical)} in recent history.")
        suggestions.append("Prioritize investigation of critical logs before new game operations.")

    if len(errors) >= 3:
        warnings.append("Multiple recent error logs detected.")
        suggestions.append("Correlate error timestamps with device/session events.")

    top_messages = [f"{str(row[1]).upper()}:{str(row[2])[:100]}" for row in rows[:10]]

    return {
        "facts": facts,
        "warnings": warnings,
        "suggestions": suggestions,
        "top_messages": top_messages,
    }


def analyze_schedule(db: Session, mission_id: int | None = None) -> dict:
    now = datetime.utcnow()
    query = db.query(models.ScheduleItem)
    if mission_id is not None:
        query = query.filter(models.ScheduleItem.mission_id == mission_id)

    items = query.order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc()).all()

    current = next(
        (
            item
            for item in items
            if not item.is_complete and item.start_time <= now <= item.end_time
        ),
        None,
    )
    next_item = next(
        (item for item in items if not item.is_complete and item.start_time > now),
        None,
    )

    warnings: list[str] = []
    facts: list[str] = []
    suggestions: list[str] = []

    if current is not None:
        facts.append(f"Current activity: {current.title} ({current.activity_type}).")
        if now > current.end_time:
            warnings.append("Current activity has exceeded planned end time.")
            suggestions.append("Announce delay mitigation and compress non-critical activities.")
    else:
        warnings.append("No active schedule item is currently running.")

    if next_item is not None:
        facts.append(f"Next activity: {next_item.title} at {next_item.start_time.isoformat()}Z.")
    else:
        warnings.append("No next schedule activity found.")
        suggestions.append("Add the next schedule block to maintain flow.")

    behind_schedule = any(
        not item.is_complete and item.end_time < now for item in items
    )
    if behind_schedule:
        warnings.append("Schedule appears behind plan.")
        suggestions.append("Re-plan timeline and communicate revised start times.")

    return {
        "facts": facts,
        "warnings": warnings,
        "suggestions": suggestions,
        "behind_schedule": behind_schedule,
    }


def analyze_mission_state(mission_control_state: dict, active_session: models.GameSession | None) -> dict:
    game_state = str(mission_control_state.get("state", "idle"))
    timer_remaining = int(mission_control_state.get("main_timer_seconds", 0) or 0)

    warnings: list[str] = []
    facts: list[str] = [
        f"Mission control state={game_state}.",
        f"Timer remaining={timer_remaining}s.",
    ]
    suggestions: list[str] = []

    if game_state == "running" and active_session is None:
        warnings.append("Game state is running but no active session exists.")
        suggestions.append("Reconcile mission control state with game session records.")

    if active_session is not None and game_state == "idle":
        warnings.append("Active session exists while mission control is idle.")
        suggestions.append("Close stale session or resume mission control to match reality.")

    if timer_remaining > 0 and active_session is None:
        warnings.append("Timer is running without an active session.")

    return {
        "facts": facts,
        "warnings": warnings,
        "suggestions": suggestions,
    }
