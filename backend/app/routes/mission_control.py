from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import (
    MissionControlCreateMissionRequest,
    MissionControlObjectiveStatusRequest,
    MissionControlScoreRequest,
    MissionControlStateResponse,
    TeamReadyRequest,
)
from app.services.mission_control_service import mission_control_service

router = APIRouter(prefix="/api/mission-control", tags=["Mission Control"])


@router.get("/state", response_model=MissionControlStateResponse)
async def get_mission_state() -> MissionControlStateResponse:
    return MissionControlStateResponse(**mission_control_service.get_state())


@router.post("/mission", response_model=MissionControlStateResponse)
async def create_mission(
    payload: MissionControlCreateMissionRequest, db: Session = Depends(get_db)
) -> MissionControlStateResponse:
    state = await mission_control_service.create_mission(db, payload)
    return MissionControlStateResponse(**state)


@router.post("/start", response_model=MissionControlStateResponse)
async def start_game(db: Session = Depends(get_db)) -> MissionControlStateResponse:
    state = await mission_control_service.start_game(db)
    return MissionControlStateResponse(**state)


@router.post("/pause", response_model=MissionControlStateResponse)
async def pause_game(db: Session = Depends(get_db)) -> MissionControlStateResponse:
    state = await mission_control_service.pause_game(db)
    return MissionControlStateResponse(**state)


@router.post("/resume", response_model=MissionControlStateResponse)
async def resume_game(db: Session = Depends(get_db)) -> MissionControlStateResponse:
    state = await mission_control_service.resume_game(db)
    return MissionControlStateResponse(**state)


@router.post("/end", response_model=MissionControlStateResponse)
async def end_game(db: Session = Depends(get_db)) -> MissionControlStateResponse:
    state = await mission_control_service.end_game(db)
    return MissionControlStateResponse(**state)


@router.post("/score", response_model=MissionControlStateResponse)
async def adjust_score(
    payload: MissionControlScoreRequest,
    db: Session = Depends(get_db),
) -> MissionControlStateResponse:
    state = await mission_control_service.adjust_score(payload, db)
    return MissionControlStateResponse(**state)


@router.post("/objectives/{objective_id}", response_model=MissionControlStateResponse)
async def set_objective_status(
    objective_id: int,
    payload: MissionControlObjectiveStatusRequest,
    db: Session = Depends(get_db),
) -> MissionControlStateResponse:
    state = await mission_control_service.set_objective_status(objective_id, payload, db)
    return MissionControlStateResponse(**state)


@router.get("/ready")
async def get_ready_state():
    return mission_control_service.get_ready_state()


@router.post("/ready")
async def set_team_ready(
    payload: TeamReadyRequest,
    db: Session = Depends(get_db),
):
    return await mission_control_service.set_team_ready(payload.team, db)


@router.delete("/ready")
async def reset_ready():
    return await mission_control_service.reset_ready()
