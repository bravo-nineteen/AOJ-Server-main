import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.connection_metadata: dict[WebSocket, dict] = {}  # Track connection metadata
        self.heartbeat_interval = 30  # seconds
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "connected_at": datetime.now(timezone.utc),
            "last_message_at": datetime.now(timezone.utc),
            "message_count": 0,
        }
        logger.info("WebSocket client connected. Total connections: %d", len(self.active_connections))
        
        # Start heartbeat task if not already running
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        logger.info("WebSocket client disconnected. Remaining connections: %d", len(self.active_connections))

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        await websocket.send_json(message)

    async def broadcast(self, message: dict) -> None:
        stale_connections: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug("WebSocket broadcast failed, marking connection stale: %s", str(e), exc_info=True)
                stale_connections.append(connection)

        for stale in stale_connections:
            self.disconnect(stale)
            logger.info("Disconnected stale WebSocket connection")

    @property
    def connected_count(self) -> int:
        return len(self.active_connections)

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat pings to detect stale connections."""
        try:
            while self.active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeats()
        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            logger.error("Heartbeat loop error: %s", str(e), exc_info=True)

    async def _send_heartbeats(self) -> None:
        """Send ping messages to all connected clients."""
        stale_connections = []
        timestamp = datetime.now(timezone.utc).isoformat()
        
        for connection in list(self.active_connections):
            try:
                await connection.send_json({
                    "event": "system.heartbeat",
                    "timestamp": timestamp
                })
            except Exception as e:
                logger.debug("Failed to send heartbeat, marking connection stale: %s", str(e))
                stale_connections.append(connection)
        
        # Clean up stale connections
        for connection in stale_connections:
            self.disconnect(connection)


websocket_manager = WebSocketManager()
