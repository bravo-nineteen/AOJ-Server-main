import json
from datetime import datetime
from datetime import timedelta
import re

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas
from app.ai.advisor import ask_ai
from app.ai.context_engine import collect_context
from app.core.ai_safety import ai_policy
from app.core.ai_safety import evaluate_ai_prompt
from app.models.member_profile import MemberProfile
from app.services.ai_diagnostics_service import (
    analyze_device_status,
    analyze_logs,
    analyze_mission_state,
    analyze_schedule,
)
from app.services.mission_control_service import mission_control_service

MAX_CONTEXT_CHARS = 2600
MAX_LOG_LINES = 10
MEMORY_RETENTION_DAYS = 90
MAX_MEMORY_CONTEXT_CHARS = 1200
MAX_MEMORY_MESSAGES = 24
_TREND_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with", "is",
    "are", "be", "we", "i", "you", "it", "this", "that", "what", "why", "how",
    "can", "could", "should", "would", "please", "now", "next", "game", "session",
}
_CONFIRM_ONLY_PATTERN = re.compile(
    r"^\s*(yes|yeah|yep|ok|okay|confirm|confirmed|proceed|go ahead|do it|approved|affirmative)\s*[!.?]*\s*$",
    re.IGNORECASE,
)
_CORRECTION_PREFIX_PATTERN = re.compile(
    r"\b(actually|correction|to clarify|i meant|sorry|update|rather|instead|not quite|no,|no\.)\b",
    re.IGNORECASE,
)
_LANGUAGE_VARIANTS: dict[str, str] = {
    "start": r"\b(start|begin|commence|kick\s*-?off|launch|go\s+live|open\s+up|開始)\b",
    "stop": r"\b(stop|end|finish|wrap\s+up|conclude|shut\s+down|halt|終了|停止)\b",
    "pause": r"\b(pause|hold|freeze|suspend|一時停止)\b",
    "resume": r"\b(resume|continue|carry\s+on|unpause|restart|再開)\b",
    "reset": r"\b(reset|clear|wipe|reinitialize|初期化|リセット)\b",
    "score": r"\b(score|points|tally|scoreboard|standing|得点|スコア)\b",
    "schedule": r"\b(schedule|agenda|rundown|itinerary|timetable|timeline|予定|スケジュール)\b",
    "announcement": r"\b(announcement|broadcast|notify|notification|message\s+everyone|tell\s+everyone|告知|アナウンス)\b",
    "team": r"\b(team|squad|fireteam|group|side|班|分隊)\b",
    "game_mode": r"\b(game\s*mode|mode|ruleset|variant|format|scenario|ルール|モード)\b",
    "device_issue": r"\b(device|prop|node|sensor|relay|radio|lora|terminal|unit|beacon|problem|issue|fault|malfunction|acting\s+up|故障|不具合)\b",
}
_TEAM_ALIASES: dict[str, str] = {
    "task force onyx": "Task Force Onyx",
    "onyx": "Task Force Onyx",
    "tfo": "Task Force Onyx",
    "black talon": "Black Talon",
    "talon": "Black Talon",
    "red team": "Red Team",
    "red": "Red Team",
    "blue team": "Blue Team",
    "blue": "Blue Team",
    "alpha team": "Alpha Team",
    "alpha": "Alpha Team",
    "bravo team": "Bravo Team",
    "bravo": "Bravo Team",
}
_SKILL_ALIASES: dict[str, str] = {
    "beginner": "beginner",
    "novice": "beginner",
    "new": "beginner",
    "newbie": "beginner",
    "rookie": "beginner",
    "intermediate": "intermediate",
    "experienced": "experienced",
    "advanced": "advanced",
    "expert": "expert",
    "veteran": "veteran",
    "pro": "pro",
}


def _to_json_list(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=True)


def _from_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _from_json_dict(raw: str | None) -> dict[str, dict[str, str]]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, dict[str, str]] = {}
    for key, item in value.items():
        if not isinstance(item, dict):
            continue
        normalized[str(key)] = {str(k): str(v) for k, v in item.items() if v is not None}
    return normalized


def _truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def _parse_json_list(raw: str | None) -> list[str]:
    """DEPRECATED: Use _from_json_list instead. This is identical function for compatibility."""
    return _from_json_list(raw)


def _normalize_user_language(text_value: str) -> str:
    text_value = (text_value or "").strip()
    if not text_value:
        return text_value

    lower = text_value.lower()
    canonical_terms: list[str] = []
    for canonical, pattern in _LANGUAGE_VARIANTS.items():
        if re.search(pattern, lower):
            canonical_terms.append(canonical)

    canonical_terms = list(dict.fromkeys(canonical_terms))
    if not canonical_terms:
        return text_value

    return (
        f"{text_value}\n\n"
        f"[INTERPRETED INTENT]\ncanonical_terms={', '.join(canonical_terms)}"
    )


def _extract_team_label(lower_text: str) -> str | None:
    for alias, canonical in sorted(_TEAM_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(alias)}\b", lower_text):
            return canonical
    return None


