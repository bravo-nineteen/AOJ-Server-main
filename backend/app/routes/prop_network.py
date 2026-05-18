import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Header, HTTPException

from app import models, schemas
from app.core.websocket import websocket_manager
from app.database import get_db
from app.lora.service import lora_service
from app.services.log_service import log_action

router = APIRouter(prefix="/api/props", tags=["Prop Network"])

FIRMWARE_PROP_TYPE_TO_NAME = {
    "Bomb": "prop_bomb",
    "Bomb Vest": "Bomb_Vest",
    "Briefcase Bomb": "Briefcase_Bomb",
    "Domination Point": "domination_point",
    "Respawn Station": "respawn_station",
    "Game Master Unit": "GM_Unit",
    "Control Panel Unit": "CP_Unit",
}


def _canonical_firmware_name(prop_type: str, name: str, device_id: str) -> str | None:
    base = FIRMWARE_PROP_TYPE_TO_NAME.get(prop_type)
    if not base:
        return None
    if base != "CP_Unit":
        return base

    lookup = f"{name} {device_id}".lower()
    if "tf" in lookup:
        return "CP_Unit_TF"
    if "bf" in lookup or "bt" in lookup:
        return "CP_Unit_BF"
    return "CP_Unit"


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.get("", response_model=list[schemas.PropRead])
def list_props(db: Session = Depends(get_db)):
    items = db.query(models.Prop).order_by(models.Prop.id.desc()).all()
    output = []
    changed = False

    for item in items:
        canonical_name = _canonical_firmware_name(
            str(item.prop_type.value),
            item.name,
            item.device_id,
        )
        if not canonical_name:
            continue
        if item.name != canonical_name:
            item.name = canonical_name
            changed = True
        output.append(item)

    if changed:
        db.commit()

    return output


@router.post("", response_model=schemas.PropRead)
def add_prop(payload: schemas.PropCreate, db: Session = Depends(get_db)):
    item_data = payload.model_dump(exclude={"auth_token"})
    item = models.Prop(**item_data)
    if payload.auth_token:
        item.auth_token_hash = _hash_token(payload.auth_token)
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_network",
        message=f"Prop added: {item.device_id} ({item.name})",
    )
    return item


@router.put("/{prop_id}", response_model=schemas.PropRead)
def edit_prop(prop_id: int, payload: schemas.PropUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    for key, value in payload.model_dump(exclude={"auth_token"}).items():
        setattr(item, key, value)
    if payload.auth_token:
        item.auth_token_hash = _hash_token(payload.auth_token)

    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_network",
        message=f"Prop updated: {item.device_id} ({item.name})",
    )
    return item


@router.post("/status-report", response_model=schemas.PropRead)
async def ingest_prop_status_report(
    payload: schemas.PropStatusReport,
    x_prop_token: str | None = Header(default=None, alias="X-Prop-Token"),
    db: Session = Depends(get_db),
):
    item = db.query(models.Prop).filter(models.Prop.device_id == payload.device_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found for device_id")

    if item.auth_token_hash:
        if not x_prop_token or _hash_token(x_prop_token) != item.auth_token_hash:
            raise HTTPException(status_code=401, detail="Invalid prop token")

    item.status = payload.status
    item.battery_level = payload.battery_level
    item.signal_strength = payload.signal_strength
    item.last_seen = datetime.now(timezone.utc)
    if payload.firmware_version:
        item.firmware_version = payload.firmware_version

    db.commit()
    db.refresh(item)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_status",
        message=(
            f"Status report {item.device_id}: status={item.status} "
            f"battery={item.battery_level}% signal={item.signal_strength}% via {payload.transport}"
        ),
    )

    await websocket_manager.broadcast(
        {
            "event": "prop.status_report",
            "payload": {
                "prop_id": item.id,
                "device_id": item.device_id,
                "name": item.name,
                "status": item.status,
                "battery_level": item.battery_level,
                "signal_strength": item.signal_strength,
                "last_status_report": item.last_seen.isoformat() if item.last_seen else None,
                "transport": payload.transport,
            },
        }
    )

    return item


@router.post("/{prop_id}/token/rotate")
def rotate_prop_token(prop_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    token = secrets.token_urlsafe(24)
    item.auth_token_hash = _hash_token(token)
    db.commit()

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.prop,
        source="prop_network",
        message=f"Prop token rotated: {item.device_id}",
    )
    return {"status": "ok", "device_id": item.device_id, "token": token}


