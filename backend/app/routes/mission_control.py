from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import (
    MissionControlCreateMissionRequest,
    MissionControlObjectiveStatusRequest,
    MissionControlScoreRequest,
    MissionControlStateResponse,
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
async def pause_game() -> MissionControlStateResponse:
    state = await mission_control_service.pause_game()
    return MissionControlStateResponse(**state)


@router.post("/resume", response_model=MissionControlStateResponse)
async def resume_game() -> MissionControlStateResponse:
    state = await mission_control_service.resume_game()
    return MissionControlStateResponse(**state)


@router.post("/end", response_model=MissionControlStateResponse)
async def end_game(db: Session = Depends(get_db)) -> MissionControlStateResponse:
    state = await mission_control_service.end_game(db)
    return MissionControlStateResponse(**state)


@router.post("/score", response_model=MissionControlStateResponse)
async def adjust_score(
    payload: MissionControlScoreRequest,
) -> MissionControlStateResponse:
    state = await mission_control_service.adjust_score(payload)
    return MissionControlStateResponse(**state)


@router.post("/objectives/{objective_id}", response_model=MissionControlStateResponse)
async def set_objective_status(
    objective_id: int,
    payload: MissionControlObjectiveStatusRequest,
) -> MissionControlStateResponse:
    state = await mission_control_service.set_objective_status(objective_id, payload)
    return MissionControlStateResponse(**state)
