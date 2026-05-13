"""Routes for announcements and notifications."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/announcements", tags=["Announcements & Notifications"])


@router.post("/create-christy", response_model=schemas.ChristyAnnouncementRead)
def create_christy_announcement(
    payload: schemas.ChristyAnnouncementCreate,
    db: Session = Depends(get_db),
) -> schemas.ChristyAnnouncementRead:
    """Create a Christy (AI character) announcement."""
    announcement = models.ChristyAnnouncement(**payload.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="announcements",
        message=f"Christy announcement created: {payload.content[:50]}...",
    )

    return announcement


@router.post("/rule", response_model=schemas.AnnouncementRuleRead)
def create_announcement_rule(
    payload: schemas.AnnouncementRuleCreate,
    db: Session = Depends(get_db),
) -> schemas.AnnouncementRuleRead:
    """Create an announcement rule (trigger-based)."""
    rule = models.AnnouncementRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/christy", response_model=list[schemas.ChristyAnnouncementRead])
def list_christy_announcements(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[schemas.ChristyAnnouncementRead]:
    """List Christy announcements."""
    announcements = (
        db.query(models.ChristyAnnouncement)
        .order_by(models.ChristyAnnouncement.created_at.desc())
        .limit(limit)
        .all()
    )

    return announcements


@router.get("/rules", response_model=list[schemas.AnnouncementRuleRead])
def list_announcement_rules(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[schemas.AnnouncementRuleRead]:
    """List announcement rules."""
    query = db.query(models.AnnouncementRule)

    if status:
        is_active = status.lower() == "active"
        query = query.filter(models.AnnouncementRule.enabled == is_active)

    rules = query.order_by(models.AnnouncementRule.created_at.desc()).all()
    return rules


@router.put("/rules/{rule_id}", response_model=schemas.AnnouncementRuleRead)
def update_announcement_rule(
    rule_id: int,
    payload: schemas.AnnouncementRuleUpdate,
    db: Session = Depends(get_db),
) -> schemas.AnnouncementRuleRead:
    """Update an announcement rule."""
    rule = db.query(models.AnnouncementRule).get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_announcement_rule(
    rule_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete an announcement rule."""
    rule = db.query(models.AnnouncementRule).get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
