import asyncio
from copy import deepcopy
from datetime import datetime

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.log_service import log_action
from app.websocket_manager import websocket_manager


class MissionControlService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state: dict = {
            "mission_id": None,
            "mission_title": "No mission loaded",
            "game_mode": "Skirmish",
            "state": "idle",
            "main_timer_seconds": 0,
            "phase_timer_seconds": 0,
            "red_team_score": 0,
            "blue_team_score": 0,
            "objectives": [],
            "event_feed": [],
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_state(self) -> dict:
        return deepcopy(self._state)

    async def create_mission(
        self, db: Session, payload: schemas.MissionControlCreateMissionRequest
    ) -> dict:
        async with self._lock:
            mission = models.Mission(
                title=payload.title,
                description=payload.description,
                status=models.MissionStatus.planned,
            )
            db.add(mission)
            db.commit()
            db.refresh(mission)

            session = models.GameSession(
                mission_id=mission.id,
                name=f"{payload.title} Session",
                is_active=False,
            )
            db.add(session)
            db.commit()

            objectives = [
                {"id": idx + 1, "label": label, "status": "pending"}
                for idx, label in enumerate(payload.objectives)
            ]

            self._state.update(
                {
                    "mission_id": mission.id,
                    "mission_title": payload.title,
                    "game_mode": payload.game_mode,
                    "state": "ready",
                    "main_timer_seconds": payload.main_timer_seconds,
                    "phase_timer_seconds": payload.phase_timer_seconds,
                    "red_team_score": 0,
                    "blue_team_score": 0,
                    "objectives": objectives,
                    "event_feed": [],
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

            self._push_event_locked(f"Mission created: {payload.title}")
            log_action(
                db,
                level=models.LogLevel.info,
                category=models.LogCategory.mission,
                source="mission_control",
                message=f"Mission created: {payload.title} ({payload.game_mode})",
            )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def start_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["mission_id"] is None:
                return self.get_state()
            self._state["state"] = "running"
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game started")
            db.query(models.Mission).filter(
                models.Mission.id == self._state["mission_id"]
            ).update({"status": models.MissionStatus.active, "start_time": datetime.utcnow()})
            db.query(models.GameSession).filter(
                models.GameSession.mission_id == self._state["mission_id"]
            ).update({"is_active": True, "start_time": datetime.utcnow()})
            db.commit()
            log_action(
                db,
                level=models.LogLevel.info,
                category=models.LogCategory.mission,
                source="mission_control",
                message=f"Game started for mission_id={self._state['mission_id']}",
            )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def pause_game(self, db: Session | None = None) -> dict:
        async with self._lock:
            if self._state["state"] == "running":
                self._state["state"] = "paused"
                self._state["updated_at"] = datetime.utcnow().isoformat()
                self._push_event_locked("Game paused")
                if db is not None:
                    log_action(
                        db,
                        level=models.LogLevel.warning,
                        category=models.LogCategory.mission,
                        source="mission_control",
                        message=f"Game paused for mission_id={self._state['mission_id']}",
                    )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def resume_game(self, db: Session | None = None) -> dict:
        async with self._lock:
            if self._state["state"] == "paused":
                self._state["state"] = "running"
                self._state["updated_at"] = datetime.utcnow().isoformat()
                self._push_event_locked("Game resumed")
                if db is not None:
                    log_action(
                        db,
                        level=models.LogLevel.info,
                        category=models.LogCategory.mission,
                        source="mission_control",
                        message=f"Game resumed for mission_id={self._state['mission_id']}",
                    )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def end_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["mission_id"] is None:
                return self.get_state()
            self._state["state"] = "ended"
            self._state["main_timer_seconds"] = 0
            self._state["phase_timer_seconds"] = 0
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game ended")
            db.query(models.Mission).filter(
                models.Mission.id == self._state["mission_id"]
            ).update({"status": models.MissionStatus.complete, "end_time": datetime.utcnow()})
            db.query(models.GameSession).filter(
                models.GameSession.mission_id == self._state["mission_id"]
            ).update({"is_active": False, "end_time": datetime.utcnow()})
            db.commit()
            log_action(
                db,
                level=models.LogLevel.info,
                category=models.LogCategory.mission,
                source="mission_control",
                message=f"Game ended for mission_id={self._state['mission_id']}",
            )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def adjust_score(
        self, payload: schemas.MissionControlScoreRequest, db: Session | None = None
    ) -> dict:
        async with self._lock:
            if payload.team == "red":
                self._state["red_team_score"] = max(
                    0, self._state["red_team_score"] + payload.delta
                )
            if payload.team == "blue":
                self._state["blue_team_score"] = max(
                    0, self._state["blue_team_score"] + payload.delta
                )
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked(
                f"Score update {payload.team.upper()} {payload.delta:+d} ({payload.reason})"
            )
            if db is not None:
                log_action(
                    db,
                    level=models.LogLevel.info,
                    category=models.LogCategory.mission,
                    source="mission_control",
                    message=(
                        f"Score update team={payload.team} delta={payload.delta} "
                        f"reason={payload.reason}"
                    ),
                )
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def set_objective_status(
        self,
        objective_id: int,
        payload: schemas.MissionControlObjectiveStatusRequest,
        db: Session | None = None,
    ) -> dict:
        async with self._lock:
            for objective in self._state["objectives"]:
                if objective["id"] == objective_id:
                    objective["status"] = payload.status
                    self._push_event_locked(
                        f"Objective {objective['label']} -> {payload.status.upper()}"
                    )
                    if db is not None:
                        log_action(
                            db,
                            level=models.LogLevel.info,
                            category=models.LogCategory.mission,
                            source="mission_control",
                            message=(
                                f"Objective update id={objective_id} "
                                f"label={objective['label']} status={payload.status}"
                            ),
                        )
                    break
            self._state["updated_at"] = datetime.utcnow().isoformat()
            snapshot = self.get_state()

        await self.broadcast_state(snapshot)
        return snapshot

    async def ticker(self) -> None:
        while True:
            await asyncio.sleep(1)
            should_broadcast = False
            async with self._lock:
                if self._state["state"] == "running":
                    if self._state["main_timer_seconds"] > 0:
                        self._state["main_timer_seconds"] -= 1
                    if self._state["phase_timer_seconds"] > 0:
                        self._state["phase_timer_seconds"] -= 1
                    if self._state["main_timer_seconds"] == 0:
                        self._state["state"] = "ended"
                        self._push_event_locked("Main timer reached zero")
                    self._state["updated_at"] = datetime.utcnow().isoformat()
                    should_broadcast = True
                snapshot = self.get_state()

            if should_broadcast:
                await self.broadcast_state(snapshot)

    async def broadcast_state(self, snapshot: dict | None = None) -> None:
        payload = snapshot if snapshot is not None else self.get_state()
        await websocket_manager.broadcast(
            {"event": "mission_control.state", "payload": payload}
        )

    def _push_event_locked(self, message: str) -> None:
        line = f"{datetime.utcnow().strftime('%H:%M:%S')}Z :: {message}"
        self._state["event_feed"] = [line, *self._state["event_feed"]][:30]


mission_control_service = MissionControlService()