@router.delete("/{prop_id}")
def delete_prop(prop_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    device_id = item.device_id
    name = item.name
    db.delete(item)
    db.commit()
    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.prop,
        source="prop_network",
        message=f"Prop deleted: {device_id} ({name})",
    )
    return {"status": "deleted", "prop_id": prop_id}


@router.post("/{prop_id}/command")
async def send_prop_command(
    prop_id: int,
    payload: schemas.PropCommandRequest,
    db: Session = Depends(get_db),
):
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    command_map = {
        "arm": "ARM",
        "disarm": "DISARM",
        "reset": "RESET",
        "status_request": "STATUS_REQUEST",
        "trigger_alarm": "TRIGGER_ALARM",
        "trigger": "TRIGGER",
        "game_start": "GAME_START",
        "game_end": "GAME_END",
        "ready": "READY",
        "test_buzz": "TEST_BUZZER",
        "test_buzzer": "TEST_BUZZER",
        "test_leds": "TEST_LEDS",
        "test_relay": "TEST_RELAY",
    }

    # Dispatch command to LoRa radio (mock in non-Pi mode).
    lora_service.send_command(item.device_id, command_map[payload.command])

    if payload.command == "arm":
        item.status = "armed"
    elif payload.command == "disarm":
        item.status = "disarmed"
    elif payload.command == "trigger" or payload.command == "trigger_alarm":
        item.status = "alarm"
    elif payload.command == "reset":
        item.status = "online"
    elif payload.command in ["test_buzz", "test_buzzer", "test_leds", "test_relay"]:
        pass  # Don't change status for test commands

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_network",
        message=f"Prop {item.device_id} command executed: {payload.command}",
    )
    db.commit()
    db.refresh(item)

    await websocket_manager.broadcast(
        {
            "event": "prop.command",
            "payload": {
                "prop_id": item.id,
                "device_id": item.device_id,
                "name": item.name,
                "command": payload.command,
                "status": item.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    )

    return {"status": "command_sent", "prop": schemas.PropRead.model_validate(item)}


# ─────────────────────────────────────────────────────────────────────────────
# Testing and Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{prop_id}/test/buzzer")
async def test_buzzer(prop_id: int, db: Session = Depends(get_db)):
    """Test the buzzer on a device."""
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    lora_service.send_command(item.device_id, "TEST_BUZZER")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_diagnostics",
        message=f"Buzzer test initiated: {item.device_id}",
    )

    return {"status": "test_initiated", "device_id": item.device_id, "test": "buzzer"}


@router.post("/{prop_id}/test/leds")
async def test_leds(prop_id: int, db: Session = Depends(get_db)):
    """Test the LEDs on a device."""
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    lora_service.send_command(item.device_id, "TEST_LEDS")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_diagnostics",
        message=f"LED test initiated: {item.device_id}",
    )

    return {"status": "test_initiated", "device_id": item.device_id, "test": "leds"}


@router.post("/{prop_id}/test/relay")
async def test_relay(prop_id: int, db: Session = Depends(get_db)):
    """Test the relay (horn) on a device."""
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    lora_service.send_command(item.device_id, "TEST_RELAY")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_diagnostics",
        message=f"Relay test initiated: {item.device_id}",
    )

    return {"status": "test_initiated", "device_id": item.device_id, "test": "relay"}


