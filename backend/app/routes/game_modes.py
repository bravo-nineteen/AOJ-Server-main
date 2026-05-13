"""Routes for game mode management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/game-modes", tags=["Game Modes"])


@router.post("", response_model=schemas.GameModeRead)
def create_game_mode(
    payload: schemas.GameModeCreate,
    db: Session = Depends(get_db),
) -> schemas.GameModeRead:
    """Create a new game mode."""
    game_mode = models.GameMode(**payload.model_dump())
    db.add(game_mode)
    db.commit()
    db.refresh(game_mode)
    return game_mode


@router.get("", response_model=list[schemas.GameModeRead])
def list_game_modes(
    db: Session = Depends(get_db),
) -> list[schemas.GameModeRead]:
    """List all game modes."""
    modes = db.query(models.GameMode).all()
    return modes


@router.get("/{mode_id}", response_model=schemas.GameModeRead)
def get_game_mode(
    mode_id: int,
    db: Session = Depends(get_db),
) -> schemas.GameModeRead:
    """Get game mode by ID."""
    mode = db.query(models.GameMode).get(mode_id)
    if not mode:
        raise HTTPException(status_code=404, detail="Game mode not found")
    return mode


@router.put("/{mode_id}", response_model=schemas.GameModeRead)
def update_game_mode(
    mode_id: int,
    payload: schemas.GameModeUpdate,
    db: Session = Depends(get_db),
) -> schemas.GameModeRead:
    """Update a game mode."""
    mode = db.query(models.GameMode).get(mode_id)
    if not mode:
        raise HTTPException(status_code=404, detail="Game mode not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(mode, key, value)

    db.commit()
    db.refresh(mode)
    return mode


@router.delete("/{mode_id}", status_code=204)
def delete_game_mode(
    mode_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a game mode."""
    mode = db.query(models.GameMode).get(mode_id)
    if not mode:
        raise HTTPException(status_code=404, detail="Game mode not found")

    db.delete(mode)
    db.commit()