def _extract_correction_records(user_text: str) -> list[dict[str, str]]:
    lower = user_text.lower()
    records: list[dict[str, str]] = []

    name_match = re.search(r"\b([A-Z][a-z]{1,20})\b", user_text)
    subject_name = name_match.group(1) if name_match else None
    if not subject_name:
        return records

    team_label = _extract_team_label(lower)
    if team_label and (
        _CORRECTION_PREFIX_PATTERN.search(user_text)
        or re.search(r"\b(now|currently|moved|switched|assigned|plays\s+for|is\s+on)\b", lower)
    ):
        records.append({"entity": subject_name, "field": "team", "value": team_label})

    skill_match = re.search(
        r"\b(beginner|novice|new|newbie|rookie|intermediate|experienced|advanced|expert|veteran|pro)\b",
        lower,
    )
    if skill_match and (
        _CORRECTION_PREFIX_PATTERN.search(user_text) or re.search(r"\b(now|actually|update)\b", lower)
    ):
        records.append(
            {
                "entity": subject_name,
                "field": "skill",
                "value": _SKILL_ALIASES[skill_match.group(1)],
            }
        )

    callsign_match = re.search(
        r"\b([A-Z][a-z]{1,20})\b.{0,30}\bcallsign\s+(?:is|=|now)?\s*([A-Za-z0-9_-]{2,24})",
        user_text,
        re.IGNORECASE,
    )
    if callsign_match:
        records.append(
            {
                "entity": callsign_match.group(1),
                "field": "callsign",
                "value": callsign_match.group(2),
            }
        )

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        marker = (record["entity"].lower(), record["field"], record["value"])
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(record)
    return deduped


def _extract_correction_facts(user_text: str) -> list[str]:
    return [
        f"{record['entity']} {record['field']}={record['value']}"
        for record in _extract_correction_records(user_text)
    ]


def _update_correction_memory(conversation: models.AIConversation, user_text: str) -> None:
    correction_memory = _from_json_dict(conversation.correction_memory)
    now = datetime.utcnow().isoformat() + "Z"

    for record in _extract_correction_records(user_text):
        entity_key = record["entity"].lower()
        entity_entry = correction_memory.get(entity_key, {})
        entity_entry["entity"] = record["entity"]
        entity_entry[record["field"]] = record["value"]
        entity_entry["updated_at"] = now
        correction_memory[entity_key] = entity_entry

    conversation.correction_memory = json.dumps(correction_memory, ensure_ascii=True)


def _trim_conversation_history(db: Session, conversation: models.AIConversation) -> dict[str, int]:
    cutoff = datetime.utcnow() - timedelta(days=MEMORY_RETENTION_DAYS)
    expired_rows = (
        db.query(models.AIMessage.id)
        .filter(
            models.AIMessage.conversation_id == conversation.id,
            models.AIMessage.created_at < cutoff,
        )
        .all()
    )
    expired_ids = [int(row[0]) for row in expired_rows]
    if not expired_ids:
        return {"messages": 0, "action_requests": 0, "audit_logs": 0}

    deleted_audit_logs = (
        db.query(models.AIAuditLog)
        .filter(
            models.AIAuditLog.conversation_id == conversation.id,
            models.AIAuditLog.message_id.in_(expired_ids),
        )
        .delete(synchronize_session=False)
    )
    deleted_action_requests = (
        db.query(models.AIActionRequest)
        .filter(
            models.AIActionRequest.conversation_id == conversation.id,
            models.AIActionRequest.message_id.in_(expired_ids),
        )
        .delete(synchronize_session=False)
    )
    deleted_messages = (
        db.query(models.AIMessage)
        .filter(models.AIMessage.id.in_(expired_ids))
        .delete(synchronize_session=False)
    )

    return {
        "messages": int(deleted_messages),
        "action_requests": int(deleted_action_requests),
        "audit_logs": int(deleted_audit_logs),
    }


def _build_memory_context(db: Session, conversation: models.AIConversation) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=MEMORY_RETENTION_DAYS)
    rows = (
        db.query(models.AIMessage)
        .filter(
            models.AIMessage.conversation_id == conversation.id,
            models.AIMessage.created_at >= cutoff,
        )
        .order_by(models.AIMessage.created_at.desc(), models.AIMessage.id.desc())
        .limit(MAX_MEMORY_MESSAGES)
        .all()
    )

    lines: list[str] = []
    total_chars = 0
    for row in reversed(rows):
        role = row.role.value.upper()
        content = _truncate_text(row.content.replace("\n", " ").strip(), 180)
        line = f"{role}: {content}"
        if total_chars + len(line) + 1 > MAX_MEMORY_CONTEXT_CHARS:
            break
        lines.append(line)
        total_chars += len(line) + 1

    learned_trends = _parse_json_list(conversation.learned_trends)
    correction_memory = _from_json_dict(conversation.correction_memory)
    summary = conversation.memory_summary.strip()
    if summary:
        lines.append(f"LEARNED: {_truncate_text(summary, 260)}")
    if learned_trends:
        lines.append(f"TRENDS: {', '.join(learned_trends[:8])}")
    if correction_memory:
        correction_lines: list[str] = []
        for item in list(correction_memory.values())[:6]:
            entity = item.get("entity", "unknown")
            fact_parts = []
            for field_name in ("team", "skill", "callsign"):
                if item.get(field_name):
                    fact_parts.append(f"{field_name}={item[field_name]}")
            if fact_parts:
                correction_lines.append(f"{entity}: {', '.join(fact_parts)}")
        if correction_lines:
            lines.append("CORRECTIONS: " + " | ".join(correction_lines))

    return {
        "lines": lines,
        "count": len(rows),
        "cutoff": cutoff.isoformat() + "Z",
    }


