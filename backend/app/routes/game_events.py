"""Routes for game event timeline and objective tracking."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/game-events", tags=["Game Events & Objectives"])


@router.post("", response_model=schemas.GameEventRead)
def record_game_event(
    payload: schemas.GameEventCreate,
    db: Session = Depends(get_db),
) -> schemas.GameEventRead:
    """Record an event during active gameplay (objective capture, deployment, etc)."""
    event = models.GameEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)

    # Log significant events
    if payload.event_type in {"objective_captured", "objective_completed"}:
        log_action(
            db,
            level=models.LogLevel.info,
            category=models.LogCategory.mission,
            source="game_events",
            message=f"Event: {payload.event_type} - {payload.description}",
        )

    return event


@router.get("/session/{session_id}", response_model=list[schemas.GameEventRead])
def list_session_events(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.GameEventRead]:
    """Get all events for a game session (game timeline)."""
    events = (
        db.query(models.GameEvent)
        .filter(models.GameEvent.game_session_id == session_id)
        .order_by(models.GameEvent.happened_at.asc())
        .all()
    )
    return events


@router.get("/session/{session_id}/objectives", response_model=list[schemas.GameEventRead])
def list_objective_events(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.GameEventRead]:
    """Get objective events for a session."""
    events = (
        db.query(models.GameEvent)
        .filter(
            models.GameEvent.game_session_id == session_id,
            models.GameEvent.event_type.in_(
                [
                    "objective_captured",
                    "objective_lost",
                    "objective_completed",
                ]
            ),
        )
        .order_by(models.GameEvent.happened_at.asc())
        .all()
    )
    return events


@router.get("/team/{team_id}/events", response_model=list[schemas.GameEventRead])
def list_team_events(
    team_id: int,
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.GameEventRead]:
    """Get all events for a team in a session."""
    events = (
        db.query(models.GameEvent)
        .filter(
            models.GameEvent.game_session_id == session_id,
            models.GameEvent.team_id == team_id,
        )
        .order_by(models.GameEvent.happened_at.asc())
        .all()
    )
    return events


@router.get("/player/{player_id}/events", response_model=list[schemas.GameEventRead])
def list_player_events(
    player_id: int,
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.GameEventRead]:
    """Get all events involving a player in a session."""
    events = (
        db.query(models.GameEvent)
        .filter(
            models.GameEvent.game_session_id == session_id,
            models.GameEvent.player_id == player_id,
        )
        .order_by(models.GameEvent.happened_at.asc())
        .all()
    )
    return events
