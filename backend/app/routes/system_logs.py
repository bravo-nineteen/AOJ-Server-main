"""Routes for system logs and audit trails."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/system-logs", tags=["System Logs"])


@router.get("", response_model=list[schemas.SystemLogRead])
def list_system_logs(
    level: str | None = None,
    category: str | None = None,
    source: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[schemas.SystemLogRead]:
    """List system logs with optional filtering."""
    query = db.query(models.SystemLog)

    if level:
        query = query.filter(models.SystemLog.level == level)
    if category:
        query = query.filter(models.SystemLog.category == category)
    if source:
        query = query.filter(models.SystemLog.source == source)

    logs = (
        query.order_by(models.SystemLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return logs


@router.get("/by-category", response_model=dict)
def get_logs_by_category(
    db: Session = Depends(get_db),
) -> dict:
    """Get count of logs by category."""
    logs = db.query(models.SystemLog).all()
    counts = {}
    for log in logs:
        if log.category not in counts:
            counts[log.category] = 0
        counts[log.category] += 1
    return counts


@router.get("/by-source", response_model=dict)
def get_logs_by_source(
    db: Session = Depends(get_db),
) -> dict:
    """Get count of logs by source."""
    logs = db.query(models.SystemLog).all()
    counts = {}
    for log in logs:
        if log.source not in counts:
            counts[log.source] = 0
        counts[log.source] += 1
    return counts