def _update_conversation_learning(
    conversation: models.AIConversation,
    retained_messages: list[models.AIMessage],
) -> None:
    token_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    correction_counts: dict[str, int] = {}

    for row in retained_messages:
        if row.role == models.MessageRole.user:
            for token in re.findall(r"[a-zA-Z]{3,}", row.content.lower()):
                if token in _TREND_STOPWORDS:
                    continue
                token_counts[token] = token_counts.get(token, 0) + 1

            for fact in _extract_correction_facts(row.content):
                correction_counts[fact] = correction_counts.get(fact, 0) + 1

        for action in _parse_json_list(row.suggested_actions):
            if action.isupper() and " " not in action:
                action_counts[action] = action_counts.get(action, 0) + 1

    top_tokens = sorted(token_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    top_actions = sorted(action_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    top_corrections = sorted(correction_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]

    trends = [token for token, _ in top_tokens] + [action for action, _ in top_actions]
    trends = list(dict.fromkeys(trends))[:12]

    summary_parts: list[str] = []
    if top_actions:
        summary_parts.append(
            "frequent_actions="
            + ",".join([f"{name}:{count}" for name, count in top_actions[:4]])
        )
    if top_tokens:
        summary_parts.append(
            "top_topics=" + ",".join([f"{name}:{count}" for name, count in top_tokens[:5]])
        )
    if top_corrections:
        summary_parts.append(
            "corrections=" + " | ".join([fact for fact, _ in top_corrections[:4]])
        )

    conversation.learned_trends = _to_json_list(trends)
    conversation.memory_summary = "; ".join(summary_parts)


# ---------------------------------------------------------------------------
# Member profile learning
# ---------------------------------------------------------------------------

# Patterns for extracting member introductions from chat messages
# e.g. "this is Alex, he plays for Red Team, intermediate, good at flanking, struggles with CQB"
_MEMBER_INTRO_PATTERN = re.compile(
    r"(?:this is|meet|player|member|add|register|remember)\s+([A-Z][a-z]+'?[a-z]*)",
    re.IGNORECASE,
)
_GENDER_WORDS = {
    "he": "male", "him": "male", "his": "male", "guy": "male", "man": "male",
    "she": "female", "her": "female", "hers": "female", "girl": "female", "woman": "female",
}
_STRENGTHS_KEYWORDS = {"good at", "great at", "strength", "strong", "skilled at", "excels", "best at"}
_WEAKNESS_KEYWORDS = {"struggles", "weakness", "weak at", "bad at", "poor at", "needs work"}


def _extract_free_text_after(phrase: str, text: str) -> str:
    idx = text.lower().find(phrase.lower())
    if idx == -1:
        return ""
    rest = text[idx + len(phrase):].strip(" .,;:")
    # Take up to first sentence break
    for sep in [",", ";", "."]:
        if sep in rest:
            return rest[:rest.index(sep)].strip()
    return rest[:80].strip()


def _update_member_from_message(db: Session, user_text: str) -> None:
    """
    Parse user messages for member introductions / corrections and upsert
    MemberProfile rows. Handles patterns like:
      "This is Alex, he's on Red Team, intermediate, good at flanking, bad at CQB"
      "Alex plays for Blue Team"
      "Update Alex: she's now expert level"
      "Alex's weakness is reloading under pressure"
    """
    # Try to extract a name from the message
    match = _MEMBER_INTRO_PATTERN.search(user_text)
    if not match:
        # Also check "Alex is|plays|on" patterns
        name_match = re.search(r"\b([A-Z][a-z]{1,20})\b\s+(?:is|plays|on\s+)", user_text)
        if not name_match:
            return
        name = name_match.group(1)
    else:
        name = match.group(1)

    # Avoid false positives on common non-name words
    _NON_NAMES = {"Red", "Blue", "Team", "Game", "Mission", "Field", "Round"}
    if name in _NON_NAMES:
        return

    lower = user_text.lower()
    existing = db.query(MemberProfile).filter(
        func.lower(MemberProfile.name) == name.lower()
    ).first()

    if existing is None:
        existing = MemberProfile(name=name)
        db.add(existing)

    # Gender
    for word, gender_val in _GENDER_WORDS.items():
        if re.search(rf"\b{word}\b", lower):
            existing.gender = gender_val
            break

    # Team
    team_label = _extract_team_label(lower)
    if team_label:
        existing.team = team_label

    # Skill level
    for skill, canonical_skill in _SKILL_ALIASES.items():
        if re.search(rf"\b{re.escape(skill)}\b", lower):
            existing.skill_level = canonical_skill
            break

    # Strengths
    for phrase in _STRENGTHS_KEYWORDS:
        val = _extract_free_text_after(phrase, user_text)
        if val:
            current_strengths = existing.strengths or ""
            if val not in current_strengths:
                existing.strengths = (current_strengths + ", " + val).strip(", ")
            break

    # Weaknesses
    for phrase in _WEAKNESS_KEYWORDS:
        val = _extract_free_text_after(phrase, user_text)
        if val:
            current_weaknesses = existing.weaknesses or ""
            if val not in current_weaknesses:
                existing.weaknesses = (current_weaknesses + ", " + val).strip(", ")
            break

    # Append a Christy memory note
    prefix = "Correction noted" if _CORRECTION_PREFIX_PATTERN.search(user_text) else "Mentioned in conversation"
    note = f"{prefix}: {user_text[:120].strip()}"
    current_memory = existing.christy_memory or ""
    if note not in current_memory:
        existing.christy_memory = (current_memory + "\n" + note).strip()

    db.flush()


def _build_members_context_block(db: Session) -> list[str]:
    """Return a compact summary of all known members for the context block."""
    members = db.query(MemberProfile).order_by(MemberProfile.name).all()
    if not members:
        return ["none"]
    lines = []
    for m in members[:12]:  # cap at 12 to avoid bloating context
        parts = [m.name]
        if m.callsign:
            parts.append(f"aka {m.callsign}")
        if m.gender:
            parts.append(m.gender)
        if m.team:
            parts.append(f"team={m.team}")
        if m.skill_level:
            parts.append(f"skill={m.skill_level}")
        if m.strengths:
            parts.append(f"strengths={m.strengths[:60]}")
        if m.weaknesses:
            parts.append(f"weaknesses={m.weaknesses[:60]}")
        lines.append("; ".join(parts))
    return lines


def _format_schedule_item(item: models.ScheduleItem | None) -> str:
    if item is None:
        return "none"
    return (
        f"{item.title} ({item.activity_type}) "
        f"{item.start_time.isoformat()}Z -> {item.end_time.isoformat()}Z"
    )



def _build_context_block(sections: dict[str, list[str]]) -> str:
    ordered = ["CURRENT STATE", "MISSION", "SCHEDULE", "DEVICES", "LOGS", "MEMBERS", "MEMORY"]
    lines: list[str] = []
    for name in ordered:
        lines.append(f"[{name}]")
        body = sections.get(name, [])
        if body:
            lines.extend(body)
        else:
            lines.append("none")
    return "\n".join(lines)


def _build_operational_context(db: Session, conversation: models.AIConversation) -> dict:
    now = datetime.utcnow()
    _trim_conversation_history(db, conversation)
    memory_ctx = _build_memory_context(db, conversation)

    active_session = (
        db.query(models.GameSession)
        .filter(models.GameSession.is_active.is_(True))
        .order_by(models.GameSession.updated_at.desc(), models.GameSession.id.desc())
        .first()
    )
    mission = None
    if conversation.mission_id is not None:
        mission = db.query(models.Mission).filter(models.Mission.id == conversation.mission_id).first()
    if mission is None and active_session is not None and active_session.mission_id is not None:
        mission = db.query(models.Mission).filter(models.Mission.id == active_session.mission_id).first()

    mission_control_state = mission_control_service.get_state()

    schedule_query = db.query(models.ScheduleItem).filter(models.ScheduleItem.is_complete.is_(False))
    if mission is not None:
        schedule_query = schedule_query.filter(models.ScheduleItem.mission_id == mission.id)
    next_schedule = (
        schedule_query
        .filter(models.ScheduleItem.start_time >= now)
        .order_by(models.ScheduleItem.start_time.asc(), models.ScheduleItem.id.asc())
        .first()
    )

    ongoing_schedule = (
        schedule_query.filter(
            and_(
                models.ScheduleItem.start_time <= now,
                models.ScheduleItem.end_time >= now,
            )
        )
        .order_by(models.ScheduleItem.start_time.desc(), models.ScheduleItem.id.desc())
        .first()
    )

    game_state = str(mission_control_state.get("state", "idle"))
    main_timer_seconds = int(mission_control_state.get("main_timer_seconds", 0) or 0)
    red_score = int(mission_control_state.get("red_team_score", 0) or 0)
    blue_score = int(mission_control_state.get("blue_team_score", 0) or 0)

    online_count = (
        db.query(func.count(models.Device.id))
        .filter(models.Device.status != models.DeviceStatus.offline)
        .scalar()
        or 0
    )
    offline_count = (
        db.query(func.count(models.Device.id))
        .filter(models.Device.status == models.DeviceStatus.offline)
        .scalar()
        or 0
    )
    total_devices = int(online_count + offline_count)

    critical_logs = db.execute(
        text(
            "SELECT created_at, category, message "
            "FROM system_logs "
            "WHERE UPPER(level) = 'CRITICAL' "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT :limit_rows"
        ),
        {"limit_rows": MAX_LOG_LINES},
    ).fetchall()

    facts: list[str] = []
    missing_data: list[str] = []
    warnings: list[str] = []
    suggested_actions: list[str] = []
    used_context: list[str] = ["context:mission_control_state", "context:database"]

    if mission is not None:
        facts.append(f"Mission: {mission.title} ({mission.status.value}).")
        used_context.append(f"mission:{mission.id}")
    else:
        missing_data.append("No mission is linked to this conversation or active session.")
        suggested_actions.append("Link this chat to a mission before issuing operational planning requests.")

    facts.append(f"Game state: {game_state}.")
    facts.append(f"Timer remaining: {main_timer_seconds} seconds.")
    facts.append(f"Team scores: RED {red_score} / BLUE {blue_score}.")

    if active_session is not None:
        facts.append(f"Active session: {active_session.name} (id={active_session.id}).")
        facts.append(
            f"Session scores RED {active_session.red_score} / BLUE {active_session.blue_score}."
        )
        used_context.append(f"game_session:{active_session.id}")
    else:
        missing_data.append("No active game session found.")
        suggested_actions.append("Start or activate the correct game session before live game control.")

    if ongoing_schedule is not None:
        facts.append(
            f"Current schedule item: {ongoing_schedule.title} ({ongoing_schedule.activity_type})."
        )
        used_context.append(f"schedule_current:{ongoing_schedule.id}")
    elif next_schedule is not None:
        facts.append(
            f"Next schedule item: {next_schedule.title} at {next_schedule.start_time.isoformat()}Z."
        )
        suggested_actions.append("Prepare marshals and teams for the next scheduled activity.")
        used_context.append(f"schedule_next:{next_schedule.id}")
    else:
        missing_data.append("No upcoming incomplete schedule items found.")
        suggested_actions.append("Add the next activity block to the schedule to keep flow predictable.")

    facts.append(
        f"Devices summary: {online_count} online, {offline_count} offline, {total_devices} total."
    )
    if total_devices == 0:
        missing_data.append("No devices are registered in the system.")
        suggested_actions.append("Register field devices to enable live operational telemetry.")

    if not critical_logs:
        facts.append("Recent critical logs: none.")
    else:
        facts.append(f"Recent critical logs: {len(critical_logs)} found.")

    if mission_control_state.get("state") == "running" and active_session is None:
        warnings.append("Inconsistency: mission control state is running but no active session exists.")
        suggested_actions.append("Reconcile mission control and session state before issuing new commands.")

    if mission_control_state.get("state") == "running" and mission_control_state.get(
        "main_timer_seconds", 0
    ) > 0 and active_session is None:
        warnings.append("Inconsistency: timer is running while no active session is recorded.")

    if active_session is not None and mission_control_state.get("state") == "idle":
        warnings.append("Inconsistency: active session exists while mission control reports idle.")

    if game_state in ("running", "paused") and next_schedule is None and ongoing_schedule is None:
        warnings.append("Inconsistency: game is active but schedule has no current or next activity.")

    sections: dict[str, list[str]] = {
        "CURRENT STATE": [
            f"game_state={game_state}",
            f"timer_remaining_seconds={main_timer_seconds}",
            f"team_scores=red:{red_score},blue:{blue_score}",
        ],
        "MISSION": [
            (
                f"id={mission.id}; title={_truncate_text(mission.title, 80)}; "
                f"status={mission.status.value}"
            )
            if mission is not None
            else "none"
        ],
        "SCHEDULE": [
            f"current={_format_schedule_item(ongoing_schedule)}",
            f"next={_format_schedule_item(next_schedule)}",
        ],
        "DEVICES": [
            f"online_count={online_count}",
            f"offline_count={offline_count}",
            f"total={total_devices}",
        ],
        "LOGS": [
            (
                f"{str(row[0])}Z | {str(row[1]).upper()} | "
                f"{_truncate_text(str(row[2]), 120)}"
            )
            for row in critical_logs
        ]
        or ["none"],
        "MEMBERS": _build_members_context_block(db),
        "MEMORY": memory_ctx["lines"] or [f"none (retention={MEMORY_RETENTION_DAYS} days)"],
    }

    context_block = _build_context_block(sections)
    if len(context_block) > MAX_CONTEXT_CHARS and critical_logs:
        trimmed_lines = sections["LOGS"]
        while len(context_block) > MAX_CONTEXT_CHARS and len(trimmed_lines) > 1:
            trimmed_lines.pop()
            sections["LOGS"] = trimmed_lines
            context_block = _build_context_block(sections)
    if len(context_block) > MAX_CONTEXT_CHARS:
        sections["LOGS"] = ["truncated"]
        context_block = _build_context_block(sections)
    if len(context_block) > MAX_CONTEXT_CHARS:
        context_block = _truncate_text(context_block, MAX_CONTEXT_CHARS)

    used_context.append(f"context_block_chars:{len(context_block)}")
    used_context.append(f"memory_messages:{memory_ctx['count']}")
    used_context.append(f"memory_retention_days:{MEMORY_RETENTION_DAYS}")

    diagnostics = {
        "device": analyze_device_status(db, ""),
        "logs": analyze_logs(db),
        "schedule": analyze_schedule(db, mission.id if mission is not None else None),
        "mission_state": analyze_mission_state(mission_control_state, active_session),
    }

    warnings = list(
        dict.fromkeys(
            [
                *warnings,
                *diagnostics["device"]["warnings"],
                *diagnostics["logs"]["warnings"],
                *diagnostics["schedule"]["warnings"],
                *diagnostics["mission_state"]["warnings"],
            ]
        )
    )

    suggested_actions = list(
        dict.fromkeys(
            [
                *suggested_actions,
                *diagnostics["device"]["suggestions"],
                *diagnostics["logs"]["suggestions"],
                *diagnostics["schedule"]["suggestions"],
                *diagnostics["mission_state"]["suggestions"],
            ]
        )
    )

    return {
        "facts": facts,
        "missing_data": missing_data,
        "warnings": warnings,
        "suggested_actions": suggested_actions,
        "diagnostics": diagnostics,
        "context_block": context_block,
        "used_context": list(dict.fromkeys(used_context)),
    }


def _build_diagnostic_answer(prompt: str, ctx: dict, db: Session) -> str | None:
    text = prompt.lower()

    if "behind schedule" in text or "schedule delay" in text or "schedule" in text and "behind" in text:
        schedule_diag = analyze_schedule(db)
        lines = ["Diagnostic summary:"]
        lines.extend([f"- {fact}" for fact in schedule_diag["facts"][:3]])
        if schedule_diag["warnings"]:
            lines.append("Warnings:")
            lines.extend([f"- {w}" for w in schedule_diag["warnings"][:3]])
        lines.append(
            "- Conclusion: "
            + ("Yes, schedule appears behind." if schedule_diag["behind_schedule"] else "No clear schedule delay detected right now.")
        )
        return "\n".join(lines)

    if "what's wrong with the system" in text or "what is wrong with the system" in text or "system issue" in text:
        log_diag = analyze_logs(db)
        mission_diag = ctx.get("diagnostics", {}).get("mission_state", {})
        lines = ["Diagnostic summary:"]
        lines.extend([f"- {fact}" for fact in log_diag["facts"][:2]])
        for fact in mission_diag.get("facts", [])[:2]:
            lines.append(f"- {fact}")
        all_warnings = list(dict.fromkeys([*log_diag["warnings"], *mission_diag.get("warnings", [])]))
        if all_warnings:
            lines.append("Warnings:")
            lines.extend([f"- {w}" for w in all_warnings[:4]])
        else:
            lines.append("- No critical system fault detected in current telemetry.")
        return "\n".join(lines)

    if "not responding" in text or "device issue" in text or "prop issue" in text:
        device_diag = analyze_device_status(db, prompt)
        lines = ["Diagnostic summary:"]
        lines.extend([f"- {fact}" for fact in device_diag["facts"][:3]])
        if device_diag["issues"]:
            lines.append("Likely causes:")
            lines.extend([f"- {issue}" for issue in device_diag["issues"][:4]])
        if device_diag["warnings"]:
            lines.append("Warnings:")
            lines.extend([f"- {w}" for w in device_diag["warnings"][:3]])
        return "\n".join(lines)

    return None


def _compose_structured_answer(base_answer: str, ctx: dict) -> str:
    facts = ctx["facts"]
    missing_data = ctx["missing_data"]
    suggestions = ctx["suggested_actions"]

    lines: list[str] = []
    lines.append("Context used:")
    lines.append("- CURRENT STATE, MISSION, SCHEDULE, DEVICES, LOGS")

    lines.append("Facts:")
    if facts:
        lines.extend([f"- {line}" for line in facts[:4]])
    else:
        lines.append("- No confirmed operational facts available.")

    lines.append("Suggestions:")
    if suggestions:
        lines.extend([f"- {line}" for line in list(dict.fromkeys(suggestions))[:4]])
    else:
        lines.append("- Use the AI response as advisory guidance only.")

    if missing_data:
        lines.append("Missing data:")
        lines.extend([f"- {line}" for line in list(dict.fromkeys(missing_data))[:3]])

    lines.append("AI guidance:")
    lines.append(f"- {base_answer}")

    return "\n".join(lines)


def create_conversation(
    db: Session,
    payload: schemas.AIConversationCreateRequest,
) -> models.AIConversation:
    item = models.AIConversation(
        title=payload.title,
        mission_id=payload.mission_id,
        user_id=payload.user_id,
        status="active",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_conversations(db: Session) -> list[models.AIConversation]:
    return db.query(models.AIConversation).order_by(models.AIConversation.updated_at.desc()).all()


def to_conversation_read(item: models.AIConversation) -> schemas.AIConversationRead:
    return schemas.AIConversationRead(
        id=item.id,
        user_id=item.user_id,
        mission_id=item.mission_id,
        title=item.title,
        status=item.status,
        memory_summary=item.memory_summary or "",
        learned_trends=_parse_json_list(item.learned_trends),
        correction_memory=_from_json_dict(item.correction_memory),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def get_conversation(db: Session, conversation_id: int) -> models.AIConversation:
    item = db.query(models.AIConversation).filter(models.AIConversation.id == conversation_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


def _to_message_read(item: models.AIMessage) -> schemas.AIMessageRead:
    return schemas.AIMessageRead(
        id=item.id,
        conversation_id=item.conversation_id,
        role=item.role.value,
        content=item.content,
        confidence=item.confidence,
        used_context=_from_json_list(item.used_context),
        suggested_actions=_from_json_list(item.suggested_actions),
        blocked_actions=_from_json_list(item.blocked_actions),
        warnings=_from_json_list(item.warnings),
        requires_admin_confirmation=item.requires_admin_confirmation,
        action_request_id=item.action_request_id,
        model=item.model,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def list_messages(db: Session, conversation_id: int) -> list[schemas.AIMessageRead]:
    _ = get_conversation(db, conversation_id)
    rows = (
        db.query(models.AIMessage)
        .filter(models.AIMessage.conversation_id == conversation_id)
        .order_by(models.AIMessage.created_at.asc(), models.AIMessage.id.asc())
        .all()
    )
    return [_to_message_read(row) for row in rows]


def _create_action_request(
    db: Session,
    conversation_id: int,
    user_message_id: int,
    user_id: int | None,
    blocked_actions: list[str],
    prompt: str,
) -> models.AIActionRequest:
    action_label = blocked_actions[0] if blocked_actions else "manual_review_required"
    item = models.AIActionRequest(
        conversation_id=conversation_id,
        message_id=user_message_id,
        requested_action=action_label,
        action_payload=json.dumps({"prompt": prompt}, ensure_ascii=True),
        status=models.AIActionStatus.pending,
        requires_admin_confirmation=True,
        created_by_user_id=user_id,
        confirmation_note="",
    )
    db.add(item)
    db.flush()
    return item


def _add_audit_log(
    db: Session,
    *,
    conversation_id: int,
    message_id: int,
    action_request_id: int | None,
    decision: models.AIAuditDecision,
    risk_level: models.AIRiskLevel,
    prompt_excerpt: str,
    response_excerpt: str,
    used_context: list[str],
    blocked_actions: list[str],
) -> None:
    row = models.AIAuditLog(
        conversation_id=conversation_id,
        message_id=message_id,
        action_request_id=action_request_id,
        policy_name="advisory_only_v1",
        decision=decision,
        risk_level=risk_level,
        prompt_excerpt=prompt_excerpt,
        response_excerpt=response_excerpt,
        used_context=_to_json_list(used_context),
        blocked_actions=_to_json_list(blocked_actions),
    )
    db.add(row)


def _enforce_final_action_safety(
    suggested_actions: list[str],
    blocked_actions: list[str],
    requires_admin_confirmation: bool,
) -> tuple[list[str], list[str], bool, list[str]]:
    filtered_suggestions: list[str] = []
    final_blocked_actions = list(blocked_actions)
    enforcement_warnings: list[str] = []

    for action in suggested_actions:
        validation = ai_policy.validate_ai_action(
            action,
            requires_admin_confirmation=requires_admin_confirmation,
        )
        if validation.allowed:
            filtered_suggestions.append(action)
            continue

        final_blocked_actions.append(action)
        if validation.reason:
            enforcement_warnings.append(f"Blocked action suggestion '{action}': {validation.reason}")

    filtered_suggestions = list(dict.fromkeys(filtered_suggestions))
    final_blocked_actions = list(dict.fromkeys(final_blocked_actions))
    enforcement_warnings = list(dict.fromkeys(enforcement_warnings))
    final_requires_admin = requires_admin_confirmation or len(final_blocked_actions) > 0
    return filtered_suggestions, final_blocked_actions, final_requires_admin, enforcement_warnings


def _build_custom_knowledge_block(db: Session, prompt: str) -> dict[str, str | list[str]]:
    """Build custom knowledge block from CustomKnowledgeEntry, CustomTeam, CustomGameMode if relevant."""
    result = {
        "block_text": "",
        "used_context": [],
        "has_custom_data": False,
    }

    custom_keywords = {
        "teams": r"\b(team|group|red|blue|neutral|callsign|side)\b",
        "rules": r"\b(rule|regulation|policy|scoring|objective|respawn|mechanic)\b",
        "game_modes": r"\b(game\s+mode|mode|challenge|variant|competition|competitive)\b",
        "schedule": r"\b(schedule|activity|event|timing|start|end|duration|timetable)\b",
        "prop_issues": r"\b(prop|device|sensor|radio|lora|arm|disarm|trigger|alert|problem|issue|malfunction|fix|repair)\b",
        "event_management": r"\b(event|manager|coordinate|marshal|briefing|debrief|checkpoint|station)\b",
        "briefings": r"\b(brief|briefing|prepare|preparation|overview|introduction|explain|instruction)\b",
        "announcements": r"\b(announce|announcement|alert|notify|notification|update|bulletin|news)\b",
    }

    prompt_lower = prompt.lower()
    detected_topics: set[str] = set()
    for topic, pattern in custom_keywords.items():
        if re.search(pattern, prompt_lower):
            detected_topics.add(topic)

    context_snapshot = collect_context(db, prompt=prompt)

    lines: list[str] = []

    if "teams" in detected_topics and context_snapshot.active_teams:
        lines.append("[ACTIVE TEAMS (Custom Data)]")
        for team in context_snapshot.active_teams:
            lines.append(f"- {team['name']} ({team['callsign']}, side: {team['side']})")
        result["used_context"].append("custom:teams")
        result["has_custom_data"] = True

    if ("rules" in detected_topics or "game_modes" in detected_topics) and context_snapshot.active_game_modes:
        lines.append("[ACTIVE GAME MODES (Custom Rules)]")
        for mode in context_snapshot.active_game_modes:
            lines.append(f"- {mode['name']} ({mode['category']})")
            if mode["description"]:
                lines.append(f"  {mode['description']}")
        result["used_context"].append("custom:game_modes")
        result["has_custom_data"] = True

    if context_snapshot.relevant_knowledge:
        lines.append("[RELEVANT KNOWLEDGE BASE (Custom Entries)]")
        for entry in context_snapshot.relevant_knowledge:
            lines.append(f"- [{entry['category']}] {entry['title']} (relevance: {entry['relevance_score']})")
            if entry["content"]:
                lines.append(f"  {entry['content']}")
        result["used_context"].append("custom:knowledge_base")
        result["has_custom_data"] = True
    else:
        fallback_entries = (
            db.query(models.CustomKnowledgeEntry)
            .filter(models.CustomKnowledgeEntry.active.is_(True))
            .order_by(models.CustomKnowledgeEntry.updated_at.desc(), models.CustomKnowledgeEntry.id.desc())
            .limit(3)
            .all()
        )
        if fallback_entries:
            lines.append("[CUSTOM KNOWLEDGE BASE (Active Entries)]")
            for entry in fallback_entries:
                lines.append(f"- [{entry.category}] {entry.title}")
                if entry.content:
                    lines.append(f"  {entry.content[:200]}")
            result["used_context"].append("custom:knowledge_base_active_fallback")
            result["has_custom_data"] = True
        elif detected_topics:
            lines.append("[CUSTOM KNOWLEDGE]")
            lines.append("- No relevant custom knowledge entries found for this query.")
            result["used_context"].append("custom:knowledge_base_empty")

    result["block_text"] = "\n".join(lines)
    return result


def send_message(
    db: Session,
    conversation_id: int,
    payload: schemas.AIMessageCreateRequest,
) -> schemas.AIChatReplyResponse:
    conversation = get_conversation(db, conversation_id)
    _trim_conversation_history(db, conversation)

    user_message = models.AIMessage(
        conversation_id=conversation_id,
        role=models.MessageRole.user,
        content=payload.content,
        confidence=1.0,
        used_context="[]",
        suggested_actions="[]",
        blocked_actions="[]",
        blocked_action=False,
        requires_admin_confirmation=False,
        model="user",
    )
    db.add(user_message)
    db.flush()

    raw_prompt = (payload.content or "").strip()
    normalized_prompt = _normalize_user_language(raw_prompt)

    # Learn and apply explicit user corrections before building context so the
    # next AI reply can immediately use updated member/team facts.
    _update_member_from_message(db, raw_prompt)
    _update_correction_memory(conversation, raw_prompt)

    policy = evaluate_ai_prompt(raw_prompt)
    context_summary = _build_operational_context(db, conversation)
    custom_knowledge_block = _build_custom_knowledge_block(db, normalized_prompt)

    injected_prompt_parts = [
        context_summary['context_block'],
        custom_knowledge_block['block_text'],
        f"[USER REQUEST]\n{raw_prompt}",
    ]
    if normalized_prompt != raw_prompt:
        injected_prompt_parts.append(f"[INTERPRETED USER REQUEST]\n{normalized_prompt}")
    injected_prompt = "\n\n".join([part for part in injected_prompt_parts if part])

    # Collect conversation history for the advisor (last 20 turns).
    recent_rows = (
        db.query(models.AIMessage)
        .filter(models.AIMessage.conversation_id == conversation_id)
        .order_by(models.AIMessage.created_at.desc(), models.AIMessage.id.desc())
        .limit(20)
        .all()
    )
    conv_history = [
        {"role": row.role.value, "content": row.content}
        for row in reversed(recent_rows)
        if row.id != user_message.id
    ]

    advisor_response = ask_ai(
        normalized_prompt,
        injected_context=injected_prompt,
        conversation_history=conv_history,
    )

    used_context = list(
        dict.fromkeys(
            [
                *advisor_response.used_context,
                *policy.used_context,
                *context_summary["used_context"],
                *custom_knowledge_block["used_context"],
            ]
        )
    )
    suggested_actions = list(
        dict.fromkeys(
            [
                *advisor_response.suggested_actions,
                *policy.suggested_actions,
                *context_summary["suggested_actions"],
            ]
        )
    )
    blocked_actions = list(
        dict.fromkeys([*advisor_response.blocked_actions, *policy.blocked_actions])
    )
    warnings = list(dict.fromkeys([*advisor_response.warnings, *context_summary["warnings"]]))

    requires_admin_confirmation = (
        advisor_response.requires_admin_confirmation
        or policy.requires_admin_confirmation
        or len(blocked_actions) > 0
    )
    suggested_actions, blocked_actions, requires_admin_confirmation, enforcement_warnings = _enforce_final_action_safety(
        suggested_actions,
        blocked_actions,
        requires_admin_confirmation,
    )
    if enforcement_warnings:
        used_context = list(dict.fromkeys([*used_context, "policy:final_action_enforcement"]))
        warnings = list(dict.fromkeys([*warnings, *enforcement_warnings]))

    confidence = min(advisor_response.confidence, policy.confidence)
    if context_summary["missing_data"]:
        confidence = max(0.2, min(confidence, 0.62))

    # The advisor handles all conversational logic including live context, confirm flow
    # and diagnostic queries. Use its answer directly.
    answer = advisor_response.answer

    # For confirmation-pending actions, log an action request for audit purposes
    # but do NOT override the AI's answer — it already asked the user to confirm.
    action_request: models.AIActionRequest | None = None
    if requires_admin_confirmation and blocked_actions:
        action_request = _create_action_request(
            db,
            conversation_id=conversation_id,
            user_message_id=user_message.id,
            user_id=payload.user_id,
            blocked_actions=blocked_actions,
            prompt=raw_prompt,
        )

    assistant_message = models.AIMessage(
        conversation_id=conversation_id,
        role=models.MessageRole.assistant,
        content=answer,
        confidence=confidence,
        used_context=_to_json_list(used_context),
        suggested_actions=_to_json_list(suggested_actions),
        blocked_actions=_to_json_list(blocked_actions),
        warnings=_to_json_list(warnings),
        blocked_action=requires_admin_confirmation,
        requires_admin_confirmation=requires_admin_confirmation,
        model=advisor_response.model,
        action_request_id=action_request.id if action_request else None,
    )
    db.add(assistant_message)
    db.flush()

    retained_messages = (
        db.query(models.AIMessage)
        .filter(
            models.AIMessage.conversation_id == conversation_id,
            models.AIMessage.created_at >= datetime.utcnow() - timedelta(days=MEMORY_RETENTION_DAYS),
        )
        .order_by(models.AIMessage.created_at.desc(), models.AIMessage.id.desc())
        .limit(150)
        .all()
    )
    _update_conversation_learning(conversation, retained_messages)

    conversation.updated_at = datetime.utcnow()

    audit_decision = (
        models.AIAuditDecision.requires_confirmation
        if requires_admin_confirmation
        else models.AIAuditDecision.allow
    )
    risk_level = models.AIRiskLevel.high if requires_admin_confirmation else models.AIRiskLevel.low
    _add_audit_log(
        db,
        conversation_id=conversation_id,
        message_id=assistant_message.id,
        action_request_id=action_request.id if action_request else None,
        decision=audit_decision,
        risk_level=risk_level,
        prompt_excerpt=raw_prompt[:300],
        response_excerpt=answer[:300],
        used_context=used_context,
        blocked_actions=blocked_actions,
    )

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    if action_request:
        db.refresh(action_request)

    return schemas.AIChatReplyResponse(
        answer=assistant_message.content,
        confidence=assistant_message.confidence,
        used_context=_from_json_list(assistant_message.used_context),
        suggested_actions=_from_json_list(assistant_message.suggested_actions),
        blocked_actions=_from_json_list(assistant_message.blocked_actions),
        warnings=_from_json_list(assistant_message.warnings),
        requires_admin_confirmation=assistant_message.requires_admin_confirmation,
        conversation_id=conversation_id,
        user_message=_to_message_read(user_message),
        assistant_message=_to_message_read(assistant_message),
        action_request=(
            schemas.AIActionRequestRead.model_validate(action_request)
            if action_request
            else None
        ),
    )


def list_action_requests(db: Session) -> list[models.AIActionRequest]:
    return (
        db.query(models.AIActionRequest)
        .order_by(models.AIActionRequest.created_at.desc(), models.AIActionRequest.id.desc())
        .all()
    )


def clear_conversation(
    db: Session,
    conversation_id: int,
) -> schemas.AIConversationClearResponse:
    conversation = get_conversation(db, conversation_id)

    deleted_audit_logs = (
        db.query(models.AIAuditLog)
        .filter(models.AIAuditLog.conversation_id == conversation_id)
        .delete(synchronize_session=False)
    )
    deleted_action_requests = (
        db.query(models.AIActionRequest)
        .filter(models.AIActionRequest.conversation_id == conversation_id)
        .delete(synchronize_session=False)
    )
    deleted_messages = (
        db.query(models.AIMessage)
        .filter(models.AIMessage.conversation_id == conversation_id)
        .delete(synchronize_session=False)
    )

    conversation.memory_summary = ""
    conversation.learned_trends = "[]"
    conversation.correction_memory = "{}"
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return schemas.AIConversationClearResponse(
        status="cleared",
        conversation_id=conversation_id,
        deleted_messages=int(deleted_messages),
        deleted_action_requests=int(deleted_action_requests),
        deleted_audit_logs=int(deleted_audit_logs),
    )
