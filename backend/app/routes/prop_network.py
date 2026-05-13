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


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.get("", response_model=list[schemas.PropRead])
def list_props(db: Session = Depends(get_db)):
    return db.query(models.Prop).order_by(models.Prop.id.desc()).all()


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
        "game_start": "GAME_START",
        "game_end": "GAME_END",
        "ready": "READY",
        "test_buzz": "TEST",
    }

    # Dispatch command to LoRa radio (mock in non-Pi mode).
    lora_service.send_command(item.device_id, command_map[payload.command])

    if payload.command == "arm":
        item.status = "armed"
    elif payload.command == "disarm":
        item.status = "disarmed"
    elif payload.command == "reset":
        item.status = "online"
    elif payload.command == "trigger_alarm":
        item.status = "alarm"

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
