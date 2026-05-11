"""Routes for mission management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/missions", tags=["Missions"])


@router.post("", response_model=schemas.MissionRead)
def create_mission(
    payload: schemas.MissionCreate,
    db: Session = Depends(get_db),
) -> schemas.MissionRead:
    """Create a new mission."""
    mission = models.Mission(**payload.model_dump())
    db.add(mission)
    db.commit()
    db.refresh(mission)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="missions",
        message=f"Mission created: {payload.name}",
    )

    return mission


@router.get("", response_model=list[schemas.MissionRead])
def list_missions(
    db: Session = Depends(get_db),
) -> list[schemas.MissionRead]:
    """List all missions."""
    missions = db.query(models.Mission).all()
    return missions


@router.get("/{mission_id}", response_model=schemas.MissionRead)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> schemas.MissionRead:
    """Get mission by ID."""
    mission = db.query(models.Mission).get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.put("/{mission_id}", response_model=schemas.MissionRead)
def update_mission(
    mission_id: int,
    payload: schemas.MissionUpdate,
    db: Session = Depends(get_db),
) -> schemas.MissionRead:
    """Update a mission."""
    mission = db.query(models.Mission).get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(mission, key, value)

    db.commit()
    db.refresh(mission)
    return mission


@router.delete("/{mission_id}", status_code=204)
def delete_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a mission."""
    mission = db.query(models.Mission).get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    db.delete(mission)
    db.commit()


@router.get("/{mission_id}/results", response_model=list[schemas.GameResultRead])
def get_mission_results(
    mission_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.GameResultRead]:
    """Get all game results for a mission."""
    results = (
        db.query(models.GameResult)
        .filter(models.GameResult.mission_id == mission_id)
        .order_by(models.GameResult.created_at.desc())
        .all()
    )
    return results
