"""Routes for player management and team assignments."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/players", tags=["Player Management"])


# Squad Management


@router.post("/squads", response_model=schemas.SquadRead)
def create_squad(
    payload: schemas.SquadCreate,
    db: Session = Depends(get_db),
) -> schemas.SquadRead:
    """Create a new squad for a game session."""
    squad = models.Squad(**payload.model_dump())
    db.add(squad)
    db.commit()
    db.refresh(squad)
    return squad


@router.get("/squads/{session_id}", response_model=list[schemas.SquadRead])
def list_squads_for_session(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.SquadRead]:
    """List all squads for a game session."""
    squads = (
        db.query(models.Squad)
        .filter(models.Squad.game_session_id == session_id)
        .all()
    )
    return squads


@router.post("/squads/{squad_id}/members", response_model=schemas.SquadMemberRead)
def add_squad_member(
    squad_id: int,
    payload: schemas.SquadMemberCreate,
    db: Session = Depends(get_db),
) -> schemas.SquadMemberRead:
    """Add player to squad."""
    squad = db.query(models.Squad).filter(models.Squad.id == squad_id).first()
    if not squad:
        raise HTTPException(status_code=404, detail="Squad not found")

    member = models.SquadMember(squad_id=squad_id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


# Team Assignments


@router.post("/team-assignments", response_model=schemas.PlayerTeamAssignmentRead)
def assign_player_to_team(
    payload: schemas.PlayerTeamAssignmentCreate,
    db: Session = Depends(get_db),
) -> schemas.PlayerTeamAssignmentRead:
    """Assign a player to a team for a game session."""
    assignment = models.PlayerTeamAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/team-assignments/{session_id}", response_model=list[schemas.PlayerTeamAssignmentRead])
def list_player_assignments(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[schemas.PlayerTeamAssignmentRead]:
    """List player-team assignments for a session."""
    assignments = (
        db.query(models.PlayerTeamAssignment)
        .filter(models.PlayerTeamAssignment.game_session_id == session_id)
        .all()
    )
    return assignments
