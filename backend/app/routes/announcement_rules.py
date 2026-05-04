"""CRUD routes for configurable timed announcement rules."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.announcement_rule import AnnouncementRule
from app.schemas.announcement_rule import (
    AnnouncementRuleCreate,
    AnnouncementRuleRead,
    AnnouncementRuleUpdate,
)

router = APIRouter(prefix="/api/announcement-rules", tags=["announcement-rules"])


@router.get("", response_model=list[AnnouncementRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.query(AnnouncementRule).order_by(AnnouncementRule.id).all()


@router.post("", response_model=AnnouncementRuleRead, status_code=201)
def create_rule(payload: AnnouncementRuleCreate, db: Session = Depends(get_db)):
    rule = AnnouncementRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=AnnouncementRuleRead)
def update_rule(rule_id: int, payload: AnnouncementRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(AnnouncementRule).filter(AnnouncementRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Announcement rule not found")
    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AnnouncementRule).filter(AnnouncementRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Announcement rule not found")
    db.delete(rule)
    db.commit()
