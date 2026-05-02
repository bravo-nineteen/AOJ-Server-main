from typing import Literal

from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    connected_clients: int
    active_game_sessions: int
    entity_counts: dict[str, int]
    backend_version: str
    platform_mode: Literal["raspberry_pi", "mock"]
    cpu_temperature_c: float
    cpu_usage_percent: float
    ram_usage_percent: float
    disk_usage_percent: float
    lora_service_status: str
    database_status: str
