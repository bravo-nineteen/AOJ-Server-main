import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import ai, health, logs, mission_control, prop_network, resources, results, schedule, system, update_center
from app.services.mission_control_service import mission_control_service
from app.websocket_manager import websocket_manager

app = FastAPI(title="AOJ Command OS API", version="0.1.0")

# Local-network oriented CORS configuration for browser clients on LAN devices.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    asyncio.create_task(mission_control_service.ticker())


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
