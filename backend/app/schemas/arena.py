"""Schemas for arena and field management."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArenaBase(BaseModel):
    name: str = Field(..., max_length=200, unique=True)
    location: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=2000)
    max_players: int = Field(default=0, ge=0)
    field_map_url: str = Field(default="", max_length=500)
    active: bool = True


class ArenaCreate(ArenaBase):
    pass


class ArenaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    max_players: int | None = None
    field_map_url: str | None = None
    active: bool | None = None


class ArenaRead(ArenaBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArenaLocationBase(BaseModel):
    arena_id: int
    name: str = Field(..., max_length=100)
    location_type: str = Field(..., max_length=50)
    x_coord: float = 0.0
    y_coord: float = 0.0
    description: str = Field(default="", max_length=500)


class ArenaLocationCreate(ArenaLocationBase):
    pass


class ArenaLocationRead(ArenaLocationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RespawnPointBase(BaseModel):
    arena_id: int
    team_id: int
    name: str = Field(..., max_length=100)
    x_coord: float = 0.0
    y_coord: float = 0.0
    respawn_delay_seconds: int = 0
    max_simultaneous_respawns: int = 0
    description: str = Field(default="", max_length=500)
    active: bool = True


class RespawnPointCreate(RespawnPointBase):
    pass


class RespawnPointRead(RespawnPointBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoFireZoneBase(BaseModel):
    arena_id: int
    name: str = Field(..., max_length=100)
    x_center: float = 0.0
    y_center: float = 0.0
    radius_meters: float = 10.0
    description: str = Field(default="", max_length=500)
    active: bool = True


class NoFireZoneCreate(NoFireZoneBase):
    pass


class NoFireZoneRead(NoFireZoneBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObjectiveMarkerBase(BaseModel):
    arena_id: int
    name: str = Field(..., max_length=100)
    objective_type: str = Field(..., max_length=50)
    x_coord: float = 0.0
    y_coord: float = 0.0
    status: str = Field(default="neutral", max_length=50)


class ObjectiveMarkerCreate(ObjectiveMarkerBase):
    pass


class ObjectiveMarkerUpdate(BaseModel):
    status: str | None = None


class ObjectiveMarkerRead(ObjectiveMarkerBase):
    id: int
    game_session_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
