from datetime import datetime

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/schedule", tags=["Schedule"])


def _normalize_schedule_item(item: models.ScheduleItem) -> models.ScheduleItem:
    if item.scheduled_for and not item.start_time:
        item.start_time = item.scheduled_for
    if item.scheduled_for and not item.end_time:
        item.end_time = item.scheduled_for
    return item


@router.get("/items", response_model=list[schemas.ScheduleItemRead])
def list_schedule_items(db: Session = Depends(get_db)):
    items = (
        db.query(models.ScheduleItem)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .all()
    )
    return [_normalize_schedule_item(item) for item in items]


@router.post("/items", response_model=schemas.ScheduleItemRead)
def add_schedule_item(payload: schemas.ScheduleItemCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    item = models.ScheduleItem(**payload.model_dump(), scheduled_for=payload.start_time)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _normalize_schedule_item(item)


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
    item.scheduled_for = payload.start_time
    item.completed_at = datetime.utcnow() if payload.is_complete else None
    db.commit()
    db.refresh(item)
    return _normalize_schedule_item(item)


@router.delete("/items/{item_id}")
def delete_schedule_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ScheduleItem).filter(models.ScheduleItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    db.delete(item)
    db.commit()
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
    return _normalize_schedule_item(item)


@router.get("/overview", response_model=schemas.ScheduleOverviewResponse)
def get_schedule_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()

    items = (
        db.query(models.ScheduleItem)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .all()
    )
    items = [_normalize_schedule_item(item) for item in items]

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
