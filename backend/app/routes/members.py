"""Member profiles API — /api/members

Allows Christy (and operators) to store and retrieve player profiles including
name, gender, team, skill level, strengths, weaknesses, and Christy's own memory
notes about each member.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.member_profile import MemberProfile
from app.schemas.member_profile import (
    MemberProfileCreate,
    MemberProfileOut,
    MemberProfileUpdate,
)

router = APIRouter(prefix="/api/members", tags=["Members"])


@router.get("", response_model=list[MemberProfileOut])
def list_members(db: Session = Depends(get_db)) -> list[MemberProfile]:
    return db.query(MemberProfile).order_by(MemberProfile.name).all()


@router.post("", response_model=MemberProfileOut, status_code=201)
def create_member(
    payload: MemberProfileCreate, db: Session = Depends(get_db)
) -> MemberProfile:
    existing = db.query(MemberProfile).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Member '{payload.name}' already exists.")
    member = MemberProfile(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=MemberProfileOut)
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberProfile:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return member


@router.patch("/{member_id}", response_model=MemberProfileOut)
def update_member(
    member_id: int, payload: MemberProfileUpdate, db: Session = Depends(get_db)
) -> MemberProfile:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)) -> None:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    db.delete(member)
    db.commit()
