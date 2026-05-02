from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api", tags=["Resources"])


@router.get("/devices", response_model=list[schemas.DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).order_by(models.Device.id.desc()).all()


@router.post("/devices", response_model=schemas.DeviceRead)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
    try:
        item = models.Device(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A device with that IP address already exists.")
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="resources",
        message=f"Device created: {item.name} ({item.ip_address})",
    )
    return item


@router.get("/missions", response_model=list[schemas.MissionRead])
def list_missions(db: Session = Depends(get_db)):
    return db.query(models.Mission).order_by(models.Mission.id.desc()).all()


@router.post("/missions", response_model=schemas.MissionRead)
def create_mission(payload: schemas.MissionCreate, db: Session = Depends(get_db)):
    item = models.Mission(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="resources",
        message=f"Mission created: {item.title}",
    )
    return item


@router.get("/game-sessions", response_model=list[schemas.GameSessionRead])
def list_game_sessions(db: Session = Depends(get_db)):
    return db.query(models.GameSession).order_by(models.GameSession.id.desc()).all()


@router.post("/game-sessions", response_model=schemas.GameSessionRead)
def create_game_session(payload: schemas.GameSessionCreate, db: Session = Depends(get_db)):
    if payload.mission_id is not None:
        if not db.query(models.Mission).filter(models.Mission.id == payload.mission_id).first():
            raise HTTPException(status_code=422, detail=f"Mission {payload.mission_id} does not exist.")
    item = models.GameSession(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="resources",
        message=f"Game session created: {item.name}",
    )
    return item


@router.get("/teams", response_model=list[schemas.TeamRead])
def list_teams(db: Session = Depends(get_db)):
    return db.query(models.Team).order_by(models.Team.id.desc()).all()


@router.post("/teams", response_model=schemas.TeamRead)
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db)):
    if not db.query(models.GameSession).filter(models.GameSession.id == payload.game_session_id).first():
        raise HTTPException(status_code=422, detail=f"GameSession {payload.game_session_id} does not exist.")
    item = models.Team(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="resources",
        message=f"Team created: {item.name} ({item.callsign})",
    )
    return item


@router.get("/score-events", response_model=list[schemas.ScoreEventRead])
def list_score_events(db: Session = Depends(get_db)):
    return db.query(models.ScoreEvent).order_by(models.ScoreEvent.id.desc()).all()


@router.post("/score-events", response_model=schemas.ScoreEventRead)
def create_score_event(payload: schemas.ScoreEventCreate, db: Session = Depends(get_db)):
    if not db.query(models.GameSession).filter(models.GameSession.id == payload.game_session_id).first():
        raise HTTPException(status_code=422, detail=f"GameSession {payload.game_session_id} does not exist.")
    if not db.query(models.Team).filter(models.Team.id == payload.team_id).first():
        raise HTTPException(status_code=422, detail=f"Team {payload.team_id} does not exist.")
    item = models.ScoreEvent(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="resources",
        message=f"Score event created: team_id={item.team_id} points={item.points}",
    )
    return item


# GET /api/schedule-items intentionally omitted here.
# Use GET /api/schedule/items (schedule.py) for the canonical schedule endpoint.

@router.post("/schedule-items", response_model=schemas.ScheduleItemRead)
def create_schedule_item(payload: schemas.ScheduleItemCreate, db: Session = Depends(get_db)):
    item = models.ScheduleItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.update,
        source="resources",
        message=f"Schedule item created: {item.title}",
    )
    return item


@router.get("/system-logs", response_model=list[schemas.SystemLogRead])
def list_system_logs(db: Session = Depends(get_db)):
    return db.query(models.SystemLog).order_by(models.SystemLog.id.desc()).all()


@router.post("/system-logs", response_model=schemas.SystemLogRead)
def create_system_log(payload: schemas.SystemLogCreate, db: Session = Depends(get_db)):
    item = models.SystemLog(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/user-roles", response_model=list[schemas.UserRoleRead])
def list_user_roles(db: Session = Depends(get_db)):
    return db.query(models.UserRole).order_by(models.UserRole.id.desc()).all()


@router.post("/user-roles", response_model=schemas.UserRoleRead)
def create_user_role(payload: schemas.UserRoleCreate, db: Session = Depends(get_db)):
    item = models.UserRole(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="resources",
        message=f"User role created: {item.role_name}",
    )
    return item
