"""
AI Context Engine - Selectively gathers relevant operational data for AI assistant.

Collects limited, actionable context without overwhelming the AI with full database dumps.
Each component is optional and can be None if not available.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app import models


class AIContextSnapshot:
    """Structured container for AI assistant context."""

    def __init__(self):
        self.active_mission: dict[str, Any] | None = None
        self.active_game_session: dict[str, Any] | None = None
        self.schedule_status: dict[str, Any] | None = None
        self.latest_results: list[dict[str, Any]] = []
        self.device_summary: dict[str, Any] = {}
        self.active_teams: list[dict[str, Any]] = []
        self.active_game_modes: list[dict[str, Any]] = []
        self.relevant_knowledge: list[dict[str, Any]] = []
        self.recent_critical_logs: list[dict[str, Any]] = []
        self.collected_at: str = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict[str, Any]:
        return {
            "collected_at": self.collected_at,
            "active_mission": self.active_mission,
            "active_game_session": self.active_game_session,
            "schedule_status": self.schedule_status,
            "latest_results": self.latest_results,
            "device_summary": self.device_summary,
            "active_teams": self.active_teams,
            "active_game_modes": self.active_game_modes,
            "relevant_knowledge": self.relevant_knowledge,
            "recent_critical_logs": self.recent_critical_logs,
        }

    def to_formatted_text(self) -> str:
        """Convert context to human-readable AI-friendly text format."""
        lines: list[str] = []

        lines.append("[AI CONTEXT SNAPSHOT]")
        lines.append(f"Generated: {self.collected_at}")
        lines.append("")

        if self.active_mission:
            lines.append("[ACTIVE MISSION]")
            lines.append(f"- Title: {self.active_mission.get('title', 'unknown')}")
            lines.append(f"- Status: {self.active_mission.get('status', 'unknown')}")
            lines.append(f"- Objectives: {self.active_mission.get('objective_count', 0)} total")
            lines.append("")

        if self.active_game_session:
            lines.append("[ACTIVE GAME SESSION]")
            lines.append(f"- Name: {self.active_game_session.get('name', 'unknown')}")
            lines.append(f"- State: {self.active_game_session.get('state', 'unknown')}")
            lines.append(f"- Red Score: {self.active_game_session.get('red_score', 0)}")
            lines.append(f"- Blue Score: {self.active_game_session.get('blue_score', 0)}")
            lines.append(f"- Timer: {self.active_game_session.get('main_timer_seconds', 0)}s remaining")
            lines.append("")

        if self.schedule_status:
            lines.append("[SCHEDULE STATUS]")
            if self.schedule_status.get("current"):
                lines.append(f"- Current: {self.schedule_status['current'].get('title', 'none')}")
            if self.schedule_status.get("next"):
                lines.append(f"- Next: {self.schedule_status['next'].get('title', 'none')}")
            lines.append(f"- Progress: {self.schedule_status.get('completed_count', 0)}/{self.schedule_status.get('total_count', 0)} complete")
            lines.append("")

        if self.latest_results:
            lines.append("[LATEST RESULTS]")
            for result in self.latest_results[:3]:
                lines.append(
                    f"- {result.get('session_name', 'Unknown')}: "
                    f"{result.get('winner', 'draw')} "
                    f"(RED {result.get('red_points', 0)}, BLUE {result.get('blue_points', 0)})"
                )
            lines.append("")

        if self.device_summary:
            lines.append("[DEVICE STATUS SUMMARY]")
            lines.append(f"- Online: {self.device_summary.get('online_count', 0)}")
            lines.append(f"- Offline: {self.device_summary.get('offline_count', 0)}")
            lines.append(f"- Armed: {self.device_summary.get('armed_count', 0)}")
            if self.device_summary.get("issues"):
                lines.append(f"- Issues: {len(self.device_summary.get('issues', []))} devices")
            lines.append("")

        if self.active_teams:
            lines.append("[ACTIVE TEAMS]")
            for team in self.active_teams:
                lines.append(f"- {team.get('name', 'Unknown')}: {team.get('callsign', '?')} ({team.get('side', '?')})")
            lines.append("")

        if self.active_game_modes:
            lines.append("[ACTIVE GAME MODES]")
            for mode in self.active_game_modes:
                lines.append(f"- {mode.get('name', 'Unknown')} ({mode.get('category', 'custom')})")
                if mode.get("description"):
                    lines.append(f"  Description: {mode['description'][:100]}...")
            lines.append("")

        if self.relevant_knowledge:
            lines.append("[RELEVANT KNOWLEDGE BASE]")
            for entry in self.relevant_knowledge:
                lines.append(f"- [{entry.get('category', 'General')}] {entry.get('title', 'Unknown')}")
                if entry.get("content"):
                    lines.append(f"  {entry['content'][:120]}...")
            lines.append("")

        if self.recent_critical_logs:
            lines.append("[RECENT CRITICAL LOGS]")
            for log in self.recent_critical_logs[:5]:
                timestamp = log.get("created_at", "unknown")
                message = log.get("message", "no message")
                lines.append(f"- [{timestamp}] {message[:100]}")
            lines.append("")

        return "\n".join(lines)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text for relevance matching."""
    if not text:
        return set()

    tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "are", "was",
        "been", "have", "has", "will", "would", "could", "should", "can",
        "may", "must", "might", "into", "your", "our", "their", "what",
        "which", "who", "where", "when", "why", "how", "all", "each",
        "every", "both", "such", "more", "most", "some", "any", "many",
        "few", "several", "only", "very", "just", "even", "also", "too",
    }
    return {token for token in tokens if token not in stopwords}


