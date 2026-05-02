from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api", tags=["Resources"])


@router.get("/devices", response_model=list[schemas.DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).order_by(models.Device.id.desc()).all()


@router.post("/devices", response_model=schemas.DeviceRead)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
    item = models.Device(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
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


@router.get("/schedule-items", response_model=list[schemas.ScheduleItemRead])
def list_schedule_items(db: Session = Depends(get_db)):
    return db.query(models.ScheduleItem).order_by(models.ScheduleItem.id.desc()).all()


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
