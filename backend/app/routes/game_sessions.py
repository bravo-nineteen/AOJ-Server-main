"""Game session management and prop assignment routes."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.core.websocket import websocket_manager
from app.database import get_db
from app.services.log_service import log_action
from app.services.game_mode_init_service import get_game_mode_by_name

router = APIRouter(prefix="/api/game-sessions", tags=["Game Sessions"])


@router.get("", response_model=list[schemas.GameSessionRead])
def list_game_sessions(db: Session = Depends(get_db)):
    """List all game sessions."""
    return db.query(models.GameSession).order_by(models.GameSession.id.desc()).all()


@router.post("", response_model=schemas.GameSessionRead)
def create_game_session(payload: schemas.GameSessionCreate, db: Session = Depends(get_db)):
    """Create a new game session."""
    # Get game mode if specified
    game_mode = None
    if payload.game_mode_id:
        game_mode = db.query(models.GameMode).filter(models.GameMode.id == payload.game_mode_id).first()
        if not game_mode:
            raise HTTPException(status_code=404, detail="Game mode not found")

    session_data = payload.model_dump(exclude_none=True)
    session = models.GameSession(**session_data)
    db.add(session)
    db.commit()
    db.refresh(session)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.game,
        source="game_session",
        message=f"Game session created: {session.name}",
    )

    return session


@router.get("/{session_id}", response_model=schemas.GameSessionRead)
def get_game_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    return session


@router.put("/{session_id}", response_model=schemas.GameSessionRead)
def update_game_session(
    session_id: int,
    payload: schemas.GameSessionUpdate,
    db: Session = Depends(get_db),
):
    """Update a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(session, key, value)

    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.game,
        source="game_session",
        message=f"Game session updated: {session.name}",
    )

    return session


@router.delete("/{session_id}", status_code=204)
def delete_game_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    session_name = session.name
    db.delete(session)
    db.commit()

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.game,
        source="game_session",
        message=f"Game session deleted: {session_name}",
    )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Prop Assignment Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{session_id}/props/{prop_id}")
async def assign_prop_to_session(
    session_id: int,
    prop_id: int,
    db: Session = Depends(get_db),
):
    """Assign a prop to a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    prop = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Prop not found")

    if prop not in session.props:
        session.props.append(prop)
        db.commit()

        log_action(
            db,
            level=models.LogLevel.info,
            category=models.LogCategory.game,
            source="game_session_props",
            message=f"Prop assigned to session: {prop.device_id} → {session.name}",
        )

        await websocket_manager.broadcast({
            "event": "game_session.prop_assigned",
            "payload": {
                "session_id": session.id,
                "prop_id": prop.id,
                "device_id": prop.device_id,
                "prop_name": prop.name,
                "session_name": session.name,
            },
        })

    return {
        "status": "assigned",
        "session_id": session.id,
        "prop_id": prop.id,
        "device_id": prop.device_id,
    }


@router.delete("/{session_id}/props/{prop_id}", status_code=204)
async def unassign_prop_from_session(
    session_id: int,
    prop_id: int,
    db: Session = Depends(get_db),
):
    """Unassign a prop from a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    prop = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Prop not found")

    if prop in session.props:
        session.props.remove(prop)
        db.commit()

        log_action(
            db,
            level=models.LogLevel.info,
            category=models.LogCategory.game,
            source="game_session_props",
            message=f"Prop unassigned from session: {prop.device_id} → {session.name}",
        )

        await websocket_manager.broadcast({
            "event": "game_session.prop_unassigned",
            "payload": {
                "session_id": session.id,
                "prop_id": prop.id,
                "device_id": prop.device_id,
            },
        })

    return None


@router.get("/{session_id}/props")
def get_session_props(session_id: int, db: Session = Depends(get_db)) -> dict:
    """Get all props assigned to a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    props = [
        {
            "id": prop.id,
            "device_id": prop.device_id,
            "name": prop.name,
            "prop_type": str(prop.prop_type),
            "status": prop.status,
            "battery_level": prop.battery_level,
            "signal_strength": prop.signal_strength,
            "location": prop.location,
            "firmware_version": prop.firmware_version,
        }
        for prop in session.props
    ]

    return {
        "session_id": session.id,
        "session_name": session.name,
        "prop_count": len(props),
        "props": props,
    }


@router.post("/{session_id}/props/bulk-assign")
async def bulk_assign_props(
    session_id: int,
    payload: dict,  # {"prop_ids": [1, 2, 3]}
    db: Session = Depends(get_db),
):
    """Assign multiple props to a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    prop_ids = payload.get("prop_ids", [])
    assigned = []
    failed = []

    for prop_id in prop_ids:
        prop = db.query(models.Prop).filter(models.Prop.id == prop_id).first()
        if not prop:
            failed.append(prop_id)
        else:
            if prop not in session.props:
                session.props.append(prop)
                assigned.append(prop_id)

    db.commit()

    if assigned:
        log_action(
            db,
            level=models.LogLevel.info,
            category=models.LogCategory.game,
            source="game_session_props",
            message=f"Bulk assigned {len(assigned)} props to session: {session.name}",
        )

    await websocket_manager.broadcast({
        "event": "game_session.props_bulk_assigned",
        "payload": {
            "session_id": session.id,
            "assigned_count": len(assigned),
            "failed_count": len(failed),
        },
    })

    return {
        "status": "bulk_assigned",
        "session_id": session.id,
        "assigned": assigned,
        "failed": failed,
    }


@router.post("/{session_id}/props/by-type")
async def assign_props_by_type(
    session_id: int,
    payload: dict,  # {"prop_types": ["Bomb", "Bomb Vest"]}
    db: Session = Depends(get_db),
):
    """Assign all props of specific types to a game session."""
    session = db.query(models.GameSession).filter(models.GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    prop_types = payload.get("prop_types", [])
    assigned = 0

    for prop_type in prop_types:
        props = db.query(models.Prop).filter(models.Prop.prop_type == prop_type).all()
        for prop in props:
            if prop not in session.props:
                session.props.append(prop)
                assigned += 1

    db.commit()

    if assigned > 0:
        log_action(
            db,
            level=models.LogLevel.info,
            category=models.LogCategory.game,
            source="game_session_props",
            message=f"Assigned {assigned} props by type to session: {session.name}",
        )

    await websocket_manager.broadcast({
        "event": "game_session.props_assigned_by_type",
        "payload": {
            "session_id": session.id,
            "prop_types": prop_types,
            "assigned_count": assigned,
        },
    })

    return {
        "status": "assigned_by_type",
        "session_id": session.id,
        "prop_types": prop_types,
        "assigned_count": assigned,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Game Mode Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/game-modes/list")
def list_game_modes(db: Session = Depends(get_db)):
    """List all available game modes."""
    modes = db.query(models.GameMode).order_by(models.GameMode.name).all()
    return {
        "count": len(modes),
        "modes": [
            {
                "id": mode.id,
                "name": mode.name,
                "description": mode.description,
                "default_main_timer_seconds": mode.default_main_timer_seconds,
                "default_phase_timer_seconds": mode.default_phase_timer_seconds,
            }
            for mode in modes
        ],
    }
