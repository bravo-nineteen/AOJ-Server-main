import asyncio
from copy import deepcopy
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.websocket import websocket_manager
from app.services.log_service import log_action

_IDLE_STATE: dict = {
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
    "updated_at": "",
}


class MissionControlService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state: dict = {**_IDLE_STATE, "updated_at": datetime.utcnow().isoformat()}

    def get_state(self) -> dict:
        return deepcopy(self._state)

    # ------------------------------------------------------------------
    # Mission lifecycle
    # ------------------------------------------------------------------

    async def create_mission(
        self, db: Session, payload: schemas.MissionControlCreateMissionRequest
    ) -> dict:
        async with self._lock:
            if self._state["state"] in ("running", "paused"):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Cannot create a new mission while state is "
                        f"'{self._state['state']}'. End the current game first."
                    ),
                )

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

            # Persist objectives to DB so they survive a server restart.
            for obj in objectives:
                db_obj = models.MissionObjective(
                    mission_id=mission.id,
                    seq=obj["id"],
                    label=obj["label"],
                    status="pending",
                )
                db.add(db_obj)
            db.commit()

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
            log_msg = f"Mission created: {payload.title} ({payload.game_mode})"
            snapshot = self.get_state()

        log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    async def start_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["state"] != "ready":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot start game from state '{self._state['state']}'. "
                        "Mission must be in 'ready' state."
                    ),
                )
            self._state["state"] = "running"
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game started")
            mission_id = self._state["mission_id"]
            db.query(models.Mission).filter(
                models.Mission.id == mission_id
            ).update({"status": models.MissionStatus.active, "start_time": datetime.utcnow()})
            db.query(models.GameSession).filter(
                models.GameSession.mission_id == mission_id
            ).update({"is_active": True, "start_time": datetime.utcnow()})
            db.commit()
            log_msg = f"Game started for mission_id={mission_id}"
            snapshot = self.get_state()

        log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    async def pause_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["state"] != "running":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot pause game from state '{self._state['state']}'. "
                        "Game must be running."
                    ),
                )
            self._state["state"] = "paused"
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game paused")
            log_msg = f"Game paused for mission_id={self._state['mission_id']}"
            snapshot = self.get_state()

        log_action(db, level=models.LogLevel.warning, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    async def resume_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["state"] != "paused":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot resume game from state '{self._state['state']}'. "
                        "Game must be paused."
                    ),
                )
            self._state["state"] = "running"
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game resumed")
            log_msg = f"Game resumed for mission_id={self._state['mission_id']}"
            snapshot = self.get_state()

        log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    async def end_game(self, db: Session) -> dict:
        async with self._lock:
            if self._state["mission_id"] is None or self._state["state"] not in (
                "running", "paused", "ready"
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot end game from state '{self._state['state']}'. "
                        "Mission must be active."
                    ),
                )
            mission_id = self._state["mission_id"]
            self._state["state"] = "ended"
            self._state["main_timer_seconds"] = 0
            self._state["phase_timer_seconds"] = 0
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked("Game ended")
            db.query(models.Mission).filter(
                models.Mission.id == mission_id
            ).update({"status": models.MissionStatus.complete, "end_time": datetime.utcnow()})
            db.query(models.GameSession).filter(
                models.GameSession.mission_id == mission_id
            ).update({"is_active": False, "end_time": datetime.utcnow()})
            db.commit()
            log_msg = f"Game ended for mission_id={mission_id}"
            snapshot = self.get_state()  # captures "ended" state for response/broadcast

        log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)

        # Reset to idle so subsequent GET /state reflects a clean slate.
        async with self._lock:
            self._state = {**_IDLE_STATE, "updated_at": datetime.utcnow().isoformat()}

        return snapshot

    # ------------------------------------------------------------------
    # Scoring and objectives
    # ------------------------------------------------------------------

    async def adjust_score(
        self, payload: schemas.MissionControlScoreRequest, db: Session
    ) -> dict:
        async with self._lock:
            if payload.team == "red":
                self._state["red_team_score"] = max(
                    0, self._state["red_team_score"] + payload.delta
                )
            elif payload.team == "blue":
                self._state["blue_team_score"] = max(
                    0, self._state["blue_team_score"] + payload.delta
                )
            self._state["updated_at"] = datetime.utcnow().isoformat()
            self._push_event_locked(
                f"Score update {payload.team.upper()} {payload.delta:+d} ({payload.reason})"
            )
            log_msg = (
                f"Score update team={payload.team} delta={payload.delta} reason={payload.reason}"
            )
            snapshot = self.get_state()

        log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                   source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    async def set_objective_status(
        self,
        objective_id: int,
        payload: schemas.MissionControlObjectiveStatusRequest,
        db: Session,
    ) -> dict:
        log_msg: str | None = None
        async with self._lock:
            matched = False
            for objective in self._state["objectives"]:
                if objective["id"] == objective_id:
                    objective["status"] = payload.status
                    self._push_event_locked(
                        f"Objective {objective['label']} -> {payload.status.upper()}"
                    )
                    log_msg = (
                        f"Objective update id={objective_id} "
                        f"label={objective['label']} status={payload.status}"
                    )
                    matched = True
                    break
            if not matched:
                raise HTTPException(status_code=404, detail=f"Objective {objective_id} not found")
            self._state["updated_at"] = datetime.utcnow().isoformat()
            mission_id = self._state["mission_id"]
            snapshot = self.get_state()

        # Persist objective status to DB outside the lock.
        if mission_id is not None:
            db.query(models.MissionObjective).filter(
                models.MissionObjective.mission_id == mission_id,
                models.MissionObjective.seq == objective_id,
            ).update({"status": payload.status, "updated_at": datetime.utcnow()})
            db.commit()

        if log_msg:
            log_action(db, level=models.LogLevel.info, category=models.LogCategory.mission,
                       source="mission_control", message=log_msg)
        await self.broadcast_state(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Background ticker
    # ------------------------------------------------------------------

    async def ticker(self) -> None:
        while True:
            await asyncio.sleep(1)
            should_broadcast = False
            timer_expired = False
            mission_id_to_close: int | None = None

            async with self._lock:
                if self._state["state"] == "running":
                    if self._state["main_timer_seconds"] > 0:
                        self._state["main_timer_seconds"] -= 1
                    if self._state["phase_timer_seconds"] > 0:
                        self._state["phase_timer_seconds"] -= 1
                    if self._state["main_timer_seconds"] == 0:
                        self._state["state"] = "ended"
                        self._push_event_locked("Main timer reached zero – game auto-ended")
                        timer_expired = True
                        mission_id_to_close = self._state["mission_id"]
                    self._state["updated_at"] = datetime.utcnow().isoformat()
                    should_broadcast = True
                snapshot = self.get_state()

            if timer_expired and mission_id_to_close is not None:
                # Persist auto-expiry to DB outside the async lock.
                from app.database import SessionLocal  # local import avoids circular dep at module level
                db = SessionLocal()
                try:
                    db.query(models.Mission).filter(
                        models.Mission.id == mission_id_to_close
                    ).update({"status": models.MissionStatus.complete, "end_time": datetime.utcnow()})
                    db.query(models.GameSession).filter(
                        models.GameSession.mission_id == mission_id_to_close
                    ).update({"is_active": False, "end_time": datetime.utcnow()})
                    db.commit()
                    log_action(
                        db,
                        level=models.LogLevel.info,
                        category=models.LogCategory.mission,
                        source="mission_control",
                        message=f"Timer expired: mission_id={mission_id_to_close} auto-ended.",
                    )
                finally:
                    db.close()

                # Reset to idle after broadcasting the ended state.
                await self.broadcast_state(snapshot)
                async with self._lock:
                    self._state = {**_IDLE_STATE, "updated_at": datetime.utcnow().isoformat()}
            elif should_broadcast:
                await self.broadcast_state(snapshot)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def broadcast_state(self, snapshot: dict | None = None) -> None:
        payload = snapshot if snapshot is not None else self.get_state()
        await websocket_manager.broadcast(
            {"event": "mission_control.state", "payload": payload}
        )

    def _push_event_locked(self, message: str) -> None:
        line = f"{datetime.utcnow().strftime('%H:%M:%S')}Z :: {message}"
        self._state["event_feed"] = [line, *self._state["event_feed"]][:30]


mission_control_service = MissionControlService()

