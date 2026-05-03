import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGIN_REGEX
from app.core.ai_safety import AISafetyMiddleware
from app.core.websocket import websocket_manager
from app.database import init_db
from app.lora.service import lora_service
from app.routes import ai, health, logs, members, mission_control, prop_network, resources, results, schedule, system, update_center, custom_admin, tts
from app.services.mission_control_service import mission_control_service
from app.services.christy_service import christy_service

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# Local-network oriented CORS configuration for browser clients on LAN devices.
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
def on_startup() -> None:
    init_db()
    lora_service.start()
    asyncio.create_task(mission_control_service.ticker())
    asyncio.create_task(christy_service.ticker())


@app.on_event("shutdown")
def on_shutdown() -> None:
    lora_service.stop()


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


# Serve the built React frontend when frontend/dist exists.
# This enables single-process production mode: one uvicorn process on :8000
# serves both the API and the UI.  API routes registered above take precedence.
_dist_override = os.getenv("AOJ_FRONTEND_DIST", "").strip()
_dist_dir = Path(_dist_override) if _dist_override else (Path(__file__).resolve().parent.parent.parent / "frontend" / "dist")
if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
