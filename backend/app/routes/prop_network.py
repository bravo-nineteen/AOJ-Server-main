from datetime import datetime

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action
from app.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/props", tags=["Prop Network"])


@router.get("", response_model=list[schemas.PropRead])
def list_props(db: Session = Depends(get_db)):
    return db.query(models.Prop).order_by(models.Prop.id.desc()).all()


@router.post("", response_model=schemas.PropRead)
def add_prop(payload: schemas.PropCreate, db: Session = Depends(get_db)):
    item = models.Prop(**payload.model_dump())
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

    for key, value in payload.model_dump().items():
        setattr(item, key, value)

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

    item.last_seen = datetime.utcnow()
    if payload.command == "arm":
        item.status = "armed"
    if payload.command == "disarm":
        item.status = "disarmed"
    if payload.command == "reset":
        item.status = "online"
    if payload.command == "trigger_alarm":
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
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    )

    return {"status": "command_sent", "prop": schemas.PropRead.model_validate(item)}