@router.post("/init/all")
async def initialize_all_props(db: Session = Depends(get_db)):
    """Initialize all built-in firmware devices."""
    devices = [
        {"device_id": "BD-001", "name": "prop_bomb", "prop_type": "Bomb", "location": "Arena Center"},
        {"device_id": "VEST-001", "name": "Bomb_Vest", "prop_type": "Bomb Vest", "location": "Player Loadout"},
        {"device_id": "CASE-001", "name": "Briefcase_Bomb", "prop_type": "Briefcase Bomb", "location": "Mission Control"},
        {"device_id": "DOM-001", "name": "domination_point", "prop_type": "Domination Point", "location": "Arena North"},
        {"device_id": "DOM-002", "name": "domination_point", "prop_type": "Domination Point", "location": "Arena South"},
        {"device_id": "RESP-001", "name": "respawn_station", "prop_type": "Respawn Station", "location": "Team Alpha Spawn"},
        {"device_id": "RESP-002", "name": "respawn_station", "prop_type": "Respawn Station", "location": "Team Bravo Spawn"},
        {"device_id": "GM-001", "name": "GM_Unit", "prop_type": "Game Master Unit", "location": "Control Room"},
        {"device_id": "CP-TF-001", "name": "CP_Unit_TF", "prop_type": "Control Panel Unit", "location": "Mission Control"},
        {"device_id": "CP-BF-001", "name": "CP_Unit_BF", "prop_type": "Control Panel Unit", "location": "Mission Control"},
    ]

    created = []
    existing = []
    updated = []
    for device in devices:
        existing_prop = db.query(models.Prop).filter(models.Prop.device_id == device["device_id"]).first()
        if existing_prop:
            changed = False
            if existing_prop.name != device["name"]:
                existing_prop.name = device["name"]
                changed = True
            if str(existing_prop.prop_type.value) != device["prop_type"]:
                existing_prop.prop_type = models.PropType(device["prop_type"])
                changed = True
            if changed:
                updated.append(existing_prop.device_id)
            existing.append(existing_prop.device_id)
        else:
            prop = models.Prop(**device, status="offline")
            db.add(prop)
            created.append(device["device_id"])

    db.commit()

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_init",
        message=(
            f"Initialized devices - Created: {len(created)}, Updated: {len(updated)}, "
            f"Already existed: {len(existing)}"
        ),
    )

    return {
        "status": "initialized",
        "created": created,
        "updated": updated,
        "existing": existing,
        "total": len(devices),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Device Status and Monitoring
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status/all")
def get_all_device_status(db: Session = Depends(get_db)) -> dict:
    """Get comprehensive status of all devices."""
    props = db.query(models.Prop).all()

    status_by_type = {}
    status_summary = {"online": 0, "offline": 0, "armed": 0, "alarm": 0}
    battery_stats = {"average": 0, "min": 100, "max": 0}
    signal_stats = {"average": 0, "min": 100, "max": 0}

    total_battery = 0
    total_signal = 0

    for prop in props:
        # Count status
        if prop.status in status_summary:
            status_summary[prop.status] += 1
        else:
            if prop.status not in status_summary:
                status_summary[prop.status] = 0
            status_summary[prop.status] += 1

        # Collect by type
        if prop.prop_type not in status_by_type:
            status_by_type[prop.prop_type] = []
        status_by_type[prop.prop_type].append({
            "id": prop.id,
            "device_id": prop.device_id,
            "name": prop.name,
            "status": prop.status,
            "battery_level": prop.battery_level,
            "signal_strength": prop.signal_strength,
            "firmware_version": prop.firmware_version,
            "last_seen": prop.last_seen.isoformat() if prop.last_seen else None,
        })

        # Battery stats
        total_battery += prop.battery_level
        battery_stats["min"] = min(battery_stats["min"], prop.battery_level)
        battery_stats["max"] = max(battery_stats["max"], prop.battery_level)

        # Signal stats
        total_signal += prop.signal_strength
        signal_stats["min"] = min(signal_stats["min"], prop.signal_strength)
        signal_stats["max"] = max(signal_stats["max"], prop.signal_strength)

    if props:
        battery_stats["average"] = round(total_battery / len(props), 1)
        signal_stats["average"] = round(total_signal / len(props), 1)

    return {
        "total_devices": len(props),
        "status_summary": status_summary,
        "battery_stats": battery_stats,
        "signal_stats": signal_stats,
        "devices_by_type": status_by_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{prop_id}/status/detail")
def get_device_detail(prop_id: int, db: Session = Depends(get_db)):
    """Get detailed status information for a specific device."""
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    return {
        "device_id": item.device_id,
        "name": item.name,
        "prop_type": item.prop_type,
        "location": item.location,
        "status": item.status,
        "battery_level": item.battery_level,
        "signal_strength": item.signal_strength,
        "firmware_version": item.firmware_version,
        "last_seen": item.last_seen.isoformat() if item.last_seen else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "health": {
            "battery_ok": item.battery_level > 20,
            "signal_ok": item.signal_strength > 30,
            "online": item.status != "offline",
        },
    }


@router.post("/scan/all")
async def scan_all_devices(db: Session = Depends(get_db)):
    """Broadcast status request to all devices."""
    props = db.query(models.Prop).all()

    for prop in props:
        lora_service.send_command(prop.device_id, "STATUS_REQUEST")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_scan",
        message=f"Broadcast status request to {len(props)} devices",
    )

    await websocket_manager.broadcast({
        "event": "prop.scan_initiated",
        "payload": {
            "device_count": len(props),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    })

    return {
        "status": "scan_initiated",
        "device_count": len(props),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{prop_id}/scan")
async def scan_device(prop_id: int, db: Session = Depends(get_db)):
    """Request status from a specific device."""
    item = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Prop not found")

    lora_service.send_command(item.device_id, "STATUS_REQUEST")

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.prop,
        source="prop_scan",
        message=f"Status request sent to device: {item.device_id}",
    )

    return {
        "status": "status_request_sent",
        "device_id": item.device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
