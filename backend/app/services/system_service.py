from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.schemas import SystemStatusResponse
from app.websocket_manager import websocket_manager

STARTED_AT = datetime.now(tz=timezone.utc)


def get_system_status(db: Session) -> SystemStatusResponse:
    now = datetime.now(tz=timezone.utc)

    entity_counts = {
        "devices": db.query(func.count(models.Device.id)).scalar() or 0,
        "missions": db.query(func.count(models.Mission.id)).scalar() or 0,
        "game_sessions": db.query(func.count(models.GameSession.id)).scalar() or 0,
        "teams": db.query(func.count(models.Team.id)).scalar() or 0,
        "score_events": db.query(func.count(models.ScoreEvent.id)).scalar() or 0,
        "schedule_items": db.query(func.count(models.ScheduleItem.id)).scalar() or 0,
        "system_logs": db.query(func.count(models.SystemLog.id)).scalar() or 0,
        "user_roles": db.query(func.count(models.UserRole.id)).scalar() or 0,
    }

    active_game_sessions = (
        db.query(func.count(models.GameSession.id))
        .filter(models.GameSession.is_active.is_(True))
        .scalar()
        or 0
    )

    return SystemStatusResponse(
        status="online",
        uptime_seconds=(now - STARTED_AT).total_seconds(),
        connected_clients=websocket_manager.connected_count,
        active_game_sessions=active_game_sessions,
        entity_counts=entity_counts,
    )
