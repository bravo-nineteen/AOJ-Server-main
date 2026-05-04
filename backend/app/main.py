import asyncio
import logging
import os
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGIN_REGEX
from app.core.ai_safety import AISafetyMiddleware
from app.core.websocket import websocket_manager
from app.database import SessionLocal, init_db
from app.lora.service import lora_service
from app.routes import (
    ai,
    custom_admin,
    health,
    logs,
    members,
    mission_control,
    prop_network,
    resources,
    results,
    schedule,
    system,
    tts,
    update_center,
)
from app.services.christy_service import christy_service
from app.services.mission_control_service import mission_control_service
from app.services.update_center_service import handle_firmware_ack_event

logger = logging.getLogger(__name__)

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AISafetyMiddleware)

app.include_router(health.router)
app.include_router(system.router)
app.include_router(resources.router)
app.include_router(ai.router)
app.include_router(logs.router)
app.include_router(prop_network.router)
app.include_router(schedule.router)
app.include_router(results.router)
app.include_router(mission_control.router)
app.include_router(update_center.router)
app.include_router(custom_admin.router)
app.include_router(tts.router)
app.include_router(members.router)


@app.on_event("startup")
async def on_startup() -> None:
    """Start database, LoRa service, and background tickers safely."""
    logger.info("Starting AOJ Command OS backend")
    init_db()

    def _ack_callback(device_id: str, ack_value: str, message_id: str) -> None:
        db = SessionLocal()
        try:
            handle_firmware_ack_event(db, device_id, ack_value, message_id)
        except Exception:
            logger.exception("Firmware ACK handling failed for device_id=%s", device_id)
        finally:
            db.close()

    lora_service.set_on_ack_callback(_ack_callback)

    try:
        lora_service.start()
        logger.info("LoRa service started")
    except Exception:
        logger.exception("LoRa service failed to start")

    app.state.mission_control_task = asyncio.create_task(
        mission_control_service.ticker(),
        name="mission_control_ticker",
    )
    app.state.christy_task = asyncio.create_task(
        christy_service.ticker(),
        name="christy_ticker",
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Stop background work cleanly."""
    logger.info("Stopping AOJ Command OS backend")

    for task_name in ("mission_control_task", "christy_task"):
        task = getattr(app.state, task_name, None)
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    try:
        lora_service.stop()
        logger.info("LoRa service stopped")
    except Exception:
        logger.exception("LoRa service failed to stop cleanly")


@app.websocket("/ws/live")
async def live_updates(websocket: WebSocket) -> None:
    await websocket_manager.connect(websocket)
    try:
        await websocket_manager.send_personal_message(
            {
                "event": "system.online",
                "message": "AOJ Command OS link established",
            },
            websocket,
        )
        await websocket_manager.send_personal_message(
            {
                "event": "mission_control.state",
                "payload": mission_control_service.get_state(),
            },
            websocket,
        )

        while True:
            payload = await websocket.receive_text()
            await websocket_manager.broadcast({"event": "echo", "payload": payload})

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception:
        websocket_manager.disconnect(websocket)
        logger.exception("WebSocket /ws/live failed")


# Serve the built React frontend when frontend/dist exists.
# API routes registered above take precedence.
_dist_override = os.getenv("AOJ_FRONTEND_DIST", "").strip()
_dist_dir = (
    Path(_dist_override)
    if _dist_override
    else Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
)

if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
else:
    logger.info("Frontend dist directory not found; API-only mode active: %s", _dist_dir)
