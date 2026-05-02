from datetime import datetime

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/schedule", tags=["Schedule"])


@router.get("/items", response_model=list[schemas.ScheduleItemRead])
def list_schedule_items(db: Session = Depends(get_db)):
    return (
        db.query(models.ScheduleItem)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .all()
    )


@router.post("/items", response_model=schemas.ScheduleItemRead)
def add_schedule_item(payload: schemas.ScheduleItemCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    item = models.ScheduleItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="schedule",
        message=f"Schedule item added: {item.title} ({item.activity_type})",
    )
    return item


@router.put("/items/{item_id}", response_model=schemas.ScheduleItemRead)
def edit_schedule_item(
    item_id: int, payload: schemas.ScheduleItemUpdate, db: Session = Depends(get_db)
):
    item = db.query(models.ScheduleItem).filter(models.ScheduleItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.completed_at = datetime.utcnow() if payload.is_complete else None
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="schedule",
        message=f"Schedule item edited: id={item.id} title={item.title}",
    )
    return item


@router.delete("/items/{item_id}")
def delete_schedule_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ScheduleItem).filter(models.ScheduleItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    title = item.title
    db.delete(item)
    db.commit()
    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.update,
        source="schedule",
        message=f"Schedule item deleted: id={item_id} title={title}",
    )
    return {"status": "deleted", "item_id": item_id}


@router.post("/items/{item_id}/complete", response_model=schemas.ScheduleItemRead)
def mark_schedule_item_complete(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ScheduleItem).filter(models.ScheduleItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    item.is_complete = True
    item.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="schedule",
        message=f"Schedule item completed: id={item.id} title={item.title}",
    )
    return item


@router.get("/overview", response_model=schemas.ScheduleOverviewResponse)
def get_schedule_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()

    items = (
        db.query(models.ScheduleItem)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .all()
    )

    current_candidates = [
        item for item in items if not item.is_complete and item.start_time <= now
    ]
    current = current_candidates[-1] if current_candidates else None
    next_item = next(
        (item for item in items if not item.is_complete and item.start_time > now),
        None,
    )

    delay_warning = None
    if current and now > current.end_time:
        delay_warning = f"{current.title} is running past planned end time"

    return schemas.ScheduleOverviewResponse(
        current_activity=current,
        next_activity=next_item,
        delay_warning=delay_warning,
    )
