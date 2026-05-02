from typing import Literal

from pydantic import BaseModel, Field


class MissionControlObjective(BaseModel):
    id: int
    label: str
    status: Literal["pending", "active", "complete", "failed"]


class MissionControlStateResponse(BaseModel):
    mission_id: int | None = None
    mission_title: str
    game_mode: str
    state: Literal["idle", "ready", "running", "paused", "ended"]
    main_timer_seconds: int
    phase_timer_seconds: int
    red_team_score: int
    blue_team_score: int
    objectives: list[MissionControlObjective]
    event_feed: list[str]
    updated_at: str


class MissionControlCreateMissionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=140)
    description: str = ""
    game_mode: str = Field(..., min_length=1, max_length=80)
    main_timer_seconds: int = Field(default=1800, ge=1)
    phase_timer_seconds: int = Field(default=300, ge=0)
    objectives: list[str] = []


class MissionControlScoreRequest(BaseModel):
    team: Literal["red", "blue"]
    delta: int = Field(..., ge=-1000, le=1000)
    reason: str = Field(default="manual", max_length=200)


class MissionControlObjectiveStatusRequest(BaseModel):
    status: Literal["pending", "active", "complete", "failed"]
