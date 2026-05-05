from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.lora.service import lora_service
from app.schemas import SystemStatusResponse
from app.services.system_service import get_system_status

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    return get_system_status(db)


@router.get("/lora/inbound-frames")
def system_lora_inbound_frames(
    device_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
) -> dict[str, object]:
    frames = lora_service.recent_inbound_frames(device_id=device_id, limit=limit)
    return {
        "status": "ok",
        "device_id": device_id,
        "limit": limit,
        "frames": frames,
    }


@router.get("/lora/device-summary")
def system_lora_device_summary() -> dict[str, object]:
    """Last-seen frame per device — lightweight dashboard data."""
    return {
        "status": "ok",
        "devices": lora_service.device_summary(),
    }
