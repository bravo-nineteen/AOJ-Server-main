"""Routes for score tracking and leaderboards."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/scores", tags=["Scoring & Leaderboards"])


@router.post("", response_model=schemas.ScoreEventRead)
def record_score_event(
    payload: schemas.ScoreEventCreate,
    db: Session = Depends(get_db),
) -> schemas.ScoreEventRead:
    """Record a score event (points awarded)."""
    score_event = models.ScoreEvent(**payload.model_dump())
    db.add(score_event)
    db.commit()
    db.refresh(score_event)

    log_action(
        db,
        level=models.LogLevel.debug,
        category=models.LogCategory.mission,
        source="score_events",
        message=f"Score: {payload.points} pts for {payload.event_type}",
    )

    return score_event


@router.get("/session/{session_id}/leaderboard", response_model=list[dict])
def get_session_leaderboard(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get player leaderboard for a session."""
    rows = (
        db.query(
            models.ScoreEvent.player_id.label("player_id"),
            func.sum(models.ScoreEvent.points).label("total_score"),
            models.Player.callsign.label("callsign"),
        )
        .outerjoin(models.Player, models.Player.id == models.ScoreEvent.player_id)
        .filter(models.ScoreEvent.game_session_id == session_id)
        .group_by(models.ScoreEvent.player_id, models.Player.callsign)
        .order_by(func.sum(models.ScoreEvent.points).desc())
        .all()
    )

    leaderboard: list[dict] = []
    for row in rows:
        if row.player_id is None:
            continue
        leaderboard.append(
            {
                "player_id": row.player_id,
                "username": row.callsign or f"player-{row.player_id}",
                "total_score": int(row.total_score or 0),
            }
        )

    return leaderboard


@router.get("/team/{team_id}/session/{session_id}", response_model=list[schemas.ScoreEventRead])
def list_team_scores(
    team_id: int,
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.ScoreEventRead]:
    """Get all score events for a team in a session."""
    scores = (
        db.query(models.ScoreEvent)
        .filter(
            models.ScoreEvent.game_session_id == session_id,
            models.ScoreEvent.team_id == team_id,
        )
        .order_by(models.ScoreEvent.happened_at.desc())
        .all()
    )
    return scores


@router.get("/player/{player_id}/session/{session_id}", response_model=list[schemas.ScoreEventRead])
def list_player_scores(
    player_id: int,
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.ScoreEventRead]:
    """Get all scores for a player in a session."""
    scores = (
        db.query(models.ScoreEvent)
        .filter(
            models.ScoreEvent.game_session_id == session_id,
            models.ScoreEvent.player_id == player_id,
        )
        .order_by(models.ScoreEvent.happened_at.desc())
        .all()
    )
    return scores


@router.get("/session/{session_id}/by-reason", response_model=dict)
def get_score_breakdown(
    session_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get scoring breakdown by reason for a session."""
    breakdown = {}
    scores = (
        db.query(models.ScoreEvent)
        .filter(models.ScoreEvent.game_session_id == session_id)
        .all()
    )

    for score in scores:
        if score.reason not in breakdown:
            breakdown[score.reason] = 0
        breakdown[score.reason] += score.points

    return breakdown
