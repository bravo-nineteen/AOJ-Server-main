import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.config import APP_TITLE, APP_VERSION, CORS_ORIGIN_REGEX
from app.core.auth import authorize_request
from app.core.ai_safety import AISafetyMiddleware
from app.core.websocket import websocket_manager
from app.database import SessionLocal, init_db
from app.lora.service import LoRaIncomingFrame, lora_service
from app.routes import (
    ai,
    announcement_rules,
    announcements,
    custom_admin,
    firmware_rollouts,
    game_events,
    game_modes,
    health,
    logs,
    members,
    missions,
    mission_control,
    players,
    prop_network,
    resources,
    results,
    schedule,
    scores,
    system,
    system_logs,
    system_settings,
    tts,
    update_center,
)
from app.services.christy_service import christy_service
from app.services.log_service import log_action
from app.services.mission_control_service import mission_control_service
from app.services.scheduled_announcements_service import scheduled_announcements_service
from app.services.update_center_service import handle_firmware_ack_event

logger = logging.getLogger(__name__)


class JsonLogFormatter(logging.Formatter):
    """Emit newline-delimited JSON logs for easier parsing in production."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def _configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)


_configure_logging()

# lifespan is defined later in this file; forward-assigned after definition
app = FastAPI(title=APP_TITLE, version=APP_VERSION)

def _custom_openapi():
    """Generate OpenAPI schema with proper documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=APP_TITLE,
        version=APP_VERSION,
        description="Local-first command system for airsoft field operations with LoRa-connected props, AI assistant, mission control, and real-time WebSocket updates.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = _custom_openapi


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AISafetyMiddleware)


@app.middleware("http")
async def request_access_and_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.perf_counter()

    decision = authorize_request(request.method, request.url.path, request.headers)
    if not decision.allowed:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.warning(
            "request_denied method=%s path=%s status=%s role=%s latency_ms=%.2f",
            request.method,
            request.url.path,
            decision.status_code,
            decision.role,
            elapsed_ms,
            extra={"request_id": request_id},
        )
        response = JSONResponse(
            status_code=decision.status_code,
            content={"detail": decision.detail, "request_id": request_id},
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-ms"] = str(elapsed_ms)
        return response

    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-ms"] = str(elapsed_ms)

    logger.info(
        "request_complete method=%s path=%s status=%s latency_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        extra={"request_id": request_id},
    )
    return response

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
app.include_router(players.router)
app.include_router(announcement_rules.router)
app.include_router(announcements.router)
app.include_router(game_events.router)
app.include_router(game_modes.router)
app.include_router(missions.router)
app.include_router(scores.router)
app.include_router(system_logs.router)
app.include_router(system_settings.router)
app.include_router(firmware_rollouts.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown."""
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("Starting AOJ Command OS backend")
    init_db()

    def _ack_callback(device_id: str, ack_value: str, message_id: str) -> None:
        db = SessionLocal()
        try:
            handle_firmware_ack_event(db, device_id, ack_value, message_id)
        except Exception as e:
            logger.exception("Firmware ACK handling failed for device_id=%s: %s", device_id, str(e))
        finally:
            db.close()

    def _incoming_callback(frame: LoRaIncomingFrame) -> None:
        db = SessionLocal()
        try:
            level = models.LogLevel.info
            if frame.command in {"EXPLODED", "TRIGGER_ALARM"}:
                level = models.LogLevel.warning
            log_action(
                db,
                level=level,
                category=models.LogCategory.lora,
                source="lora_inbound",
                message=(
                    f"RX {frame.device_id} {frame.command} value={frame.value} "
                    f"message_id={frame.message_id}"
                ),
            )
        except Exception as e:
            logger.exception("Inbound LoRa logging failed for device_id=%s: %s", frame.device_id, str(e))
        finally:
            db.close()

    loop = asyncio.get_running_loop()

    def _timeout_callback(device_id: str, message_id: str, retries: int) -> None:
        db = SessionLocal()
        try:
            log_action(
                db,
                level=models.LogLevel.error,
                category=models.LogCategory.lora,
                source="lora_timeout",
                message=(
                    f"ACK timeout device_id={device_id} message_id={message_id} retries={retries}"
                ),
            )
        except Exception as e:
            logger.exception("LoRa timeout logging failed for device_id=%s: %s", device_id, str(e))
        finally:
            db.close()

        try:
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast(
                    {
                        "event": "lora.ack_timeout",
                        "payload": {
                            "device_id": device_id,
                            "message_id": message_id,
                            "retries": retries,
                        },
                    }
                ),
                loop,
            )
        except Exception as e:
            logger.exception("LoRa timeout websocket broadcast failed for device_id=%s: %s", device_id, str(e))

    lora_service.set_on_ack_callback(_ack_callback)
    lora_service.set_on_incoming_callback(_incoming_callback)
    lora_service.set_on_timeout_callback(_timeout_callback)

    try:
        lora_service.start()
        logger.info("LoRa service started")
    except Exception as e:
        logger.exception("LoRa service failed to start: %s", str(e))

    app.state.mission_control_task = asyncio.create_task(
        mission_control_service.ticker(),
        name="mission_control_ticker",
    )
    app.state.christy_task = asyncio.create_task(
        christy_service.ticker(),
        name="christy_ticker",
    )
    app.state.scheduled_announcements_task = asyncio.create_task(
        scheduled_announcements_service.ticker(),
        name="scheduled_announcements_ticker",
    )

    yield  # Application is running

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("Stopping AOJ Command OS backend")

    for task_name in ("mission_control_task", "christy_task", "scheduled_announcements_task"):
        task = getattr(app.state, task_name, None)
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    try:
        lora_service.stop()
        logger.info("LoRa service stopped")
    except Exception as e:
        logger.exception("LoRa service failed to stop cleanly: %s", str(e))


# Wire the lifespan into the app after it is defined
app.router.lifespan_context = lifespan


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
        logger.info("WebSocket client disconnected normally")
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", str(e), exc_info=True)
        websocket_manager.disconnect(websocket)

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
_uploads_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
else:
    logger.info("Frontend dist directory not found; API-only mode active: %s", _dist_dir)
