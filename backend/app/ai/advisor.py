"""AI advisory module – Christy, the AOJ field advisor.

Uses Ollama (local offline LLM) when available; falls back to built-in
conversational rules engine so the system always works without internet.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.schemas.ai import AIAskResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE = "http://localhost:11434"
# Preferred models in order — first one found wins.
OLLAMA_MODEL_PREFERENCE = [
    "llama3.2:3b",
    "llama3.2",
    "llama3:8b",
    "llama3",
    "mistral",
    "phi3:mini",
    "gemma2:2b",
    "gemma:2b",
]

CHRISTY_SYSTEM_PROMPT = """You are Christy, the intelligent field operations advisor for AOJ Command OS — an airsoft command platform.

Your personality: calm, professional, friendly, and knowledgeable. You speak in a natural, conversational tone. You DO NOT use bullet-point walls unless specifically asked for a list. You write in short, clear paragraphs.

Your capabilities:
- Give live game status from the context block provided (scores, timer, devices, schedule)
- Suggest appropriate game modes based on player count, field size, session length, and team handicap
- Draft complete rule sets for any game mode
- Write marshal briefings and team announcements personalised to specific players when their profile is known
- Help with schedule management and delay recovery
- Diagnose device/prop issues
- For operational actions (start/stop game, arm/reset devices), always ask for confirmation first
- Remember and use player/member profiles (name, gender, team, skill level, strengths, weaknesses)
- Use member data to suggest balanced teams, personalised tips, and role assignments
- Learn from corrections: if someone says "actually Alex is on Blue Team now", update your understanding

CRITICAL rules:
- NEVER execute an operational action without explicit user confirmation — ask "Can you confirm?" first
- When confirming an action, embed the tag [CONFIRM_ACTION:action_key] at the end of your message (hidden from display)
- If the user says yes/confirm/proceed, provide step-by-step guidance
- Keep answers under 200 words unless building a detailed rule set
- Do NOT use excessive markdown symbols in responses — use plain, natural language
- Do NOT start every message with "Certainly!" or similar filler phrases

Context block format: The operational context is provided as a structured block with sections [CURRENT STATE], [MISSION], [SCHEDULE], [DEVICES], [LOGS], [MEMBERS], [MEMORY]. Use this to give accurate, live answers.

The [MEMBERS] section lists known player profiles in the format: Name; gender; team=X; skill=Y; strengths=...; weaknesses=...
Use this to personalise advice, suggest team balancing, and address players by name when relevant.
Your name is Christy. You work for the AOJ field team."""

MOCK_MODEL_NAME = "christy-rules-engine-v2"

SAFETY_NOTICE = (
    "Advisory mode active. Christy will ask for your confirmation before any operational action."
)

# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

_ollama_available: bool | None = None  # None = not yet checked
_ollama_model: str | None = None


def _check_ollama() -> tuple[bool, str | None]:
    """Probe Ollama and return (available, best_model_name)."""
    global _ollama_available, _ollama_model
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=2.0)
        if resp.status_code != 200:
            _ollama_available = False
            return False, None
        data = resp.json()
        installed = [m["name"] for m in data.get("models", [])]
        # Find first preferred model that is installed
        for pref in OLLAMA_MODEL_PREFERENCE:
            for inst in installed:
                if inst.startswith(pref.split(":")[0]):
                    _ollama_available = True
                    _ollama_model = inst
                    return True, inst
        # No preferred model — use whatever is installed
        if installed:
            _ollama_available = True
            _ollama_model = installed[0]
            return True, installed[0]
        _ollama_available = False
        return False, None
    except Exception:
        _ollama_available = False
        return False, None


def _ollama_chat(
    prompt: str,
    context: str | None,
    history: list[dict[str, Any]],
    model: str,
) -> str | None:
    """
    Call Ollama /api/chat and return the assistant text, or None on failure.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": CHRISTY_SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "system",
            "content": f"[OPERATIONAL CONTEXT]\n{context}",
        })

    for entry in history[-20:]:  # last 20 turns for better continuity
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": prompt})

    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=60.0,
        )
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
        logger.warning("Ollama returned status %d", resp.status_code)
        return None
    except Exception as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Confirmation / operational patterns
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

_CONFIRM_PATTERNS = re.compile(
    r"\b(yes|yeah|confirm|confirmed|proceed|go ahead|do it|approved|affirmative|ok|okay)\b",
    re.IGNORECASE,
)

_OPERATIONAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(start|launch|begin)\b.{0,30}\b(game|mission|session|round)\b", re.I), "start_game"),
    (re.compile(r"\b(end|stop|finish|terminate|abort)\b.{0,30}\b(game|mission|session|round)\b", re.I), "end_game"),
    (re.compile(r"\b(pause|resume)\b.{0,30}\b(game|mission|session)\b", re.I), "pause_resume_game"),
    (re.compile(r"\b(arm|disarm)\b", re.I), "arm_disarm_device"),
    (re.compile(r"\b(reset)\b.{0,20}\b(device|prop|system|all)\b", re.I), "reset_device"),
    (re.compile(r"\b(trigger|activate|fire)\b.{0,20}\b(alarm|prop|device)\b", re.I), "trigger_device"),
    (re.compile(r"\b(shutdown|reboot|restart)\b.{0,20}\b(system|server|pi|device)\b", re.I), "system_power"),
    (re.compile(r"\b(adjust|set|change|add|deduct)\b.{0,20}\b(score|points?)\b", re.I), "adjust_score"),
]

_HUMAN_LABELS: dict[str, str] = {
    "start_game": "start the game/mission",
    "end_game": "end the game/mission",
    "pause_resume_game": "pause or resume the game",
    "arm_disarm_device": "arm or disarm a device",
    "reset_device": "reset a device/system",
    "trigger_device": "trigger a prop/alarm",
    "system_power": "shut down or reboot the system",
    "adjust_score": "adjust team scores",
}

# ---------------------------------------------------------------------------
# Number extraction helpers
# ---------------------------------------------------------------------------