def _calculate_relevance(knowledge_entry: models.CustomKnowledgeEntry, prompt_keywords: set[str]) -> float:
    """Calculate relevance score (0.0 to 1.0) based on keyword matches."""
    if not prompt_keywords:
        return 0.0

    matched_keywords: set[str] = set()

    if knowledge_entry.title:
        matched_keywords.update(_extract_keywords(knowledge_entry.title) & prompt_keywords)

    if knowledge_entry.category:
        matched_keywords.update(_extract_keywords(knowledge_entry.category) & prompt_keywords)

    if knowledge_entry.content:
        matched_keywords.update(_extract_keywords(knowledge_entry.content) & prompt_keywords)

    if knowledge_entry.tags:
        try:
            tags_list = json.loads(knowledge_entry.tags) if isinstance(knowledge_entry.tags, str) else knowledge_entry.tags
            if isinstance(tags_list, list):
                for tag in tags_list:
                    matched_keywords.update(_extract_keywords(str(tag)) & prompt_keywords)
        except (json.JSONDecodeError, TypeError):
            pass

    if not prompt_keywords:
        return 0.0
    return len(matched_keywords) / len(prompt_keywords)


def collect_context(db: Session, prompt: str = "", mission_id: int | None = None) -> AIContextSnapshot:
    """Collect and aggregate limited AI context from the database."""
    snapshot = AIContextSnapshot()
    now = datetime.utcnow()

    prompt_keywords = _extract_keywords(prompt)

    active_session = (
        db.query(models.GameSession)
        .filter(models.GameSession.is_active.is_(True))
        .order_by(models.GameSession.updated_at.desc(), models.GameSession.id.desc())
        .first()
    )

    active_mission = None
    if mission_id is not None:
        active_mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if active_mission is None and active_session is not None and active_session.mission_id is not None:
        active_mission = db.query(models.Mission).filter(models.Mission.id == active_session.mission_id).first()

    if active_mission is not None:
        objectives_count = (
            db.query(func.count(models.MissionObjective.id))
            .filter(models.MissionObjective.mission_id == active_mission.id)
            .scalar()
            or 0
        )
        snapshot.active_mission = {
            "id": active_mission.id,
            "title": active_mission.title,
            "status": active_mission.status.value,
            "objective_count": objectives_count,
        }

    if active_session is not None:
        snapshot.active_game_session = {
            "id": active_session.id,
            "name": active_session.name,
            "state": active_session.state,
            "red_score": active_session.red_score,
            "blue_score": active_session.blue_score,
            "main_timer_seconds": active_session.main_timer_seconds,
            "is_active": active_session.is_active,
        }

        teams = (
            db.query(models.Team)
            .filter(models.Team.game_session_id == active_session.id)
            .all()
        )
        snapshot.active_teams = [
            {
                "id": t.id,
                "name": t.name,
                "callsign": t.callsign,
                "side": t.side.value,
                "score": t.score,
            }
            for t in teams
        ]

    schedule_query = db.query(models.ScheduleItem).filter(models.ScheduleItem.is_complete.is_(False))
    if active_mission is not None:
        schedule_query = schedule_query.filter(models.ScheduleItem.mission_id == active_mission.id)

    current_schedule = schedule_query.filter(
        and_(
            models.ScheduleItem.start_time <= now,
            models.ScheduleItem.end_time >= now,
        )
    ).first()

    next_schedule = (
        schedule_query
        .filter(models.ScheduleItem.start_time >= now)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .first()
    )

    total_schedule = (
        db.query(func.count(models.ScheduleItem.id))
        .filter(models.ScheduleItem.is_complete.is_(False))
        .scalar()
        or 0
    )
    completed_schedule = (
        db.query(func.count(models.ScheduleItem.id))
        .filter(models.ScheduleItem.is_complete.is_(True))
        .scalar()
        or 0
    )

    snapshot.schedule_status = {
        "current": {
            "title": current_schedule.title,
            "activity_type": current_schedule.activity_type,
        } if current_schedule else None,
        "next": {
            "title": next_schedule.title,
            "activity_type": next_schedule.activity_type,
            "start_time": next_schedule.start_time.isoformat() + "Z",
        } if next_schedule else None,
        "completed_count": completed_schedule,
        "total_count": total_schedule + completed_schedule,
    }

    latest_results = (
        db.query(models.GameResult)
        .order_by(models.GameResult.created_at.desc(), models.GameResult.id.desc())
        .limit(5)
        .all()
    )
    snapshot.latest_results = [
        {
            "id": r.id,
            "session_name": r.session_name,
            "winner": r.winner.value,
            "red_points": r.red_points,
            "blue_points": r.blue_points,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in latest_results
    ]

    online_count = (
        db.query(func.count(models.Device.id))
        .filter(models.Device.status == models.DeviceStatus.online)
        .scalar()
        or 0
    )
    offline_count = (
        db.query(func.count(models.Device.id))
        .filter(models.Device.status == models.DeviceStatus.offline)
        .scalar()
        or 0
    )
    armed_count = (
        db.query(func.count(models.Device.id))
        .filter(models.Device.status == models.DeviceStatus.armed)
        .scalar()
        or 0
    )

    issues = (
        db.query(models.Device)
        .filter(
            models.Device.status.in_(
                [models.DeviceStatus.alarm, models.DeviceStatus.maintenance]
            )
        )
        .all()
    )

    snapshot.device_summary = {
        "online_count": online_count,
        "offline_count": offline_count,
        "armed_count": armed_count,
        "total_count": online_count + offline_count,
        "issues": [
            {
                "id": d.id,
                "name": d.name,
                "status": d.status.value,
            }
            for d in issues
        ],
    }

    active_modes = (
        db.query(models.CustomGameMode)
        .filter(models.CustomGameMode.active.is_(True))
        .limit(10)
        .all()
    )
    snapshot.active_game_modes = [
        {
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "description": m.description[:150] if m.description else "",
        }
        for m in active_modes
    ]

    if prompt_keywords:
        # AI context must use active knowledge entries only.
        relevant_knowledge = (
            db.query(models.CustomKnowledgeEntry)
            .filter(models.CustomKnowledgeEntry.active.is_(True))
            .all()
        )

        scored_entries = [
            (entry, _calculate_relevance(entry, prompt_keywords))
            for entry in relevant_knowledge
        ]
        scored_entries.sort(key=lambda x: x[1], reverse=True)

        snapshot.relevant_knowledge = [
            {
                "id": entry.id,
                "title": entry.title,
                "category": entry.category,
                "content": entry.content[:200] if entry.content else "",
                "relevance_score": round(score, 2),
            }
            for entry, score in scored_entries[:5]
            if score > 0.0
        ]

    critical_logs = db.execute(
        text(
            "SELECT created_at, category, message "
            "FROM system_logs "
            "WHERE UPPER(level) = 'CRITICAL' "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT 10"
        ),
    ).fetchall()

    snapshot.recent_critical_logs = [
        {
            "created_at": str(log[0]),
            "category": str(log[1]),
            "message": str(log[2])[:200],
        }
        for log in critical_logs
    ]

    return snapshot
