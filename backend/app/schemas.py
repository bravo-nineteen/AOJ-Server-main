from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    name: str
    device_type: str
    ip_address: str
    status: Literal["online", "offline", "maintenance"] = "offline"


class DeviceCreate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    id: int
    last_seen: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionBase(BaseModel):
    title: str
    description: str = ""
    status: Literal["planned", "active", "complete"] = "planned"
    start_time: datetime | None = None
    end_time: datetime | None = None


class MissionCreate(MissionBase):
    pass


class MissionRead(MissionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameSessionBase(BaseModel):
    mission_id: int | None = None
    name: str
    is_active: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None


class GameSessionCreate(GameSessionBase):
    pass


class GameSessionRead(GameSessionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TeamBase(BaseModel):
    game_session_id: int
    name: str
    callsign: str


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ScoreEventBase(BaseModel):
    game_session_id: int
    team_id: int
    device_id: int | None = None
    points: int = 0
    event_type: str


class ScoreEventCreate(ScoreEventBase):
    pass


class ScoreEventRead(ScoreEventBase):
    id: int
    happened_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleItemBase(BaseModel):
    mission_id: int | None = None
    title: str
    details: str = ""
    activity_type: Literal[
        "Safety Brief", "Game", "Break", "Lunch", "Setup", "Pack Down", "Custom"
    ] = "Custom"
    start_time: datetime
    end_time: datetime


class ScheduleItemCreate(ScheduleItemBase):
    pass


class ScheduleItemRead(ScheduleItemBase):
    id: int
    is_complete: bool
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleItemUpdate(BaseModel):
    mission_id: int | None = None
    title: str
    details: str = ""
    activity_type: Literal[
        "Safety Brief", "Game", "Break", "Lunch", "Setup", "Pack Down", "Custom"
    ] = "Custom"
    start_time: datetime
    end_time: datetime
    is_complete: bool = False


class ScheduleOverviewResponse(BaseModel):
    current_activity: ScheduleItemRead | None = None
    next_activity: ScheduleItemRead | None = None
    delay_warning: str | None = None


class SystemLogBase(BaseModel):
    level: Literal["info", "warning", "error"] = "info"
    source: str
    message: str


class SystemLogCreate(SystemLogBase):
    pass


class SystemLogRead(SystemLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleBase(BaseModel):
    role_name: str
    permissions: str = "[]"
    is_active: bool = True


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleRead(UserRoleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    database: str


class SystemStatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    connected_clients: int
    active_game_sessions: int
    entity_counts: dict[str, int]


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
    title: str
    description: str = ""
    game_mode: str
    main_timer_seconds: int = 1800
    phase_timer_seconds: int = 300
    objectives: list[str] = []


class MissionControlScoreRequest(BaseModel):
    team: Literal["red", "blue"]
    delta: int
    reason: str = "manual"


class MissionControlObjectiveStatusRequest(BaseModel):
    status: Literal["pending", "active", "complete", "failed"]