_NUM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d+)\s*(?:players?|people|participants?|persons?)", re.I), "players"),
    (re.compile(r"(\d+)\s*(?:per\s*team|a\s*side|each\s*team)", re.I), "per_team"),
    (re.compile(r"(?:field|area|site)\s*(?:is\s*)?(\d+)\s*(?:m|meters?|metres?|acres?|hectares?|sqm|sq\s*m)", re.I), "field_m"),
    (re.compile(r"(\d+)\s*(?:m|meters?|metres?|acres?|hectares?)\s*(?:field|area|site|large|wide|big|small)", re.I), "field_m"),
    (re.compile(r"(?:handicap|advantage|bias)\s*(?:of\s*)?(\d+)\s*(?:%|percent|points?)", re.I), "handicap_pct"),
    (re.compile(r"(\d+)\s*(?:min(?:utes?)?|hrs?|hours?)\s*(?:time|limit|available|to\s*play)?", re.I), "minutes"),
]


def _extract_numbers(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for pattern, key in _NUM_PATTERNS:
        m = pattern.search(text)
        if m:
            result[key] = int(m.group(1))
    return result


# ---------------------------------------------------------------------------
# Context block parser
# ---------------------------------------------------------------------------

def _parse_context_block(context: str | None) -> dict[str, Any]:
    """Parse the structured context block into a usable dict."""
    out: dict[str, Any] = {
        "game_state": "idle",
        "timer_seconds": 0,
        "red_score": 0,
        "blue_score": 0,
        "mission_title": None,
        "mission_status": None,
        "schedule_current": None,
        "schedule_next": None,
        "devices_online": 0,
        "devices_offline": 0,
        "devices_total": 0,
        "critical_logs": [],
        "member_lines": [],
        "memory_lines": [],
        "available_game_modes": [],
        "active_teams": [],
        "custom_knowledge": [],
    }
    if not context:
        return out

    current_section = ""
    for raw_line in context.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Section header
        section_match = re.match(r"^\[([A-Z _]+)\]$", line)
        if section_match:
            current_section = section_match.group(1)
            continue

        # CURRENT STATE
        if current_section == "CURRENT STATE":
            m = re.match(r"game_state=(\S+)", line)
            if m:
                out["game_state"] = m.group(1)
            m = re.match(r"timer_remaining_seconds=(\d+)", line)
            if m:
                out["timer_seconds"] = int(m.group(1))
            m = re.match(r"team_scores=red:(\d+),blue:(\d+)", line)
            if m:
                out["red_score"] = int(m.group(1))
                out["blue_score"] = int(m.group(2))

        # MISSION
        elif current_section == "MISSION":
            m = re.search(r"title=([^;]+)", line)
            if m:
                out["mission_title"] = m.group(1).strip()
            m = re.search(r"status=(\S+)", line)
            if m:
                out["mission_status"] = m.group(1).strip()

        # SCHEDULE
        elif current_section == "SCHEDULE":
            if line.startswith("current=") and "none" not in line:
                out["schedule_current"] = line[len("current="):].strip()
            if line.startswith("next=") and "none" not in line:
                out["schedule_next"] = line[len("next="):].strip()

        # DEVICES
        elif current_section == "DEVICES":
            m = re.match(r"online_count=(\d+)", line)
            if m:
                out["devices_online"] = int(m.group(1))
            m = re.match(r"offline_count=(\d+)", line)
            if m:
                out["devices_offline"] = int(m.group(1))
            m = re.match(r"total=(\d+)", line)
            if m:
                out["devices_total"] = int(m.group(1))

        # LOGS
        elif current_section == "LOGS":
            if line != "none":
                out["critical_logs"].append(line)

        # MEMBERS
        elif current_section == "MEMBERS":
            if line != "none":
                out["member_lines"].append(line)

        # MEMORY
        elif current_section == "MEMORY":
            if line not in ("none",) and not line.startswith("none (retention"):
                out["memory_lines"].append(line)

        # ACTIVE GAME MODES
        elif "ACTIVE GAME MODES" in current_section or "GAME MODE" in current_section:
            if line.startswith("-"):
                name = line.lstrip("- ").split("(")[0].strip()
                if name:
                    out["available_game_modes"].append(name)

        # ACTIVE TEAMS
        elif "ACTIVE TEAMS" in current_section or "TEAM" in current_section:
            if line.startswith("-"):
                out["active_teams"].append(line.lstrip("- ").strip())

        # CUSTOM KNOWLEDGE
        elif "KNOWLEDGE" in current_section or "RELEVANT KNOWLEDGE" in current_section:
            if line.startswith("-"):
                out["custom_knowledge"].append(line.lstrip("- ").strip())

    # Also scan for game modes from inline lines anywhere in context
    for line in context.splitlines():
        if re.search(r"game mode.*:", line, re.I) and ":" in line:
            mode = line.split(":", 1)[-1].strip().strip("-").strip()
            if mode and len(mode) < 60 and mode not in out["available_game_modes"]:
                out["available_game_modes"].append(mode)

    return out


def _fmt_timer(seconds: int) -> str:
    """Format seconds as MM:SS or 'not running'."""
    if seconds <= 0:
        return "not running"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def _detect_operational_action(text: str) -> tuple[str | None, str | None]:
    for pattern, key in _OPERATIONAL_PATTERNS:
        if pattern.search(text):
            return key, _HUMAN_LABELS.get(key, key)
    return None, None


def _check_history_for_pending_confirmation(history: list[dict[str, Any]]) -> str | None:
    for entry in reversed(history):
        if entry.get("role") == "assistant":
            content = entry.get("content", "")
            m = re.search(r"\[CONFIRM_ACTION:([^\]]+)\]", content)
            if m:
                return m.group(1)
            break
    return None


def _extract_nums_from_history(history: list[dict[str, Any]]) -> dict[str, int]:
    """Scan conversation history for previously mentioned numbers."""
    nums: dict[str, int] = {}
    for entry in history:
        if entry.get("role") == "user":
            found = _extract_numbers(entry.get("content", "").lower())
            for k, v in found.items():
                if k not in nums:
                    nums[k] = v
    return nums


def _last_message_by_role(history: list[dict[str, Any]], role: str) -> str:
    for entry in reversed(history):
        if entry.get("role") == role:
            return str(entry.get("content", "") or "")
    return ""


def _is_followup_message(text: str) -> bool:
    short = len(text.split()) <= 10
    followup_cues = re.search(
        r"\b(yes|yeah|yep|ok|okay|sure|that one|go with|do that|sounds good|more|details?|expand|continue|next|then|why|how)\b",
        text,
        re.I,
    )
    return bool(short and followup_cues)


def _extract_numbered_modes(text: str) -> list[str]:
    modes = re.findall(r"\d+\.\s+\*\*([^*]+)\*\*", text)
    return [m.strip() for m in modes if m.strip()]


def _plain_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return [re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", ln) for ln in lines]


def _summarize_previous_answer(last_assistant: str) -> str:
    lines = _plain_lines(last_assistant)
    if not lines:
        return "Here is the short version: continue with the selected mode and I will tailor timers, scoring, and balance for your field."
    picks = [ln for ln in lines if re.match(r"^\d+\.\s+", ln)]
    if picks:
        return "Short version: " + "; ".join(picks[:3]) + ". Tell me one and I will build full rules."
    return "Short version: " + " ".join(lines[:2])[:240]


def _compare_recommended_modes(last_assistant: str) -> str | None:
    modes = _extract_numbered_modes(last_assistant)
    if not modes:
        return None
    top = modes[:3]
    guidance: list[str] = []
    for mode in top:
        m = mode.lower()
        if "domination" in m:
            guidance.append("Domination: best for tactical control play and balanced team pressure.")
        elif "capture" in m or "flag" in m or "ctf" in m:
            guidance.append("Capture The Flag: best for movement, flanking, and objective-focused rounds.")
        elif "king" in m or "hill" in m or "koth" in m:
            guidance.append("King of the Hill: best for intense central fights and fast momentum swings.")
        elif "skirmish" in m:
            guidance.append("Skirmish: best for simple setup and quick back-to-back rounds.")
        else:
            guidance.append(f"{mode}: adaptable mode; I can tune it to your field and player mix.")
    return "Comparison from my previous suggestion:\n\n- " + "\n- ".join(guidance)


def _followup_intent(text: str) -> str | None:
    if re.search(r"\b(compare|difference|which is better|pros and cons|vs\.?|versus)\b", text, re.I):
        return "compare"
    if re.search(r"\b(why|reason|because|explain)\b", text, re.I):
        return "explain"
    if re.search(r"\b(short|brief|summary|quick version|tldr)\b", text, re.I):
        return "summarize"
    return None


def _extract_mode_from_text(text: str, available_modes: list[str]) -> str | None:
    """Find a game mode mention in free text, including common shorthand."""
    lower = text.lower()

    alias_map = {
        "ctf": "capture the flag",
        "capture the flag": "capture the flag",
        "capture flag": "capture the flag",
        "dom": "domination",
        "domination": "domination",
        "koth": "king of the hill",
        "king of the hill": "king of the hill",
        "skirmish": "skirmish",
        "hostage": "hostage rescue",
        "hostage rescue": "hostage rescue",
        "assault": "assault",
        "siege": "siege",
    }

    for alias, canonical in alias_map.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return canonical

    for mode in available_modes:
        if mode and mode.lower() in lower:
            return mode

    return None


def _select_mode_from_followup(
    user_text: str,
    last_assistant: str,
    available_modes: list[str],
) -> str | None:
    lower = user_text.lower()
    options = _extract_numbered_modes(last_assistant)

    # Direct numeric references ("1", "option 2", "second")
    if options:
        idx_match = re.search(r"\b(?:option\s*)?(1|2|3)\b", lower)
        if idx_match:
            idx = int(idx_match.group(1)) - 1
            if 0 <= idx < len(options):
                return options[idx]
        if "first" in lower and len(options) >= 1:
            return options[0]
        if "second" in lower and len(options) >= 2:
            return options[1]
        if "third" in lower and len(options) >= 3:
            return options[2]

    # Explicit mode name/alias in user text
    direct = _extract_mode_from_text(user_text, available_modes)
    if direct:
        return direct

    # If user says "that one" and we have options, default to first recommendation
    if options and re.search(r"\b(that one|go with it|sounds good|let's do it|do it)\b", lower):
        return options[0]

    return None


# ---------------------------------------------------------------------------
# Action guidance
# ---------------------------------------------------------------------------

def _action_guidance(action_key: str) -> str:
    guides: dict[str, str] = {
        "start_game": (
            "1. Confirm all players are staged and ready\n"
            "2. Check all props report online in Prop Network\n"
            "3. Verify marshals are in position\n"
            "4. Click **Start Game** in Mission Control → Game Controls\n"
            "5. The countdown begins automatically"
        ),
        "end_game": (
            "1. Announce end of game via radio/PA\n"
            "2. Click **End Game** in Mission Control → Game Controls\n"
            "3. Record final scores in Results Board\n"
            "4. Disarm all active props via Prop Network\n"
            "5. Debrief both teams before clearing the field"
        ),
        "pause_resume_game": (
            "1. Call a temporary halt via radio\n"
            "2. Click **Pause Game** or **Resume Game** in Mission Control\n"
            "3. Ensure all players acknowledge the pause\n"
            "4. Resume only when field is clear and safe"
        ),
        "arm_disarm_device": (
            "1. Confirm the device ID in Prop Network\n"
            "2. Verify no players are within 5m of the prop\n"
            "3. Use the Prop Network panel to send the arm/disarm command\n"
            "4. Wait for status confirmation before proceeding"
        ),
        "reset_device": (
            "1. Identify the device in Prop Network\n"
            "2. Ensure device is safely accessible\n"
            "3. Send reset command via Prop Network panel\n"
            "4. Monitor status — device should reconnect within 30 seconds"
        ),
        "trigger_device": (
            "1. Verify field is clear of players near the device\n"
            "2. Confirm trigger intent with nearest marshal\n"
            "3. Send trigger command via Prop Network panel\n"
            "4. Log the trigger event in the mission notes"
        ),
        "system_power": (
            "1. Notify all connected clients that the system is restarting\n"
            "2. Complete any active game sessions first\n"
            "3. Use the system shutdown/reboot option in System Monitor\n"
            "4. Wait 30 seconds before reconnecting clients"
        ),
        "adjust_score": (
            "1. Go to Mission Control → Game Controls\n"
            "2. Use the **+10** / **-10** score buttons for each team\n"
            "3. Note the adjustment reason in the session notes\n"
            "4. Inform both team marshals of the change"
        ),
    }
    return guides.get(action_key, "Use the appropriate panel in Mission Control or Prop Network to complete this action.")


# ---------------------------------------------------------------------------
# Game mode builder
# ---------------------------------------------------------------------------

def _build_game_mode_rules(mode_name: str, players: int | None, minutes: int | None) -> str:
    p = players or 10
    t = minutes or 20
    per_team = p // 2

    templates: dict[str, str] = {
        "skirmish": (
            f"**Skirmish – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Objective: Most eliminations wins\n"
            "- Respawn: Unlimited, 1-min delay at base\n"
            "- Scoring: 1 point per elimination, 5-point bonus for last-team-standing\n"
            "- Field: Any size — no objective markers needed\n"
            "- Marshal: One per team + one neutral"
        ),
        "domination": (
            f"**Domination – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Objectives: 3 control points (A, B, C)\n"
            "- Capture: Stand within 3m for 30 sec uncontested\n"
            "- Scoring: 1 point per 30-sec held per point\n"
            "- Respawn: Zone-based, 45-sec cooldown\n"
            "- Win: Most points at time-up or hold all 3 simultaneously for 2 min"
        ),
        "capture the flag": (
            f"**Capture The Flag – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Objective: Retrieve enemy flag, return to base\n"
            "- Flag carrier: cannot sprint, tagged = flag drops in place\n"
            "- Respawn: At base, 1-min cooldown\n"
            "- Scoring: 3 points per flag capture\n"
            "- Win: First to 3 captures or most at time-up"
        ),
        "king of the hill": (
            f"**King of the Hill – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Objective: One central zone — hold it\n"
            "- Control: Both teams in zone = contested (no points)\n"
            "- Scoring: 1 point per 10 sec held\n"
            "- Respawn: Flanks only, 30-sec cooldown\n"
            "- Win: First to 60 points"
        ),
        "hostage rescue": (
            f"**Hostage Rescue – {p} players, {t} min**\n"
            f"- Attackers: {per_team} players   Defenders: {p - per_team} players\n"
            "- Objective: Attackers extract the hostage prop to the extraction zone\n"
            "- Defenders must prevent extraction for the full duration\n"
            "- Hostage carrier: moves at walking pace, cannot fire\n"
            "- Respawn: Defenders unlimited (45-sec), Attackers 3 tickets each\n"
            "- Scoring: Extraction = 10 pts for attackers; time-out = 10 pts for defenders\n"
            "- Win: Team with most points after 2 rounds (swap roles between rounds)"
        ),
    }
    key = mode_name.lower().strip()
    for template_key, content in templates.items():
        if template_key in key or key in template_key:
            return content

    return (
        f"**{mode_name} – {p} players, {t} min**\n"
        f"- Teams: {per_team} vs {per_team}\n"
        "- Objective: Complete the primary objective before time expires\n"
        "- Respawn: 1-min cooldown at designated respawn zone\n"
        "- Scoring: Objective completion = 5 points, elimination = 1 point\n"
        "- Win: Highest score at end of round\n\n"
        "Let me know if you want to customise any rules (timers, scoring, respawn rules)."
    )


# ---------------------------------------------------------------------------
# Game suggestion engine
# ---------------------------------------------------------------------------

def _suggest_game(
    players: int | None,
    field_m: int | None,
    handicap_pct: int | None,
    minutes: int | None,
    available_modes: list[str] | None,
) -> str:
    p = players or 0
    f = field_m or 0
    h = handicap_pct or 0
    t = minutes or 20

    if p == 0:
        return (
            "To give you the best suggestion I'll need a bit more info — "
            "how many players do you have and roughly how large is your field?\n\n"
            "For example: *'We have 20 players on a 5000m² field, 25-minute sessions'*"
        )

    per_team = p // 2

    if p <= 8:
        mode_style = "close-quarters, fast-paced"
        recommendations = ["Skirmish", "Capture The Flag", "King of the Hill"]
        rule_note = "Keep rounds short (10–15 min) with a 3-min respawn delay."
    elif p <= 20:
        mode_style = "medium-team tactical"
        recommendations = ["Domination", "Capture The Flag", "King of the Hill"]
        rule_note = "Suggest 2 objectives minimum. 20-min rounds work well."
    else:
        mode_style = "large-force strategic"
        recommendations = ["Domination", "Hostage Rescue", "Skirmish"]
        rule_note = "Use 3+ objectives and a 30-min session with a 1-min respawn limit."

    # Overlay custom modes where names overlap
    if available_modes:
        for mode in available_modes:
            for i, rec in enumerate(recommendations):
                if rec.lower() in mode.lower() or mode.lower() in rec.lower():
                    recommendations[i] = mode

    handicap_note = ""
    if h >= 30:
        handicap_note = (
            f"\n\nWith a **{h}% handicap**, give the weaker team a 2-point head-start "
            "and restrict respawns for the stronger team."
        )
    elif h > 0:
        handicap_note = (
            f"\n\nWith a **{h}% handicap**, consider giving the weaker team an extra "
            "10 points at game start or one extra respawn ticket."
        )

    lines = [
        f"Based on **{p} players** ({per_team} per team)"
        + (f", **{f} m²** field" if f else "")
        + f", **{t}-minute** sessions — here are my top picks:",
        "",
    ]
    for i, mode in enumerate(recommendations[:3], 1):
        lines.append(f"{i}. **{mode}**")
    lines += [
        "",
        f"Style: {mode_style}.{handicap_note}",
        f"Rule tip: {rule_note}",
        "",
        "Want me to build out the full rule set for any of these? "
        "Just say which one and I'll draft objectives, timers, and scoring.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main conversational handler
# ---------------------------------------------------------------------------

def _mk_response(
    answer: str,
    confidence: float = 0.85,
    used_ctx: list[str] | None = None,
    suggested_actions: list[str] | None = None,
    requires_admin_confirmation: bool = False,
    blocked_actions: list[str] | None = None,
) -> AIAskResponse:
    return AIAskResponse(
        answer=answer,
        confidence=confidence,
        used_context=used_ctx or ["advisor:conversational", "provider:mock-local"],
        suggested_actions=suggested_actions or [],
        blocked_actions=blocked_actions or [],
        warnings=[],
        advisory_only=True,
        requires_admin_confirmation=requires_admin_confirmation,
        blocked_action=False,
        safety_notice=SAFETY_NOTICE,
        model=MOCK_MODEL_NAME,
    )


def _handle_conversation(
    prompt: str,
    history: list[dict[str, Any]],
    injected_context: str | None,
) -> AIAskResponse:
    text = prompt.strip()
    lower = text.lower()

    # Parse live operational context
    ctx = _parse_context_block(injected_context)

    # Numbers from current message, then fill from history, then from context block
    nums = _extract_numbers(lower)
    history_nums = _extract_nums_from_history(history)
    for k, v in history_nums.items():
        if k not in nums:
            nums[k] = v

    used_ctx = ["advisor:conversational", "provider:mock-local"]
    if injected_context:
        used_ctx.append("context:injected")

    # -----------------------------------------------------------------------
    # 1. Operational command flow (confirm before proceeding)
    # -----------------------------------------------------------------------
    action_key, action_label = _detect_operational_action(text)
    pending = _check_history_for_pending_confirmation(history)

    if action_key:
        is_confirm = bool(_CONFIRM_PATTERNS.search(lower))
        if is_confirm and pending == action_key:
            answer = (
                f"Confirmed. Here's the procedure to **{action_label}**:\n\n"
                + _action_guidance(action_key)
            )
            return _mk_response(answer, confidence=0.88,
                                 used_ctx=[*used_ctx, "advisor:confirmed_action"],
                                 suggested_actions=[f"Proceed with: {action_label}"])
        else:
            answer = (
                f"I can help you **{action_label}**. "
                "Before I guide you through this, can you confirm that's what you want to do?\n\n"
                "Reply **yes** or **confirm** to proceed, or tell me more about what you need.\n\n"
                f"[CONFIRM_ACTION:{action_key}]"
            )
            return _mk_response(answer, confidence=0.75,
                                 used_ctx=[*used_ctx, "advisor:awaiting_confirmation"],
                                 suggested_actions=["Confirm the action to proceed."],
                                 requires_admin_confirmation=True)

    # Bare confirmation with no current action — resolve pending if any
    if _CONFIRM_PATTERNS.match(lower) and len(lower.split()) <= 3:
        if pending:
            return _mk_response(
                "Confirmed. Here's the procedure:\n\n" + _action_guidance(pending),
                confidence=0.88,
                used_ctx=[*used_ctx, "advisor:confirmed_action"],
            )
        return _mk_response("Got it! What would you like me to help with?")

    # -----------------------------------------------------------------------
    # 2. Follow-up continuation (prevents "restart" behavior)
    # -----------------------------------------------------------------------
    last_assistant = _last_message_by_role(history, "assistant")
    followup_intent = _followup_intent(lower)

    # Direct mode reply after a recommendation prompt, e.g. user: "capture the flag"
    if last_assistant and re.search(r"want me to build out the full rule set", last_assistant, re.I):
        direct_mode = _extract_mode_from_text(lower, ctx.get("available_game_modes", []))
        if direct_mode:
            rules = _build_game_mode_rules(
                mode_name=direct_mode,
                players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
                minutes=nums.get("minutes"),
            )
            answer = (
                f"Great choice. Continuing from my last suggestion, here are the full **{direct_mode}** rules.\n\n"
                + rules
            )
            return _mk_response(
                answer,
                confidence=0.92,
                used_ctx=[*used_ctx, "history:followup_direct_mode"],
            )

    if _is_followup_message(lower) and last_assistant:
        chosen_mode = _select_mode_from_followup(
            user_text=lower,
            last_assistant=last_assistant,
            available_modes=ctx.get("available_game_modes", []),
        )

        if chosen_mode and re.search(r"\b(yes|ok|okay|go with|that one|do it|build|rules?)\b", lower):
            rules = _build_game_mode_rules(
                mode_name=chosen_mode,
                players=nums.get("players") or ctx.get("players"),
                minutes=nums.get("minutes"),
            )
            answer = (
                f"Perfect, continuing from my last suggestion. We'll run **{chosen_mode}**.\n\n"
                + rules
            )
            return _mk_response(
                answer,
                confidence=0.9,
                used_ctx=[*used_ctx, "history:followup_mode"],
            )

        answer = (
            "Got it, continuing from where we left off. "
            "Do you want me to expand the previous suggestion into a full plan, "
            "or adjust players, timer, or balancing first?"
        )
        return _mk_response(
            answer,
            confidence=0.84,
            used_ctx=[*used_ctx, "history:followup"],
        )

    # Advanced follow-up intents: compare/explain/summarize relative to prior answer
    if followup_intent and last_assistant:
        if followup_intent == "compare":
            comp = _compare_recommended_modes(last_assistant)
            if comp:
                return _mk_response(
                    comp + "\n\nTell me your priority (speed, fairness, objective complexity), and I will pick the best one.",
                    confidence=0.9,
                    used_ctx=[*used_ctx, "history:followup_compare"],
                )
        if followup_intent == "summarize":
            return _mk_response(
                _summarize_previous_answer(last_assistant),
                confidence=0.88,
                used_ctx=[*used_ctx, "history:followup_summarize"],
            )
        if followup_intent == "explain":
            modes = _extract_numbered_modes(last_assistant)
            if modes:
                return _mk_response(
                    "I recommended those because your player count and field size favor objective modes that keep everyone involved. "
                    "Domination gives stable scoring, Capture The Flag encourages movement, and King of the Hill creates high-intensity control battles. "
                    "If you want, I can choose one now based on your top priority.",
                    confidence=0.9,
                    used_ctx=[*used_ctx, "history:followup_explain"],
                )

    # -----------------------------------------------------------------------
    # 3. Live data queries — use the parsed context
    # -----------------------------------------------------------------------

    # Member recognition / profile query
    if re.search(r"\b(member|player|who is|recognize|recognise|strength|weakness|skill|team balance)\b", lower):
        member_lines = ctx.get("member_lines", [])
        if member_lines:
            preview = "\n".join([f"- {line}" for line in member_lines[:8]])
            answer = (
                "I recognize the following members from stored profiles:\n\n"
                f"{preview}\n\n"
                "If you want, I can suggest balanced squad assignments based on these profiles."
            )
            return _mk_response(
                answer,
                confidence=0.9,
                used_ctx=[*used_ctx, "context:members"],
                suggested_actions=["Generate team balancing plan from member profiles."],
            )
        return _mk_response(
            "I don't have member profiles yet. Tell me each person's name, gender, team, skill level, strengths, and weaknesses, and I'll store them for future guidance.",
            confidence=0.82,
            used_ctx=[*used_ctx, "context:members:none"],
        )

    # Score query
    if re.search(r"\b(score|points?|who('s| is) (winning|ahead)|what.{0,10}score)\b", lower):
        state = ctx["game_state"]
        r, b = ctx["red_score"], ctx["blue_score"]
        if state == "idle" and r == 0 and b == 0:
            answer = "No game is currently active. Scores will show here once a game is running."
        else:
            leader = "Red" if r > b else ("Blue" if b > r else "Tied")
            delta = abs(r - b)
            answer = (
                f"**Current scores:**\n\n"
                f"- Red: **{r}** pts\n"
                f"- Blue: **{b}** pts\n\n"
            )
            if r == b:
                answer += "The game is currently **tied**."
            else:
                answer += f"**{leader} team is leading** by {delta} points."
            if state != "running":
                answer += f"\n\n*(Game state: {state})*"
        return _mk_response(answer, confidence=0.92,
                             used_ctx=[*used_ctx, "context:live_scores"])

    # Timer query
    if re.search(r"\b(timer|time (left|remaining)|how (long|much time)|countdown)\b", lower):
        secs = ctx["timer_seconds"]
        state = ctx["game_state"]
        if state == "idle" or secs == 0:
            answer = "The timer is not currently running. Start a game in Mission Control to begin the countdown."
        elif state == "paused":
            answer = f"The game is **paused** with **{_fmt_timer(secs)}** remaining."
        else:
            answer = f"**{_fmt_timer(secs)}** remaining in the current game."
        return _mk_response(answer, confidence=0.92,
                             used_ctx=[*used_ctx, "context:live_timer"])

    # Game state query
    if re.search(r"\b(game (state|status)|is the game (running|active|on|paused|started)|what('s| is) (happening|the status))\b", lower):
        state = ctx["game_state"]
        mission = ctx["mission_title"] or "unknown"
        r, b = ctx["red_score"], ctx["blue_score"]
        secs = ctx["timer_seconds"]
        state_desc = {
            "running": f"**Running** — {_fmt_timer(secs)} remaining",
            "paused": f"**Paused** — {_fmt_timer(secs)} left on clock",
            "idle": "**Idle** — no active game",
            "ended": "**Ended** — game completed",
        }.get(state, state)
        answer = (
            f"**Mission:** {mission}\n"
            f"**State:** {state_desc}\n"
            f"**Score:** Red {r} – Blue {b}"
        )
        if ctx["schedule_current"]:
            answer += f"\n**Current activity:** {ctx['schedule_current']}"
        return _mk_response(answer, confidence=0.92,
                             used_ctx=[*used_ctx, "context:game_state"])

    # Device/prop status query
    if re.search(r"\b(device|prop|sensor|how many (devices?|props?)|devices? (online|offline|status))\b", lower):
        on = ctx["devices_online"]
        off = ctx["devices_offline"]
        total = ctx["devices_total"]
        if total == 0:
            answer = (
                "No devices are registered yet. "
                "Add your field props in the Prop Network panel and they will appear here."
            )
        else:
            answer = (
                f"**Device status:**\n\n"
                f"- Online: **{on}**\n"
                f"- Offline: **{off}**\n"
                f"- Total: **{total}**\n"
            )
            if off > 0:
                answer += (
                    f"\n⚠️ **{off} device{'s are' if off > 1 else ' is'} offline.**\n\n"
                    "Troubleshooting steps:\n"
                    "1. Check battery level (>20% required)\n"
                    "2. Verify LoRa signal — move closer to the gateway\n"
                    "3. Confirm last-seen timestamp in Prop Network\n"
                    "4. Send a status ping from Prop Network panel\n"
                    "5. Check firmware version matches other props"
                )
        return _mk_response(answer, confidence=0.9,
                             used_ctx=[*used_ctx, "context:devices"])

    # Schedule query
    if re.search(r"\b(schedule|next (activity|event|game|round)|what('s| is) next|current activity)\b", lower):
        cur = ctx["schedule_current"]
        nxt = ctx["schedule_next"]
        if not cur and not nxt:
            answer = (
                "No upcoming schedule items found. "
                "Add activities to the schedule in Mission Control to keep the event on track."
            )
        else:
            answer = ""
            if cur:
                answer += f"**Current activity:** {cur}\n\n"
            if nxt:
                answer += f"**Next activity:** {nxt}"
            if not answer:
                answer = "The schedule is clear — no current or upcoming activities."
        return _mk_response(answer, confidence=0.88,
                             used_ctx=[*used_ctx, "context:schedule"])

    # -----------------------------------------------------------------------
    # 3. Game suggestion flow
    # -----------------------------------------------------------------------
    if re.search(
        r"\b(suggest|recommend|what.{0,10}game|which.{0,10}game|best\s+game|pick\s+a\s+game|help.{0,10}choose|good game for)\b",
        lower,
    ):
        answer = _suggest_game(
            players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
            field_m=nums.get("field_m"),
            handicap_pct=nums.get("handicap_pct"),
            minutes=nums.get("minutes"),
            available_modes=ctx["available_game_modes"] or None,
        )
        return _mk_response(answer, confidence=0.86,
                             used_ctx=[*used_ctx, "advisor:game_suggestion"],
                             suggested_actions=["Choose a mode and ask me to build the full rule set."])

    # -----------------------------------------------------------------------
    # 4. Rule set builder
    # -----------------------------------------------------------------------
    is_build_mode = re.search(
        r"\b(build|create|draft|write|make|design)\b.{0,20}\b(game mode|ruleset|rules|mode)\b",
        lower,
    )
    is_detail_request = re.search(
        r"\b(rules?|full|details?|set\s*up|setup|how\s+to\s+play)\b.{0,20}"
        r"\b(skirmish|domination|capture|king|flag|hill|assault|siege|hostage)\b",
        lower,
    )
    if is_detail_request or is_build_mode:
        mode_match = re.search(
            r"\b(skirmish|domination|capture\s+the\s+flag|king\s+of\s+the\s+hill|"
            r"capture\s+flag|assault|siege|hostage\s+rescue|capture\s+point)\b",
            lower,
        )
        mode_name = mode_match.group(0).strip() if mode_match else "Custom Mode"
        answer = _build_game_mode_rules(
            mode_name=mode_name,
            players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
            minutes=nums.get("minutes"),
        )
        return _mk_response(answer, confidence=0.9,
                             used_ctx=[*used_ctx, "advisor:game_mode_builder"],
                             suggested_actions=["Save this mode in Admin > Game Modes to use it in Mission Control."])

    # -----------------------------------------------------------------------
    # 5. Specialist quick-responses
    # -----------------------------------------------------------------------

    if re.search(r"\bsummariz[ei]\w*\b|\bresults\b", lower):
        r, b = ctx["red_score"], ctx["blue_score"]
        mission = ctx["mission_title"] or "[Mission]"
        if ctx["game_state"] in ("ended", "running", "paused") and (r > 0 or b > 0):
            winner = "Red" if r > b else ("Blue" if b > r else "Draw")
            answer = (
                f"**Results Summary — {mission}**\n\n"
                f"- **Winner:** {winner}\n"
                f"- **Final score:** Red {r} — Blue {b}\n"
                f"- **Score gap:** {abs(r - b)} points\n\n"
                "Post-game recommendations:\n"
                "- Rotate starting positions next round\n"
                "- Review prop performance in Prop Network\n"
                "- Brief both teams on what worked\n\n"
                "Want a tactical debrief for each team?"
            )
        else:
            answer = (
                "Here's a results summary template:\n\n"
                "- **Winner:** [Team name] by [score delta] points\n"
                "- **Final score:** Red [X] — Blue [Y]\n"
                "- **Penalties applied:** [list]\n"
                "- **Fairness note for next round:** [e.g. rotate starting sides]\n"
                "- **Tactical tip — Red:** [one improvement]\n"
                "- **Tactical tip — Blue:** [one improvement]\n\n"
                "Start a game in Mission Control and I'll fill this in with live data."
            )
        return _mk_response(answer, confidence=0.85, used_ctx=[*used_ctx, "context:results"])

    if re.search(r"\bmarshal\b|\bbriefing\b", lower):
        mode = ctx.get("available_game_modes", [None])[0] if ctx["available_game_modes"] else None
        answer = (
            f"**Marshal Briefing Checklist{f' — {mode}' if mode else ''}:**\n\n"
            "1. Safety priorities — hit calls, eye protection mandatory\n"
            "2. Rule reminders — no blind firing, field boundaries, mercy rule\n"
            "3. Objective flow — explain win conditions clearly\n"
            "4. Dispute protocol — pause play, marshal ruling is final\n"
            "5. Emergency halt phrase — 'CODE RED, ALL STOP'\n"
            "6. Radio channel check — confirm all marshals on ch.1\n"
            "7. First aid point location\n\n"
            "Ready to print? I can format this as a full briefing card."
        )
        return _mk_response(answer, confidence=0.85, used_ctx=[*used_ctx, "advisor:briefing"])

    if re.search(r"\bschedule\b.*\b(delay|behind|late)\b|\bdelay\b|\brunning\s+late\b", lower):
        nxt = ctx["schedule_next"]
        answer = (
            "**Delay Recovery Plan:**\n\n"
            "- Cut break time by 5 min\n"
            "- Tighten briefing to key rules only (skip examples)\n"
            "- Move non-critical announcements to post-round\n"
            "- Compress game round if needed\n\n"
        )
        if nxt:
            answer += f"Next scheduled item: **{nxt}**\n\n"
        answer += "How far behind are you? I can help adjust the full schedule."
        return _mk_response(answer, confidence=0.82, used_ctx=[*used_ctx, "context:schedule"])

    if re.search(r"\bannouncement\b|\bteam\s*message\b|\bbroadcast\b", lower):
        teams = ctx["active_teams"]
        t1 = teams[0].split("(")[0].strip() if len(teams) > 0 else "Red Team"
        t2 = teams[1].split("(")[0].strip() if len(teams) > 1 else "Blue Team"
        answer = (
            f"**Team Announcement Draft:**\n\n"
            f"> 'Attention all players — next mission begins in 10 minutes. "
            f"{t1} and {t2}: report to your assigned staging lane, "
            "confirm radio is on channel 1, and await the marshal signal. "
            "Any questions, see the duty marshal now.'\n\n"
            "Want me to customise this with objective details?"
        )
        return _mk_response(answer, confidence=0.85, used_ctx=[*used_ctx, "advisor:announcement"])

    if re.search(r"\b(handicap|imbalance|uneven|disadvantage|advantage)\b", lower):
        h = nums.get("handicap_pct", 0)
        answer = (
            f"**Handling Team Imbalance{f' ({h}% handicap)' if h else ''}:**\n\n"
            "Options to balance the game:\n"
            "1. **Point head-start** — weaker team starts with 5–10 points\n"
            "2. **Extra respawn tickets** — weaker team gets +1 life per round\n"
            "3. **Objective advantage** — weaker team starts with one objective captured\n"
            "4. **Restricted loadout** — stronger team uses pistols only for first 5 min\n"
            "5. **Field advantage** — weaker team starts closer to key objectives\n\n"
            "Which would you like to apply? I can adjust the scoring rules accordingly."
        )
        return _mk_response(answer, confidence=0.85, used_ctx=[*used_ctx, "advisor:handicap"])

    if re.search(r"\b(hello|hi|hey|howdy|good morning|good afternoon|what can you do|help)\b", lower):
        state = ctx["game_state"]
        r, b = ctx["red_score"], ctx["blue_score"]
        status_line = ""
        if state == "running":
            status_line = f"\n\nCurrent game: **running** — Red {r} / Blue {b}, {_fmt_timer(ctx['timer_seconds'])} remaining."
        elif state == "paused":
            status_line = f"\n\nCurrent game: **paused** — Red {r} / Blue {b}."
        answer = (
            "Hi! I'm your AOJ field advisor. Here's what I can help with:\n\n"
            "- **Live data** — 'what's the score?', 'how long is left?', 'which devices are offline?'\n"
            "- **Game suggestions** — 'suggest a game for 16 players on a 4000m² field'\n"
            "- **Rule sets** — 'build domination rules for 20 players, 25 minutes'\n"
            "- **Marshal briefings** — 'generate a marshal briefing'\n"
            "- **Results summaries** — 'summarize today's results'\n"
            "- **Operational actions** — start/stop/reset (I'll ask you to confirm first)\n"
            "- **Schedule** — 'what's next on the schedule?'"
            + status_line
        )
        return _mk_response(answer, confidence=0.92, used_ctx=[*used_ctx, "advisor:greeting"])

    if re.search(r"\bwhat.{0,10}(learn|know|remember)\b", lower):
        memory = ctx["memory_lines"]
        if memory:
            answer = "Here's what I've picked up from our conversation:\n\n" + "\n".join(f"- {l}" for l in memory[:6])
        else:
            answer = (
                "I'm still learning from our conversation. "
                "The more you tell me about your field setup, teams, and game preferences, "
                "the better my suggestions get!"
            )
        return _mk_response(answer, confidence=0.8, used_ctx=[*used_ctx, "context:memory"])

    # -----------------------------------------------------------------------
    # 6. Context-aware fallback
    # -----------------------------------------------------------------------
    state = ctx["game_state"]
    r, b = ctx["red_score"], ctx["blue_score"]
    secs = ctx["timer_seconds"]
    mission = ctx["mission_title"]
    on = ctx["devices_online"]
    off = ctx["devices_offline"]

    status_parts: list[str] = []
    if mission:
        status_parts.append(f"Mission: **{mission}**")
    if state != "idle":
        status_parts.append(f"Game: **{state}**")
    if state in ("running", "paused") and secs > 0:
        status_parts.append(f"Timer: **{_fmt_timer(secs)}**")
    if state in ("running", "paused"):
        status_parts.append(f"Score: Red {r} / Blue {b}")
    if on or off:
        status_parts.append(f"Devices: {on} online / {off} offline")

    if status_parts:
        answer = (
            "Here's your current field status:\n\n"
            + "\n".join(f"- {p}" for p in status_parts)
            + "\n\nI can help with game suggestions, rule sets, briefings, "
            "diagnostics, or schedule management. What do you need?"
        )
    else:
        answer = (
            "I'm your AOJ field advisor, ready to help. Try asking:\n\n"
            "- 'Suggest a game for 16 players on a 4000m² field'\n"
            "- 'What's the score?'\n"
            "- 'Build domination rules for 20 players'\n"
            "- 'Generate a marshal briefing'"
        )

    return _mk_response(answer, confidence=0.75, used_ctx=[*used_ctx, "advisor:fallback"])


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ask_ai(
    prompt: str,
    injected_context: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> AIAskResponse:
    """Entry point for the conversational advisor.

    Tries Ollama (local LLM) first; falls back to the built-in rules engine
    so the system always works even without Ollama installed.
    """
    history = conversation_history or []

    # ------------------------------------------------------------------
    # Attempt Ollama (re-check once per cold start, then cache result)
    # ------------------------------------------------------------------
    global _ollama_available, _ollama_model
    if _ollama_available is None:
        _check_ollama()

    if _ollama_available:
        llm_answer = _ollama_chat(
            prompt=prompt,
            context=injected_context,
            history=history,
            model=_ollama_model,
        )
        if llm_answer:
            return AIAskResponse(
                answer=llm_answer,
                model=f"ollama/{_ollama_model}",
                context_used=bool(injected_context),
            )
        # Ollama request failed at runtime — retry on next request instead of
        # permanently disabling it for this process.
        logger.warning("Ollama request failed; falling back to rules engine.")
        _ollama_available = None

    # ------------------------------------------------------------------
    # Fallback: built-in rules engine
    # ------------------------------------------------------------------
    return _handle_conversation(
        prompt=prompt,
        history=history,
        injected_context=injected_context,
    )
