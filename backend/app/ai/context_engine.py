"""
AI Context Engine - selectively gathers relevant operational data for Christy.

Goal:
- Give the AI enough live context to answer well.
- Avoid dumping the whole database into the prompt.
- Keep output stable, compact, and easy for advisor.py to parse.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app import models


MAX_GAME_MODES = 15
MAX_KNOWLEDGE = 6
MAX_RESULTS = 5
MAX_CRITICAL_LOGS = 8
MAX_MODE_DESCRIPTION_CHARS = 220
MAX_KNOWLEDGE_CHARS = 320


class AIContextSnapshot:
    """Structured container for AI assistant context."""

    def __init__(self) -> None:
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
        """Convert context to compact AI-friendly text.

        advisor.py can parse the bracket sections, so keep names predictable.
        """
        lines: list[str] = []

        lines.append("[AI CONTEXT SNAPSHOT]")
        lines.append(f"Generated: {self.collected_at}")
        lines.append("")

        if self.active_game_session:
            lines.append("[CURRENT STATE]")
            lines.append(f"game_state={self.active_game_session.get('state', 'unknown')}")
            lines.append(f"timer_remaining_seconds={self.active_game_session.get('main_timer_seconds', 0)}")
            lines.append(
                "team_scores="
                f"red:{self.active_game_session.get('red_score', 0)},"
                f"blue:{self.active_game_session.get('blue_score', 0)}"
            )
            lines.append(f"session_name={self.active_game_session.get('name', 'unknown')}")
            lines.append("")

        if self.active_mission:
            lines.append("[MISSION]")
            lines.append(
                "title="
                f"{self.active_mission.get('title', 'unknown')}; "
                f"status={self.active_mission.get('status', 'unknown')}; "
                f"objectives={self.active_mission.get('objective_count', 0)}"
            )
            lines.append("")

        if self.schedule_status:
            lines.append("[SCHEDULE]")
            current = self.schedule_status.get("current")
            next_item = self.schedule_status.get("next")
            if current:
                lines.append(
                    f"current={current.get('title', 'none')}; "
                    f"type={current.get('activity_type', 'unknown')}"
                )
            else:
                lines.append("current=none")

            if next_item:
                lines.append(
                    f"next={next_item.get('title', 'none')}; "
                    f"type={next_item.get('activity_type', 'unknown')}; "
                    f"start={next_item.get('start_time', 'unknown')}"
                )
            else:
                lines.append("next=none")

            lines.append(
                f"progress={self.schedule_status.get('completed_count', 0)}/"
                f"{self.schedule_status.get('total_count', 0)}"
            )
            lines.append("")

        if self.device_summary:
            lines.append("[DEVICES]")
            lines.append(f"online_count={self.device_summary.get('online_count', 0)}")
            lines.append(f"offline_count={self.device_summary.get('offline_count', 0)}")
            lines.append(f"armed_count={self.device_summary.get('armed_count', 0)}")
            lines.append(f"total={self.device_summary.get('total_count', 0)}")
            issues = self.device_summary.get("issues", [])
            if issues:
                lines.append("issues=" + "; ".join(
                    f"{d.get('name', 'unknown')}:{d.get('status', 'unknown')}"
                    for d in issues[:5]
                ))
            else:
                lines.append("issues=none")
            lines.append("")

        if self.active_teams:
            lines.append("[ACTIVE TEAMS]")
            for team in self.active_teams:
                lines.append(
                    f"- {team.get('name', 'Unknown')}; "
                    f"callsign={team.get('callsign', '?')}; "
                    f"side={team.get('side', '?')}; "
                    f"score={team.get('score', 0)}"
                )
            lines.append("")

        if self.active_game_modes:
            lines.append("[ACTIVE GAME MODES]")
            for mode in self.active_game_modes:
                lines.append(f"- {mode.get('name', 'Unknown')} ({mode.get('category', 'custom')})")
                description = mode.get("description")
                if description:
                    lines.append(f"  Description: {_clean_inline(description, MAX_MODE_DESCRIPTION_CHARS)}")
            lines.append("")

        if self.latest_results:
            lines.append("[LATEST RESULTS]")
            for result in self.latest_results[:MAX_RESULTS]:
                lines.append(
                    f"- {result.get('session_name', 'Unknown')}: "
                    f"winner={result.get('winner', 'draw')}; "
                    f"red={result.get('red_points', 0)}; "
                    f"blue={result.get('blue_points', 0)}; "
                    f"at={result.get('created_at', 'unknown')}"
                )
            lines.append("")

        if self.relevant_knowledge:
            lines.append("[RELEVANT KNOWLEDGE]")
            for entry in self.relevant_knowledge:
                lines.append(
                    f"- [{entry.get('category', 'General')}] "
                    f"{entry.get('title', 'Unknown')} "
                    f"(score={entry.get('relevance_score', 0)})"
                )
                content = entry.get("content")
                if content:
                    lines.append(f"  {_clean_inline(content, MAX_KNOWLEDGE_CHARS)}")
            lines.append("")

        if self.recent_critical_logs:
            lines.append("[LOGS]")
            for log in self.recent_critical_logs[:MAX_CRITICAL_LOGS]:
                lines.append(
                    f"- [{log.get('created_at', 'unknown')}] "
                    f"{log.get('category', 'system')}: "
                    f"{_clean_inline(log.get('message', 'no message'), 160)}"
                )
            lines.append("")

        return "\n".join(lines).strip()


def _clean_inline(value: Any, max_chars: int) -> str:
    """Clean long DB text so it is prompt-safe and readable."""
    text_value = str(value or "")
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if len(text_value) <= max_chars:
        return text_value
    return text_value[: max_chars - 3].rstrip() + "..."


def _safe_enum_value(value: Any) -> str:
    """Return enum.value where available, otherwise a safe string."""
    return str(getattr(value, "value", value))


def _extract_keywords(text_value: str) -> set[str]:
    """Extract useful keywords from English/Japanese mixed prompts."""
    if not text_value:
        return set()

    english_tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_'-]{2,}\b", text_value.lower())
    japanese_tokens = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]{2,}", text_value)

    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "are", "was", "been",
        "have", "has", "will", "would", "could", "should", "can", "may", "must",
        "might", "into", "your", "our", "their", "what", "which", "who", "where",
        "when", "why", "how", "all", "each", "every", "both", "such", "more",
        "most", "some", "any", "many", "few", "several", "only", "very", "just",
        "even", "also", "too", "please", "need", "want", "tell", "give", "make",
        "help", "about", "using", "used", "current", "status", "info",
    }

    return {token for token in english_tokens if token not in stopwords} | set(japanese_tokens)


def _parse_tags(raw_tags: Any) -> list[str]:
    if not raw_tags:
        return []

    if isinstance(raw_tags, list):
        return [str(tag) for tag in raw_tags]

    if isinstance(raw_tags, str):
        try:
            parsed = json.loads(raw_tags)
            if isinstance(parsed, list):
                return [str(tag) for tag in parsed]
        except (json.JSONDecodeError, TypeError):
            return [part.strip() for part in raw_tags.split(",") if part.strip()]

    return []


def _calculate_relevance(knowledge_entry: models.CustomKnowledgeEntry, prompt_keywords: set[str]) -> float:
    """Calculate simple but stable relevance score from title/category/content/tags."""
    if not prompt_keywords:
        return 0.0

    weighted_score = 0.0

    title_keywords = _extract_keywords(getattr(knowledge_entry, "title", "") or "")
    category_keywords = _extract_keywords(getattr(knowledge_entry, "category", "") or "")
    content_keywords = _extract_keywords(getattr(knowledge_entry, "content", "") or "")
    tag_keywords: set[str] = set()
    for tag in _parse_tags(getattr(knowledge_entry, "tags", None)):
        tag_keywords |= _extract_keywords(tag)

    weighted_score += len(title_keywords & prompt_keywords) * 3.0
    weighted_score += len(category_keywords & prompt_keywords) * 2.0
    weighted_score += len(tag_keywords & prompt_keywords) * 2.5
    weighted_score += len(content_keywords & prompt_keywords) * 1.0

    # Normalize enough for sorting and display. Not a true probability.
    return min(1.0, weighted_score / max(3.0, len(prompt_keywords) * 2.0))


def _safe_query_all(query, fallback: list[Any] | None = None) -> list[Any]:
    try:
        return query.all()
    except Exception:
        return fallback or []


def collect_context(db: Session, prompt: str = "", mission_id: int | None = None) -> AIContextSnapshot:
    """Collect and aggregate limited AI context from the database."""
    snapshot = AIContextSnapshot()
    now = datetime.utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
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
        active_mission = (
            db.query(models.Mission)
            .filter(models.Mission.id == active_session.mission_id)
            .first()
        )

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
            "status": _safe_enum_value(active_mission.status),
            "objective_count": objectives_count,
        }

    if active_session is not None:
        snapshot.active_game_session = {
            "id": active_session.id,
            "name": active_session.name,
            "state": _safe_enum_value(active_session.state),
            "red_score": active_session.red_score,
            "blue_score": active_session.blue_score,
            "main_timer_seconds": active_session.main_timer_seconds,
            "is_active": active_session.is_active,
        }

        teams = (
            db.query(models.Team)
            .filter(models.Team.game_session_id == active_session.id)
            .order_by(models.Team.side.asc(), models.Team.name.asc())
            .all()
        )
        snapshot.active_teams = [
            {
                "id": team.id,
                "name": team.name,
                "callsign": team.callsign,
                "side": _safe_enum_value(team.side),
                "score": team.score,
            }
            for team in teams
        ]

    schedule_query = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.is_complete.is_(False),
        models.ScheduleItem.start_time >= day_start,
        models.ScheduleItem.start_time < day_end,
    )
    if active_mission is not None:
        schedule_query = schedule_query.filter(models.ScheduleItem.mission_id == active_mission.id)

    current_schedule = (
        schedule_query.filter(
            models.ScheduleItem.start_time <= now
        )
        .order_by(models.ScheduleItem.start_time.desc(), models.ScheduleItem.id.desc())
        .first()
    )

    next_schedule = (
        schedule_query
        .filter(models.ScheduleItem.start_time >= now)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .first()
    )

    base_schedule_query = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.start_time >= day_start,
        models.ScheduleItem.start_time < day_end,
    )
    if active_mission is not None:
        base_schedule_query = base_schedule_query.filter(models.ScheduleItem.mission_id == active_mission.id)

    total_schedule = base_schedule_query.count()
    completed_schedule = base_schedule_query.filter(models.ScheduleItem.is_complete.is_(True)).count()

    snapshot.schedule_status = {
        "current": {
            "title": current_schedule.title,
            "activity_type": current_schedule.activity_type,
            "start_time": current_schedule.start_time.isoformat() + "Z",
        } if current_schedule else None,
        "next": {
            "title": next_schedule.title,
            "activity_type": next_schedule.activity_type,
            "start_time": next_schedule.start_time.isoformat() + "Z",
        } if next_schedule else None,
        "completed_count": completed_schedule,
        "total_count": total_schedule,
    }

    latest_results = (
        db.query(models.GameResult)
        .order_by(models.GameResult.created_at.desc(), models.GameResult.id.desc())
        .limit(MAX_RESULTS)
        .all()
    )
    snapshot.latest_results = [
        {
            "id": result.id,
            "session_name": result.session_name,
            "winner": _safe_enum_value(result.winner),
            "red_points": result.red_points,
            "blue_points": result.blue_points,
            "created_at": result.created_at.isoformat() + "Z",
        }
        for result in latest_results
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
    total_devices = db.query(func.count(models.Device.id)).scalar() or 0

    issues = (
        db.query(models.Device)
        .filter(
            models.Device.status.in_(
                [
                    models.DeviceStatus.alarm,
                    models.DeviceStatus.maintenance,
                    models.DeviceStatus.offline,
                ]
            )
        )
        .order_by(models.Device.updated_at.desc(), models.Device.id.desc())
        .limit(8)
        .all()
    )

    snapshot.device_summary = {
        "online_count": online_count,
        "offline_count": offline_count,
        "armed_count": armed_count,
        "total_count": total_devices,
        "issues": [
            {
                "id": device.id,
                "name": device.name,
                "status": _safe_enum_value(device.status),
            }
            for device in issues
        ],
    }

    active_modes_query = (
        db.query(models.CustomGameMode)
        .filter(models.CustomGameMode.active.is_(True))
    )

    # If user asks about a specific mode/category, bias relevant modes first.
    if prompt_keywords:
        like_terms = [f"%{kw}%" for kw in prompt_keywords if len(kw) >= 3 and re.match(r"^[a-zA-Z0-9_'-]+$", kw)]
        if like_terms:
            active_modes_query = active_modes_query.order_by(
                # SQLite-compatible enough when backed by SQLAlchemy.
                models.CustomGameMode.name.asc()
            )

    active_modes = active_modes_query.limit(MAX_GAME_MODES).all()
    snapshot.active_game_modes = [
        {
            "id": mode.id,
            "name": mode.name,
            "category": mode.category,
            "description": _clean_inline(mode.description, MAX_MODE_DESCRIPTION_CHARS) if mode.description else "",
        }
        for mode in active_modes
    ]

    if prompt_keywords:
        relevant_knowledge = (
            db.query(models.CustomKnowledgeEntry)
            .filter(models.CustomKnowledgeEntry.active.is_(True))
            .all()
        )

        scored_entries = [
            (entry, _calculate_relevance(entry, prompt_keywords))
            for entry in relevant_knowledge
        ]
        scored_entries.sort(key=lambda item: item[1], reverse=True)

        snapshot.relevant_knowledge = [
            {
                "id": entry.id,
                "title": entry.title,
                "category": entry.category,
                "content": _clean_inline(entry.content, MAX_KNOWLEDGE_CHARS) if entry.content else "",
                "relevance_score": round(score, 2),
            }
            for entry, score in scored_entries[:MAX_KNOWLEDGE]
            if score > 0.0
        ]

    try:
        critical_logs = db.execute(
            text(
                "SELECT created_at, category, message "
                "FROM system_logs "
                "WHERE UPPER(level) IN ('CRITICAL', 'ERROR') "
                "ORDER BY created_at DESC, id DESC "
                "LIMIT :limit"
            ),
            {"limit": MAX_CRITICAL_LOGS},
        ).fetchall()
    except Exception:
        critical_logs = []

    snapshot.recent_critical_logs = [
        {
            "created_at": str(log[0]),
            "category": str(log[1]),
            "message": _clean_inline(log[2], 200),
        }
        for log in critical_logs
    ]

    return snapshot
