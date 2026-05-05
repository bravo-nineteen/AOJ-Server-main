from pydantic import BaseModel
from typing import Any


class HealthResponse(BaseModel):
    status: str
    database: str
    lora: dict[str, Any] | None = None
