"""AI advisory module – Christy, the AOJ field advisor.

Uses Ollama (local offline LLM) when available; falls back to built-in
conversational rules engine so the system always works without internet.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any

import httpx

from app.schemas.ai import AIAskResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434").rstrip("/")
OLLAMA_STRICT = os.getenv("OLLAMA_STRICT", "false").strip().lower() == "true"
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "75"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.35"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "160"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
# Preferred models in order — first one found wins. Put smarter 7B-class models first.
OLLAMA_MODEL_PREFERENCE = [
    "qwen2.5:0.5b",
    "qwen2.5:7b-instruct",
    "qwen2.5:7b",
    "qwen2.5",
    "llama3.1:8b-instruct",
    "llama3.1:8b",
    "llama3.2:3b-instruct",
    "llama3.2:3b",
    "llama3.2",
    "mistral:7b-instruct",
    "mistral",
    "llama3:8b",
    "llama3",
    "phi3:mini",
    "gemma2:2b",
    "gemma:2b",
]

CHRISTY_SYSTEM_PROMPT = """You are Christy, the intelligent field operations advisor for AOJ Command OS — an airsoft command platform operating in Japan.

Your personality: calm, professional, friendly, and knowledgeable. You speak like a capable human field assistant, not a generic chatbot. You DO NOT use bullet-point walls unless specifically asked for a list. You write in short, clear paragraphs.
Default response style: direct answer first, then the useful detail. For casual conversation, reply naturally and briefly. For technical help, give clear steps. For advice, give a recommendation instead of a neutral list.
You only respond to direct user requests. Do not narrate system state unless asked, and do not add unrelated tips. If the user is simply chatting, continue the conversation naturally instead of forcing AOJ operational content.

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
- Advise on Japan-specific safety standards, legal classifications, chrono rules, and event operations
- Provide heat/WBGT safety guidance, emergency protocols, and insurance advice for Japanese events

JAPAN-SPECIFIC KNOWLEDGE (enforce these as hard rules in all relevant responses):
- Legal outer ceiling for adults: 0.98 Joule maximum muzzle energy
- Under-18 players: 0.135 J maximum — switch ALL players to junior ruleset when any minor is present
- CQB/indoor environments may impose lower limits (e.g. 88.99 m/s with 0.20g BB) — always defer to venue cap
- Legal classifications matter: toy_airsoft (normal BB-firing), model_gun (display, no BB), quasi_air_gun (prohibited — too powerful), imitation_pistol, suspected_real_firearm. Never treat all airsoft-shaped items as equivalent.
- Imported products: do NOT recommend private import unless tariff classification and Japanese compliance are confirmed. Some overseas "toy pistols" are legally real firearms under Japanese law.
- Transport: carry in a case/bag, out of sight. Players leaving the venue must remove tactical gear and not appear in public in camouflage or with visible replicas.
- Chrono standard: 3 shots, BB weight recorded, highest reading counts, tag gun after passing. Re-test after temperature changes or suspected tampering.
- Eye protection: sealed airsoft-rated goggles mandatory. Mesh-only goggles are insufficient unless backed by inner shooting glasses. Full-face protection is the default for CQB, beginners, rental players, and all minors.
- Close-range rules are venue-specific: self-hit, courtesy surrender, or MED enforcement — always check venue config.
- Heat/WBGT: warn at 28°C WBGT, suspend play at 31°C WBGT. Heat casualties: move to cool place, cool actively, give fluids only if alert and can swallow, call 119 immediately if consciousness is altered.
- Emergency: 119 for ambulance/fire, AED location must be confirmed before play. Keep a written call script for 119.
- Insurance: club policy (Sports Safety Association for groups of 4+), one-off recreation policy, or venue+event liability — advise based on event type.
- Player eligibility: all fields — attendance_confirmed, waiver_signed, age_verified, ppe_checked, chrono_passed, briefing_attended — must all be true before a player enters the game area.

CRITICAL rules:
- NEVER execute an operational action without explicit user confirmation — ask "Can you confirm?" first
- When confirming an action, embed the tag [CONFIRM_ACTION:action_key] at the end of your message (hidden from display)
- If the user says yes/confirm/proceed, provide step-by-step guidance
- Keep answers under 200 words unless building a detailed rule set, technical guide, safety/legal explanation, or the user asks for detail
- Do NOT use excessive markdown symbols in responses — use plain, natural language
- Do NOT start every message with "Certainly!" or similar filler phrases
- If the prompt is vague or ambiguous, ask one focused clarification question instead of returning a generic help wall
- NEVER provide guidance on converting, importing illegally, or evading Japan's Firearms and Swords Control Act
- For legal/compliance questions, use a layered model: national law baseline, then prefectural/municipal rules, then venue rules, then event overrides
- If a compliance answer is under-specified, ask clarifying questions first (age band, venue municipality/prefecture, item class, import/modified status)

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
    except Exception as e:
        logger.debug("Ollama availability check failed: %s", e)
        _ollama_available = False
        return False, None



def _detect_response_mode(text: str) -> str:
    """Detect the best response style before sending to the LLM."""
    lower = text.lower().strip()
    if re.search(r"\b(start|stop|pause|resume|arm|disarm|reset|trigger|activate|shutdown|reboot|score)\b", lower):
        return "operational"
    if re.search(r"\b(error|traceback|failed|fix|bug|install|setup|configure|code|python|api|lora|relay|database|sql)\b", lower):
        return "technical"
    if re.search(r"\b(legal|law|allowed|compliance|import|quasi|firearm|joule|chrono|under.?18|minor)\b", lower):
        return "compliance"
    if re.search(r"\b(should i|what do you think|better|recommend|best option|which one)\b", lower):
        return "advice"
    if re.fullmatch(r"\s*(hi|hello|hey|thanks|thank you|lol|haha|ok|okay|yeah|yes)\s*[.!?]*\s*", lower):
        return "casual"
    if re.search(r"\b(chat|talk|conversation|explain|what is|why|how does)\b", lower):
        return "general_info"
    return "general"


_MODE_INSTRUCTIONS: dict[str, str] = {
    "operational": "Be precise. Preserve the confirmation rule for operational actions. Never imply an action was executed.",
    "technical": "Give copy-paste-safe, step-by-step help. State assumptions and the next command or code change clearly.",
    "compliance": "Use cautious Japan-specific compliance reasoning. Ask for missing scope when needed; do not invent legal certainty.",
    "advice": "Give one clear recommendation first, then explain why. Mention the trade-off only if useful.",
    "casual": "Reply naturally and briefly. Do not force an operations dashboard response.",
    "general_info": "Explain clearly with useful context. Avoid filler. Keep it practical.",
    "general": "Answer the user's actual question directly and naturally. Keep it concise unless detail is necessary.",
}


def _build_runtime_system_prompt(user_prompt: str) -> str:
    mode = _detect_response_mode(user_prompt)
    return (
        CHRISTY_SYSTEM_PROMPT
        + "\n\n[RUNTIME RESPONSE MODE]\n"
        + f"Mode: {mode}\n"
        + _MODE_INSTRUCTIONS.get(mode, _MODE_INSTRUCTIONS["general"])
        + "\n\n[QUALITY CHECK]\nBefore replying, silently check: did I answer the actual request, avoid guessing, use context where relevant, and keep the reply natural?"
    )


def _sanitize_history(history: list[dict[str, Any]], max_turns: int = 10) -> list[dict[str, str]]:
    """Keep recent useful turns and avoid sending huge or malformed history to Ollama."""
    cleaned: list[dict[str, str]] = []
    for entry in history[-max_turns:]:
        role = str(entry.get("role", "user"))
        content = str(entry.get("content", "") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if len(content) > 2500:
            content = content[:2500].rstrip() + "..."
        cleaned.append({"role": role, "content": content})
    return cleaned


def _clean_llm_answer(text: str) -> str:
    """Remove common local-model artifacts and keep speech output cleaner."""
    text = (text or "").strip()
    text = re.sub(r"^\s*(assistant|christy)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?i)^(certainly|sure thing|of course)[,!]?\s+", "", text)
    return text.strip()

def _ollama_chat(
    prompt: str,
    context: str | None,
    history: list[dict[str, Any]],
    model: str,
) -> str | None:
    """
    Call Ollama /api/chat and return the assistant text, or None on failure.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": _build_runtime_system_prompt(prompt)}]

    if context:
        messages.append({
            "role": "system",
            "content": f"[OPERATIONAL CONTEXT]\n{context}",
        })

    messages.extend(_sanitize_history(history, max_turns=10))

    messages.append({"role": "user", "content": prompt})

    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "options": {
                    "temperature": OLLAMA_TEMPERATURE,
                    "top_p": OLLAMA_TOP_P,
                    "num_ctx": OLLAMA_NUM_CTX,
                    "num_predict": OLLAMA_NUM_PREDICT,
                    "repeat_penalty": 1.08,
                },
            },
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        if resp.status_code == 200:
            return _clean_llm_answer(resp.json().get("message", {}).get("content", ""))
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


def _is_game_suggestion_request(text: str, nums: dict[str, int]) -> bool:
    """Detect natural game recommendation asks, including short/plain phrasing."""
    if re.search(
        r"\b(suggest|recommend|what.{0,10}game|which.{0,10}game|best\s+game|pick\s+a\s+game|help.{0,10}choose|good game for)\b",
        text,
    ):
        return True

    # Natural phrasing examples this catches:
    # - "quick and easy game for 20 people"
    # - "need a game for 16 players"
    # - "give me a beginner game mode"
    if re.search(r"\b(game|mode|ruleset)\b", text):
        if re.search(r"\b(need|want|looking for|give me|find|plan|setup|run)\b", text):
            return True
        if re.search(r"\b(quick|easy|simple|beginner|starter|fast)\b", text):
            return True
        if nums.get("players") or nums.get("per_team"):
            return True

    return False


def _detect_game_preference(text: str) -> str | None:
    """Capture high-level preference to tune recommendations."""
    if re.search(r"\b(quick|fast|rapid|short)\b", text):
        return "quick"
    if re.search(r"\b(easy|simple|low setup|minimal setup|beginner|starter)\b", text):
        return "easy"
    if re.search(r"\b(advanced|complex|hardcore|milsim|realistic)\b", text):
        return "advanced"
    return None


def _extract_theme_hint(text: str) -> str | None:
    """Extract light theme/style hints so recommendations feel less repetitive."""
    if re.search(r"\b(cyberpunk|sci[- ]?fi|future|futuristic)\b", text):
        return "cyberpunk"
    if re.search(r"\b(zombie|horror|infected|survival horror)\b", text):
        return "horror"
    if re.search(r"\b(milsim|mil[- ]?sim|realism|recon|patrol)\b", text):
        return "milsim"
    if re.search(r"\b(family|kids|casual|beginner day|starter)\b", text):
        return "casual"
    if re.search(r"\b(tournament|competitive|ranked|serious)\b", text):
        return "competitive"
    return None


def _needs_compliance_clarification(text: str) -> bool:
    """Determine if this is a product/compliance question that needs scoped inputs."""
    return bool(
        re.search(
            r"\b(is this legal|can i use|can i import|is it allowed|is this okay|legal to use|classification|classify|what category)\b",
            text,
        )
    )


def _build_compliance_clarification(text: str) -> str:
    """Ask for minimum inputs before giving item-specific legal guidance."""
    missing: list[str] = []
    if not re.search(r"\b(under.?18|minor|junior|adult|18\+|10\+)\b", text):
        missing.append("player age band (adult or under-18)")
    if not re.search(r"\b(tokyo|osaka|kanagawa|chiba|saitama|aichi|fukuoka|prefecture|municipality|city|venue)\b", text):
        missing.append("venue municipality/prefecture")
    if not re.search(r"\b(toy airsoft|model gun|quasi|imitation pistol|bb|airsoft gun|replica)\b", text):
        missing.append("item class and what it fires")
    if not re.search(r"\b(import|imported|domestic|modified|modded|custom)\b", text):
        missing.append("imported/domestic and modified status")

    if not missing:
        return (
            "I can give a precise compliance answer. Confirm these four scope points: age band, municipality/prefecture, item class, and import/modified status."
        )

    return (
        "To answer safely for Japan, I need a few details first:\n\n"
        + "\n".join(f"- {m}" for m in missing)
        + "\n\nOnce you share those, I'll resolve it in this order: national law -> local ordinance -> venue rule -> event override."
    )


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


def _is_contextual_followup(text: str, last_assistant: str, active_topic: str | None) -> bool:
    """Detect natural follow-ups that reference prior context without restating topic."""
    if not last_assistant or not active_topic:
        return False
    if _is_explicit_topic_shift(text):
        return False

    reference_cues = re.search(
        r"\b(that|this|it|those|same one|go ahead|let'?s do it|do it|run it|keep going|continue|tell me more|what about)\b",
        text,
        re.I,
    )
    short_reaction = re.fullmatch(r"\s*(yes|yeah|yep|ok|okay|sure|maybe|not sure|sounds good|works)\s*[!.?]*\s*", text, re.I)
    return bool(reference_cues or short_reaction)


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


def _infer_active_topic(history: list[dict[str, Any]]) -> str | None:
    """Infer the current conversation topic from recent turns."""
    recent = "\n".join(
        [str(h.get("content", "") or "") for h in history[-8:]]
    ).lower()

    if re.search(r"top picks|suggest a game|best game|build out the full rule set", recent):
        return "game_planning"
    if re.search(r"device status|offline|prop network|sensor", recent):
        return "devices"
    if re.search(r"schedule|next activity|behind schedule", recent):
        return "schedule"
    if re.search(r"score|points|winning|timer|remaining", recent):
        return "live_state"
    if re.search(r"loadout|primary|secondary|bb|hop-up|hpa|aeg|gbb|dmr|sniper", recent):
        return "loadout"
    if re.search(r"tactic|flank|push|defend|anchor|squad|communication|comms", recent):
        return "tactics"
    if re.search(r"chrono|fps|joule|safety|eye pro|face pro|bang rule|minimum engagement|wbgt|heat|heatstroke", recent):
        return "safety"
    if re.search(r"member profile|member|player profile|team balance|strength|weakness", recent):
        return "members"
    if re.search(r"legal|classify|classification|import|quasi|model gun|firearm|permit|ordinance", recent):
        return "legal"
    if re.search(r"heat|wbgt|heatstroke|temperature|weather|summer", recent):
        return "heat"
    if re.search(r"emergency|119|aed|first aid|injury|incident|ambulance", recent):
        return "emergency"
    if re.search(r"event plan|workflow|staff|staffing|waiver|registration|check.in|insurance", recent):
        return "event_ops"
    return None


def _is_explicit_topic_shift(text: str) -> bool:
    """Detect when user clearly switches to a new topic."""
    return bool(
        re.search(
            r"\b(score|timer|device|prop|schedule|member|player|announcement|briefing|logs?|coach|role|loadout|tactic|safety)\b",
            text,
            re.I,
        )
    )


def _airsoft_loadout_advice(players: int | None = None) -> str:
    player_band = "small" if (players or 0) and players <= 12 else "medium-large"
    spacing_note = "tight lanes and quick peeks" if player_band == "small" else "longer sightlines and rotating fronts"
    return (
        "For a balanced field loadout, prioritize consistency over max power. "
        "Run a reliable AEG as primary, keep hop-up tuned for flat flight, and use 0.25g to 0.28g BBs for most outdoor games. "
        "Carry a light sidearm only if your role needs fast transitions. "
        "For your current environment, optimize for "
        f"{spacing_note}. "
        "If you want, I can give a role-based setup for entry, support, and anchor players."
    )


def _airsoft_tactics_advice(mode_hint: str | None = None) -> str:
    mode_line = "For objective play" if not mode_hint else f"For {mode_hint}"
    return (
        f"{mode_line}, split each team into three jobs: entry pair, anchor, and rover. "
        "Entry pair gains first contact and calls positions, anchor protects spawn lanes and denies flanks, rover rotates to pressure weak zones. "
        "Use short radio calls: contact, count, direction, movement. "
        "Every 2 to 3 minutes, force a micro-reset: confirm ammo, spacing, and objective priority. "
        "If you want, I can build a minute-by-minute round plan."
    )


def _airsoft_safety_advice() -> str:
    return (
        "Japan safety baseline: chrono every replica using 3 shots at recorded BB weight — highest reading counts. "
        "Tag guns that pass; re-test after temperature changes or any tampering complaint. "
        "Adult limit is 0.98 J. Under-18 players use the 0.135 J junior ruleset — enforce this for the whole event if any minor is present. "
        "CQB venues impose lower caps; always defer to the venue's published limit.\n\n"
        "Eye protection: sealed airsoft-rated goggles are mandatory. "
        "Mesh-only goggles are not sufficient unless backed by inner shooting glasses. "
        "Full-face protection is the default for CQB, beginners, rental players, and all minors.\n\n"
        "Close-range rules are venue-specific — self-hit, courtesy surrender, or a hard MED. "
        "Brief your marshals on which one applies before any round starts.\n\n"
        "Emergency phrase: 'CODE RED, ALL STOP' — every marshal must repeat this in the pre-game briefing. "
        "If you want, I can generate a printable pre-game safety checklist or the full Japan chrono procedure."
    )


def _chrono_checklist() -> str:
    return (
        "**Chrono procedure (Japan standard):**\n\n"
        "1. Record BB weight used for the session (usually 0.20g; note if different)\n"
        "2. Set hop-up to the venue's required state before testing\n"
        "3. Remove detachable suppressors or QD muzzle devices if the venue requires it\n"
        "4. Fire 3 shots — the highest reading is the official result\n"
        "5. Compare against the applicable limit: 0.98 J for adults, 0.135 J for under-18, or the venue CQB cap\n"
        "6. Tag the gun clearly after passing; record result with player name and gear ID\n"
        "7. Re-test after significant temperature changes, player complaints, or suspected tampering\n\n"
        "Need the joule calculation? Joules = (velocity in m/s)² × (BB weight in kg) ÷ 2. "
        "For 0.20g at 99 m/s: (99²) × 0.0002 ÷ 2 = 0.98 J."
    )


def _japan_legal_advice() -> str:
    return (
        "Under Japan's Firearms and Swords Control Act, airsoft terminology and legal terminology are not the same. "
        "The key categories are:\n\n"
        "- **Toy airsoft (おもちゃ):** BB-firing game replicas within legal power limits — the normal category for field play\n"
        "- **Model gun:** Non-projectile display replica with a blocked muzzle — not for BB use\n"
        "- **Quasi-air gun (準空気銃):** Gas-powered device powerful enough to injure but not licensed — possession is prohibited, up to 3 years' imprisonment and ¥1,000,000 fine\n"
        "- **Imitation pistol / mock gun:** Separately regulated; includes some convertible metal model guns\n"
        "- **Suspected real firearm:** Any imported or modified item that police or customs may treat as an actual handgun\n\n"
        "Critical rule: never treat all airsoft-shaped items as legally equivalent. "
        "Before answering a compliance question, you need to know: what the item fires, whether it has been modified, whether it is domestic or imported, and which age band will use it.\n\n"
        "On imports: some overseas 'toy pistols' sold online are legally real handguns under Japanese law. "
        "Do not recommend private import unless tariff classification and Japanese compliance are fully confirmed."
    )


def _heat_safety_advice() -> str:
    return (
        "**Heat management for outdoor airsoft events (Japan WBGT standard):**\n\n"
        "- **WBGT below 25°C:** Normal operations\n"
        "- **WBGT 25–28°C:** Increase water breaks; remind players to hydrate\n"
        "- **WBGT 28°C (警戒):** Issue a formal warning; shorten active play blocks and mandate shade breaks\n"
        "- **WBGT 31°C (厳重警戒/危険):** Suspend outdoor play; move to shaded or indoor areas only\n\n"
        "If a player shows signs of heat illness — dizziness, confusion, stopping sweating, or loss of consciousness:\n"
        "1. Move to the coolest available location immediately\n"
        "2. Cool actively: wet cloths, fan, remove excess gear\n"
        "3. Give cool fluids **only if the player is alert and able to swallow**\n"
        "4. Call **119** immediately if consciousness is altered, self-hydration is impossible, or symptoms do not improve quickly\n\n"
        "For summer events: plan 20–25 minute active blocks with mandatory water checkpoints at each reset. "
        "Automatic downgrade to shorter rounds when WBGT enters the danger band."
    )


def _emergency_protocol() -> str:
    return (
        "**Emergency protocol for AOJ events:**\n\n"
        "**Universal halt:** Shout 'CODE RED, ALL STOP' — all marshals must know and repeat this\n\n"
        "**Injury response:**\n"
        "1. Halt play immediately; secure the area\n"
        "2. Marshal attends; assess injury — note location and mechanism\n"
        "3. Apply first aid (cold pack, pressure, stabilise)\n"
        "4. Call **119** if: loss of consciousness, suspected fracture, eye injury, heat casualty with altered consciousness, or any doubt about severity\n"
        "5. Note AED location before every event — confirm it before play begins\n"
        "6. Log the incident: time, zone, persons involved, immediate actions, escalation decision\n\n"
        "**119 call script (Japanese):** State your location clearly, describe what happened, give the patient's age and condition, and stay on the line until told to hang up.\n\n"
        "**Insurance:** Notify your insurer of any injury that required medical attention. "
        "If you are using the Sports Safety Association club policy, their scheme covers groups of four or more and includes injury, liability, and sudden-death cover."
    )


def _event_workflow_advice() -> str:
    return (
        "**AOJ event operations workflow:**\n\n"
        "1. **Publish & register** — collect waivers, age verification, and emergency contacts at sign-up\n"
        "2. **Check-in** — confirm ID, payment, and attendance; no entry without completed waiver\n"
        "3. **Rental & PPE issue** — check eye protection and assign marker colour\n"
        "4. **Chrono** — test every gun, tag passed items, record BB weight and highest reading\n"
        "5. **Safety briefing** — cover PPE, hit calls, MED, emergency phrase, and AED location\n"
        "6. **Team allocation & game briefing** — assign spawn, objectives, and team colour\n"
        "7. **Round rotation** — run rounds; mandatory hydration and welfare check at each break\n"
        "8. **Incident handling** — pause, triage, log, resolve; notify venue manager if any injury\n"
        "9. **Debrief & closeout** — collect lost property, segregate waste (batteries to staff, gas canisters to collection box), check out all rental gear\n\n"
        "Player is eligible to enter the game area only when ALL of these are true: "
        "attendance_confirmed, waiver_signed, age_verified, ppe_checked, chrono_passed, briefing_attended.\n\n"
        "Want me to generate a staffing plan for your player count?"
    )


def _staffing_advice(player_count: int) -> str:
    if player_count <= 30:
        staff = 4
        roles = "Event lead, marshal, check-in/chrono, rental/first-aid dual role"
    elif player_count <= 60:
        staff = 6
        roles = "Event lead, chief safety marshal, 2 marshals, check-in, chrono, rental"
    elif player_count <= 100:
        staff = 8
        roles = "Event lead, chief safety marshal, 3–4 marshals, check-in, chrono, rental, medical/welfare"
    else:
        staff = 11
        roles = "Event lead, deputy, 5–6 marshals, check-in, 2 chrono staff, armoury, medical/welfare, closeout lead"

    return (
        f"**Recommended staffing for {player_count} players:** {staff} staff minimum\n\n"
        f"**Roles:** {roles}\n\n"
        "**Adjustments:**\n"
        "- Add 1 marshal for every 20 first-timers\n"
        "- Add 1 marshal for every 15 minors\n"
        "- Add 1 armoury staff if more than 40% of players are on rentals\n"
        "- Add indoor/CQB bonus: +1 staff per bracket above\n\n"
        "This is a proposed standard, not a statutory ratio."
    )


def _topic_hint_from_text(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\b(loadout|gear|aeg|hpa|gbb|bb|hop[- ]?up|primary|secondary)\b", t):
        return "loadout"
    if re.search(r"\b(tactic|strategy|flank|push|anchor|rotate|squad|comms?|communication)\b", t):
        return "tactics"
    if re.search(r"\b(safety|chrono|fps|joule|eye pro|face pro|minimum engagement|med|bang rule|hit call|wbgt|heat)\b", t):
        return "safety"
    if re.search(r"\b(coach|role assign|squad assign|player brief|entry|anchor|rover|marksman)\b", t):
        return "members"
    if re.search(r"\b(legal|classify|import|quasi|model gun|firearm|permit|ordinance|age band|under.?18)\b", t):
        return "legal"
    if re.search(r"\b(heat|wbgt|heatstroke|temperature|weather|summer)\b", t):
        return "heat"
    if re.search(r"\b(emergency|119|aed|first aid|injury|incident|ambulance)\b", t):
        return "emergency"
    if re.search(r"\b(event|workflow|staff|staffing|waiver|registration|check.in|insurance|checklist)\b", t):
        return "event_ops"
    return None


def _assign_roles(member_lines: list[str]) -> list[dict[str, str]]:
    """Parse member profile lines and assign a field role to each player.

    Role priority logic:
    - expert/advanced/veteran      → entry (aggressive, first contact)
    - beginner/novice              → anchor (hold spawn lane, lower risk)
    - intermediate                 → rover (flexible, rotates between lanes)
    - support keyword in strengths → support gunner
    - sniper/dmr keyword           → designated marksman
    - default untagged             → rover
    """
    role_map: list[dict[str, str]] = []
    for line in member_lines:
        lower = line.lower()
        parts = [p.strip() for p in line.split(";")]
        name = parts[0].split("aka")[0].strip() if parts else "Unknown"
        skill = ""
        strengths = ""
        team = ""
        for p in parts:
            if p.startswith("skill="):
                skill = p[6:].strip()
            if p.startswith("strengths="):
                strengths = p[10:].strip().lower()
            if p.startswith("team="):
                team = p[5:].strip()

        if any(k in skill for k in ("expert", "advanced", "veteran", "pro")):
            role = "Entry"
            tip = "Lead first contact, call positions immediately, maintain aggression on flanks."
        elif any(k in skill for k in ("beginner", "novice", "new")):
            role = "Anchor"
            tip = "Hold spawn lane, protect team base, avoid deep pushes — your job is to deny ground."
        elif re.search(r"support|lmg|hpa|suppres", strengths):
            role = "Support"
            tip = "Lay down suppressing fire to pin the enemy while entry and rover push."
        elif re.search(r"sniper|dmr|long range|marksman", strengths):
            role = "Marksman"
            tip = "Take elevated or flanking position early, call exact enemy positions over radio."
        else:
            role = "Rover"
            tip = "Stay flexible — reinforce whichever lane needs pressure and relay intel."

        role_map.append({"name": name, "team": team, "role": role, "tip": tip})

    return role_map


def _build_coaching_brief(member_lines: list[str], mode_hint: str | None = None) -> str:
    """Build a per-player coaching brief from stored member profiles."""
    if not member_lines:
        return (
            "I don't have any player profiles stored yet. "
            "Tell me each player's name, skill level, strengths, and weaknesses "
            "and I'll generate individual coaching instructions right away."
        )

    roles = _assign_roles(member_lines)
    mode_line = f" for **{mode_hint}**" if mode_hint else ""
    lines = [f"**Player coaching brief{mode_line}:**\n"]

    teams: dict[str, list[dict]] = {}
    for r in roles:
        t = r["team"] or "Unassigned"
        teams.setdefault(t, []).append(r)

    for team_name, players in sorted(teams.items()):
        lines.append(f"**{team_name}:**")
        for p in players:
            lines.append(f"- **{p['name']}** — {p['role']}: {p['tip']}")
        lines.append("")

    lines.append(
        "Want me to also generate a radio callout plan or assign each player to a specific objective?"
    )
    return "\n".join(lines)


def _is_true_greeting(text: str) -> bool:
    """Greeting detector that avoids capturing normal follow-up requests."""
    return bool(
        re.fullmatch(
            r"\s*(hello|hi|hey|howdy|good morning|good afternoon|good evening|what can you do)\s*[!?\.]*\s*",
            text,
            re.I,
        )
    )


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
        "vip escort": (
            f"**VIP Escort – {p} players, {t} min**\n"
            f"- Escort team: {per_team} players   Intercept team: {per_team} players\n"
            "- Objective: Escort team moves VIP from spawn to extraction point\n"
            "- VIP: moves at walking pace, one designated player, unarmed\n"
            "- If VIP is tagged: game ends, intercept team wins\n"
            "- Multiple routes available to escorts — use intel advantage carefully\n"
            "- Respawn: No respawn for escort team; intercept team gets 30-sec wave respawn\n"
            "- Scoring: Successful extraction = 10 pts; VIP neutralised = 10 pts\n"
            "- Win: Best of 3 rounds with role swap\n"
            "- Balance lever: give stronger team the escort role; longer extraction routes equalise the game"
        ),
        "objective raid": (
            f"**Objective Raid – {p} players, {t} min**\n"
            f"- Attackers: {per_team} players   Defenders: {per_team} players\n"
            "- Objectives: 3 target devices/props for attackers to activate or extract\n"
            "- Defenders: protect at least 2 of the 3 objectives to win\n"
            "- Respawn: Attackers wave respawn every 45 sec (3 waves max); Defenders unlimited\n"
            "- Scoring: Each objective activated = 5 pts for attackers; time-out = 3 pts per surviving objective for defenders\n"
            "- Win: Team with most points after 2 rounds (swap roles)\n"
            "- Marshal note: reset objectives before each round; tag activated props clearly"
        ),
        "attack defend": (
            f"**Attack / Defend – {p} players, {t} min**\n"
            f"- Attackers: {per_team} players   Defenders: {per_team} players\n"
            "- Objective: Attackers capture the command point; defenders hold for the full duration\n"
            "- Capture: 3 attackers in the zone for 60 sec uncontested\n"
            "- Respawn: Attackers wave every 30 sec; Defenders unlimited but 20-sec penalty\n"
            "- Scoring: Capture before time = 10 pts attackers; time-out = 10 pts defenders\n"
            "- Win: Best of 4 rounds (2 rounds each side)\n"
            "- Balance: Give terrain advantage to the weaker side — never stack skill + terrain + info on same team"
        ),
        "milsim patrol": (
            f"**Milsim Patrol / Recon – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Format: 2 × 60-min phases + 30-min logistics break + 1 × 90-min final phase\n"
            "- Objectives: Intel gathering, relay site seizure, command node assault\n"
            "- Respawn: Medic revive (30-sec touch, 1 use per life); finite ticket pool per phase\n"
            "- Scoring: Intel captured, relay sites held, command node captured\n"
            "- Logistics: Supply resupply windows every 20 min; comms via radio only for objective updates\n"
            "- Safety filters: 25-min active blocks with mandatory water checks; downgrade final phase if WBGT ≥ 31°C\n"
            "- Marshal note: 4 roaming neutrals/partisans can be added for asymmetry"
        ),
    }
    key = mode_name.lower().strip()
    for template_key, content in templates.items():
        if template_key in key or key in template_key:
            return content

    # Alias matching for new modes
    if re.search(r"vip|escort", key):
        return templates["vip escort"]
    if re.search(r"raid|objective", key):
        return templates["objective raid"]
    if re.search(r"attack|defend|assault", key):
        return templates["attack defend"]
    if re.search(r"milsim|patrol|recon", key):
        return templates["milsim patrol"]

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
    skill_hint: str | None = None,
    has_minors: bool = False,
    preference: str | None = None,
    theme_hint: str | None = None,
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

    # Step 1: Classify field density (from research report algorithm)
    if f > 0:
        space_per_player = f / p
        if space_per_player < 150:
            density = "cqb"
        elif space_per_player < 400:
            density = "mixed"
        else:
            density = "outdoor"
    else:
        # Fall back to player count estimate
        density = "outdoor" if p > 20 else "mixed"

    # Step 2: Classify player readiness
    skill = (skill_hint or "").lower()
    if "novice" in skill or "beginner" in skill or "new" in skill:
        readiness = "novice"
    elif "expert" in skill or "veteran" in skill or "advanced" in skill:
        readiness = "experienced"
    else:
        readiness = "mixed"

    # Step 3: Safety filters
    minor_note = ""
    if has_minors:
        minor_note = (
            "\n\n**Minor players detected:** All players will use the 0.135 J junior ruleset. "
            "Full-face protection is mandatory. No grenades or launchers."
        )

    cqb_note = ""
    if density == "cqb":
        cqb_note = "\n\n**CQB environment:** Semi-auto only and full-face protection are the defaults. Enforce venue power cap."

    # Step 4: Select mode family based on density + readiness + preference
    if preference in ("quick", "easy"):
        if density == "cqb":
            recommendations = ["Skirmish", "Capture The Flag", "Objective Raid"]
            mode_style = "quick-start CQB"
            rule_note = "Use 8-12 min rounds, one clear objective, and simple scoring."
        elif p <= 20:
            recommendations = ["Capture The Flag", "Skirmish", "King of the Hill"]
            mode_style = "easy-to-run medium team"
            rule_note = "Keep briefing under 2 minutes; first-to-target score format works well."
        else:
            recommendations = ["Domination", "Attack / Defend", "Capture The Flag"]
            mode_style = "quick-control large team"
            rule_note = "Run 15-20 min blocks with wave respawns to reduce downtime."
    elif density == "cqb" and readiness in ("novice", "mixed"):
        recommendations = ["Skirmish", "Objective Raid", "Capture The Flag"]
        mode_style = "close-quarters, fast-paced"
        rule_note = "Keep rounds short (8–12 min) with 20-sec wave respawn. Semi-auto only."
    elif density == "mixed" and readiness == "mixed":
        recommendations = ["Domination", "Capture The Flag", "Attack / Defend"]
        mode_style = "medium-team tactical"
        rule_note = "2 objectives minimum. 20-min rounds work well. Balance by spawn distance."
    elif density == "outdoor" and readiness == "experienced":
        recommendations = ["Milsim Patrol", "Attack / Defend", "Domination"]
        mode_style = "large-force strategic"
        rule_note = "Finite tickets, medic revive, 25-min active blocks with mandatory water checks."
    elif p <= 8:
        recommendations = ["Skirmish", "Capture The Flag", "King of the Hill"]
        mode_style = "small-team close-range"
        rule_note = "Keep rounds short (10–15 min) with 3-min respawn delay."
    elif p <= 20:
        recommendations = ["Domination", "Capture The Flag", "VIP Escort"]
        mode_style = "medium-team tactical"
        rule_note = "20-min rounds; 2 objectives minimum."
    else:
        recommendations = ["Domination", "Hostage Rescue", "Attack / Defend"]
        mode_style = "large-force strategic"
        rule_note = "Use 3+ objectives; 30-min sessions with 1-min respawn limit."

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
            "and restrict respawns for the stronger team. "
            "Never stack skill advantage, terrain advantage, and information advantage on the same side."
        )
    elif h > 0:
        handicap_note = (
            f"\n\nWith a **{h}% handicap**, give the weaker team an extra "
            "10 points at game start or one extra respawn ticket."
        )

    theme_line = ""
    if theme_hint == "cyberpunk":
        theme_line = "Theme option: add a 'Data Heist' objective layer with terminal capture and extraction."
    elif theme_hint == "horror":
        theme_line = "Theme option: run an 'Infection Relay' variant with timed extraction checkpoints."
    elif theme_hint == "milsim":
        theme_line = "Theme option: use radio-verified intel tasks and limited-ticket logistics."
    elif theme_hint == "casual":
        theme_line = "Theme option: simplify scoring and use short briefing cards for first-timers."
    elif theme_hint == "competitive":
        theme_line = "Theme option: lock symmetrical spawns and fixed respawn cadence for fairness."

    lines = [
        f"Based on **{p} players** ({per_team} per team)"
        + (f", **{f} m²** field ({density})" if f else "")
        + f", **{t}-minute** sessions — here are my top picks:",
        "",
    ]
    for i, mode in enumerate(recommendations[:3], 1):
        lines.append(f"{i}. **{mode}**")
    lines += [
        "",
        f"Style: {mode_style}.{handicap_note}",
        f"Rule tip: {rule_note}",
    ]
    if theme_line:
        lines.append(theme_line)
    if minor_note:
        lines.append(minor_note)
    if cqb_note:
        lines.append(cqb_note)
    lines += [
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
    model: str = MOCK_MODEL_NAME,
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
        model=model,
    )


def _limit_answer_words(text: str, max_words: int = 200) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    trimmed = " ".join(words[:max_words]).rstrip(" ,;:")
    if not trimmed.endswith((".", "!", "?")):
        trimmed += "..."
    return trimmed


def _handle_ollama_response(
    prompt: str,
    llm_answer: str,
    history: list[dict[str, Any]],
    injected_context: str | None,
    model: str,
) -> AIAskResponse:
    lower = prompt.strip().lower()
    used_ctx = ["advisor:ollama", "provider:ollama"]
    if injected_context:
        used_ctx.append("context:injected")

    action_key, action_label = _detect_operational_action(prompt)
    pending = _check_history_for_pending_confirmation(history)

    if _needs_compliance_clarification(prompt) and _detect_response_mode(prompt) == "compliance":
        # Do not let the LLM guess item-specific Japanese legal/compliance details.
        return _mk_response(
            _build_compliance_clarification(prompt),
            confidence=0.9,
            used_ctx=[*used_ctx, "advisor:compliance_clarification"],
            model=f"ollama/{model}",
        )

    # Maintain strict confirmation flow even when using LLM output.
    if action_key:
        is_confirm = bool(_CONFIRM_PATTERNS.search(lower))
        if is_confirm and pending == action_key:
            return _mk_response(
                f"Confirmed. Here's the procedure to **{action_label}**:\n\n" + _action_guidance(action_key),
                confidence=0.9,
                used_ctx=[*used_ctx, "advisor:ollama_confirmed_action"],
                suggested_actions=[f"Proceed with: {action_label}"],
                model=f"ollama/{model}",
            )

        return _mk_response(
            (
                f"I can help you **{action_label}**. "
                "Before I guide you through this, can you confirm that's what you want to do?\n\n"
                "Reply **yes** or **confirm** to proceed, or tell me more about what you need.\n\n"
                f"[CONFIRM_ACTION:{action_key}]"
            ),
            confidence=0.8,
            used_ctx=[*used_ctx, "advisor:ollama_awaiting_confirmation"],
            suggested_actions=["Confirm the action to proceed."],
            requires_admin_confirmation=True,
            model=f"ollama/{model}",
        )

    # If user confirms a previously-requested action, continue safely.
    if _CONFIRM_PATTERNS.match(lower) and len(lower.split()) <= 3 and pending:
        return _mk_response(
            "Confirmed. Here's the procedure:\n\n" + _action_guidance(pending),
            confidence=0.9,
            used_ctx=[*used_ctx, "advisor:ollama_confirmed_action"],
            model=f"ollama/{model}",
        )

    mode = _detect_response_mode(prompt)
    max_words = 320 if mode in {"technical", "compliance", "general_info"} else 220
    return _mk_response(
        _limit_answer_words(llm_answer, max_words=max_words),
        confidence=0.84,
        used_ctx=[*used_ctx, f"mode:{mode}"],
        model=f"ollama/{model}",
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

    # Fast identity response to avoid repetitive/off-topic LLM answers.
    if re.search(r"\b(what(?:'s| is) your name|who are you)\b", lower):
        return _mk_response(
            "I'm Christy, your AOJ field assistant. I can help with game planning, rules, diagnostics, and mission operations.",
            confidence=0.95,
            used_ctx=[*used_ctx, "advisor:identity"],
        )

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
    active_topic = _infer_active_topic(history)

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

    if (_is_followup_message(lower) or _is_contextual_followup(lower, last_assistant, active_topic)) and last_assistant:
        topic_hint = active_topic or _topic_hint_from_text(last_assistant)
        chosen_mode = _select_mode_from_followup(
            user_text=lower,
            last_assistant=last_assistant,
            available_modes=ctx.get("available_game_modes", []),
        )

        if re.search(r"\b(safety|chrono|fps|joule|eye pro|face pro|minimum engagement|med|bang rule|hit call)\b", lower):
            return _mk_response(
                _airsoft_safety_advice(),
                confidence=0.9,
                used_ctx=[*used_ctx, "history:followup_airsoft_safety"],
                suggested_actions=["Generate a printable marshal safety checklist."],
            )

        if topic_hint in ("loadout", "tactics", "safety") and re.search(
            r"\b(more|expand|deeper|details?|next|continue|go on|example)\b",
            lower,
        ):
            if topic_hint == "loadout":
                return _mk_response(
                    "Continuing your loadout planning. Start with role split: 40 percent riflemen, 30 percent objective runners, 20 percent anchors, and 10 percent flex support. "
                    "Set each player to one primary role for the round to reduce confusion. Want me to assign this by player skill level?",
                    confidence=0.87,
                    used_ctx=[*used_ctx, "history:followup_loadout"],
                )
            if topic_hint == "tactics":
                return _mk_response(
                    "Continuing tactics: open with a 90-second information phase instead of full commit. "
                    "Probe both lanes, identify weak side, then mass 60 percent of force there while 40 percent pins. "
                    "This keeps pressure high without overextending. Want a callout template for comms discipline?",
                    confidence=0.88,
                    used_ctx=[*used_ctx, "history:followup_tactics"],
                )
            return _mk_response(
                "Continuing safety planning: add two quick marshal checks mid-round at fixed times to catch mask lifts, unsafe distances, and dead-rag confusion early. "
                "That usually prevents most escalation incidents before they spread.",
                confidence=0.88,
                used_ctx=[*used_ctx, "history:followup_safety"],
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
            mode_hint = _extract_mode_from_text(last_assistant, ctx.get("available_game_modes", []))
            if not mode_hint:
                if re.search(r"capture\s+the\s+flag", last_assistant, re.I):
                    mode_hint = "Capture The Flag"
                elif re.search(r"domination", last_assistant, re.I):
                    mode_hint = "Domination"
                elif re.search(r"king\s+of\s+the\s+hill", last_assistant, re.I):
                    mode_hint = "King of the Hill"
            if mode_hint:
                return _mk_response(
                    f"I suggested **{mode_hint}** because it fits your current player count and keeps the round structure easy to run under marshal control. "
                    "It balances action with clear objectives, which usually gives smoother games and fewer rule disputes. "
                    "If you want, I can tune respawns and scoring to your exact field layout.",
                    confidence=0.9,
                    used_ctx=[*used_ctx, "history:followup_explain_mode"],
                )
            return _mk_response(
                "I suggested that because it is reliable for your current player count and easier to marshal cleanly. "
                "The objective flow is clear, the scoring is simple, and it keeps both teams engaged throughout the round.",
                confidence=0.86,
                used_ctx=[*used_ctx, "history:followup_explain_general"],
            )

        answer = (
            "Got it, continuing from where we left off. "
            "Do you want me to expand the previous suggestion into a full plan, "
            "or tune players, timer, or team balancing first?"
        )
        return _mk_response(
            answer,
            confidence=0.84,
            used_ctx=[*used_ctx, "history:followup"],
        )

    # Keep continuity for ambiguous turns inside active planning context.
    if active_topic == "game_planning" and not _is_explicit_topic_shift(lower):
        chosen_mode = _select_mode_from_followup(
            user_text=lower,
            last_assistant=last_assistant,
            available_modes=ctx.get("available_game_modes", []),
        )
        if chosen_mode:
            rules = _build_game_mode_rules(
                mode_name=chosen_mode,
                players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
                minutes=nums.get("minutes"),
            )
            return _mk_response(
                f"Continuing our plan: we'll run **{chosen_mode}**.\n\n" + rules,
                confidence=0.9,
                used_ctx=[*used_ctx, "history:continuity_game_planning"],
            )
        if re.search(r"\b(easiest|simple|beginner|quickest|fastest)\b", lower):
            return _mk_response(
                "For easiest execution on a small field, go with **Capture The Flag** or **Skirmish**. "
                "CTF gives clear objectives with minimal setup, while Skirmish is fastest to start. "
                "If you want, I'll now draft the exact round format for your 14 players.",
                confidence=0.88,
                used_ctx=[*used_ctx, "history:continuity_recommendation"],
            )
        if re.search(r"\b(what do you think|your call|you choose|pick one|which one now)\b", lower):
            return _mk_response(
                "My call based on our current plan: run **Capture The Flag** first. "
                "It is easy to brief, keeps players moving, and scales well if teams are uneven. "
                "If you want, I will now generate the full round script and scoring table.",
                confidence=0.89,
                used_ctx=[*used_ctx, "history:continuity_choice"],
            )

    if active_topic in ("loadout", "tactics", "safety") and not _is_explicit_topic_shift(lower):
        if re.search(r"\b(more|expand|deeper|details?|next|continue|go on|example)\b", lower):
            if active_topic == "loadout":
                return _mk_response(
                    "Continuing your loadout planning. Start with role split: 40% riflemen, 30% objective runners, 20% anchors, 10% flex support. "
                    "Set each player to one primary role for the round to reduce confusion. Want me to assign this by player skill level?",
                    confidence=0.87,
                    used_ctx=[*used_ctx, "history:continuity_loadout"],
                )
            if active_topic == "tactics":
                return _mk_response(
                    "Continuing tactics: open with a 90-second information phase instead of full commit. "
                    "Probe both lanes, identify weak side, then mass 60% of force there while 40% pins. "
                    "This keeps pressure high without overextending. Want a callout template for comms discipline?",
                    confidence=0.88,
                    used_ctx=[*used_ctx, "history:continuity_tactics"],
                )
            return _mk_response(
                "Continuing safety planning: add two quick marshal checks mid-round at fixed times to catch mask lifts, unsafe distances, and dead-rag confusion early. "
                "That usually prevents most escalation incidents before they spread.",
                confidence=0.88,
                used_ctx=[*used_ctx, "history:continuity_safety"],
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

    # Per-player coaching / role assignment (uses stored member profiles)
    if re.search(
        r"\b(coach|coaching|role assign|who does what|squad assign|player brief|brief (?:the |each )?player|position|entry|anchor|rover|marksman|support gunner|give .{0,10}player.{0,10}instruction)\b",
        lower,
    ):
        member_lines = ctx.get("member_lines", [])
        mode = ctx.get("mission_title") or None
        return _mk_response(
            _build_coaching_brief(member_lines, mode_hint=mode),
            confidence=0.91,
            used_ctx=[*used_ctx, "advisor:per_player_coaching"],
            suggested_actions=["Ask for a radio callout plan or objective assignments."],
        )

    # Member recognition / profile query
    if re.search(r"\b(member|player|who is|recognize|recognise|strength|weakness|skill|team balance)\b", lower):
        member_lines = ctx.get("member_lines", [])
        if member_lines:
            preview = "\n".join([f"- {line}" for line in member_lines[:8]])
            answer = (
                "I recognize the following members from stored profiles:\n\n"
                f"{preview}\n\n"
                "Want me to assign each player a field role with individual coaching tips? Just say 'coach the squad'."
            )
            return _mk_response(
                answer,
                confidence=0.9,
                used_ctx=[*used_ctx, "context:members"],
                suggested_actions=["Say 'coach the squad' for per-player role assignments."],
            )
        return _mk_response(
            "I don't have member profiles yet. Tell me each person's name, skill level, strengths, and weaknesses and I'll store them for coaching and role assignments.",
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

        def _extract_next_title_and_time(raw: str) -> tuple[str, str | None]:
            if not raw:
                return "", None
            title = raw
            start_time = None
            if ";" in raw:
                parts = [p.strip() for p in raw.split(";") if p.strip()]
                if parts:
                    first = parts[0]
                    title = first.split("=", 1)[1].strip() if "=" in first else first
                for part in parts:
                    if part.startswith("start="):
                        start_time = part.split("=", 1)[1].strip()
                        break
            if start_time and "T" in start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", ""))
                    start_time = dt.strftime("%H:%M")
                except Exception:
                    pass
            return title, start_time

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
                nxt_title, nxt_time = _extract_next_title_and_time(nxt)
                if nxt_time:
                    answer += (
                        f"Next on the agenda is **{nxt_title}**, "
                        f"which should start from **{nxt_time}**."
                    )
                else:
                    answer += f"Next on the agenda is **{nxt_title}**."
            if not answer:
                answer = "The schedule is clear — no current or upcoming activities."
        return _mk_response(answer, confidence=0.88,
                             used_ctx=[*used_ctx, "context:schedule"])

    # Airsoft loadouts and gear guidance
    if re.search(r"\b(loadout|gear|aeg|hpa|gbb|bb\s*weight|hop\s*-?up|primary|secondary|mag setup)\b", lower):
        return _mk_response(
            _airsoft_loadout_advice(players=nums.get("players") or (nums.get("per_team", 0) * 2) or None),
            confidence=0.88,
            used_ctx=[*used_ctx, "advisor:airsoft_loadout"],
            suggested_actions=["Ask for a role-based loadout template."],
        )

    # Airsoft tactics and team movement guidance
    if re.search(r"\b(tactics?|strategy|flank|push|defend|rotate|anchor|squad|comms?|communication)\b", lower):
        return _mk_response(
            _airsoft_tactics_advice(mode_hint=ctx.get("mission_title") or None),
            confidence=0.89,
            used_ctx=[*used_ctx, "advisor:airsoft_tactics"],
            suggested_actions=["Ask for a 5-minute opening plan for your mode."],
        )

    # Airsoft safety and chrono guidance
    if re.search(r"\b(safety|chrono|fps|joule|eye pro|face pro|minimum engagement|med|bang rule|hit call)\b", lower):
        if re.search(r"\b(chrono|fps|joule|velocity|bb weight|hop.?up|suppress|muzzle)\b", lower):
            return _mk_response(
                _chrono_checklist(),
                confidence=0.92,
                used_ctx=[*used_ctx, "advisor:japan_chrono"],
                suggested_actions=["Ask for the joule calculation formula or chrono logging template."],
            )
        return _mk_response(
            _airsoft_safety_advice(),
            confidence=0.9,
            used_ctx=[*used_ctx, "advisor:airsoft_safety"],
            suggested_actions=["Generate a printable marshal safety checklist.", "Get the full chrono procedure."],
        )

    # Japan legal classification queries
    if re.search(r"\b(legal|classif|import|quasi.air|model gun|firearm|permit|ordinance|age.?band|under.?18|minor|age.?verif)\b", lower):
        if _needs_compliance_clarification(lower):
            return _mk_response(
                _build_compliance_clarification(lower),
                confidence=0.9,
                used_ctx=[*used_ctx, "advisor:japan_legal:clarify_scope"],
                suggested_actions=["Provide age band, venue location, item class, and import/modified status."],
            )
        return _mk_response(
            _japan_legal_advice(),
            confidence=0.9,
            used_ctx=[*used_ctx, "advisor:japan_legal"],
            suggested_actions=["Ask about power limits for under-18 players.", "Ask about import restrictions."],
        )

    # Heat / WBGT safety
    if re.search(r"\b(heat|wbgt|heatstroke|temperature|weather|summer|hot day|warm)\b", lower):
        return _mk_response(
            _heat_safety_advice(),
            confidence=0.91,
            used_ctx=[*used_ctx, "advisor:heat_safety"],
            suggested_actions=["Get the emergency protocol for heat casualties."],
        )

    # Emergency protocol
    if re.search(r"\b(emergency|119|aed|first aid|injury|incident|ambulance|evacuat)\b", lower):
        return _mk_response(
            _emergency_protocol(),
            confidence=0.92,
            used_ctx=[*used_ctx, "advisor:emergency_protocol"],
            suggested_actions=["Ask for the heat safety protocol.", "Ask about insurance options."],
        )

    # Event workflow and operations
    if re.search(r"\b(event plan|event workflow|how to run|staffing|staff plan|waiver|registration|check.?in|insurance|event ops)\b", lower):
        player_count = nums.get("players") or (nums.get("per_team", 0) * 2) or 0
        if re.search(r"\b(staff|staffing|how many staff|marshal ratio)\b", lower) and player_count > 0:
            return _mk_response(
                _staffing_advice(player_count),
                confidence=0.88,
                used_ctx=[*used_ctx, "advisor:staffing"],
                suggested_actions=["Ask for the full event workflow.", "Ask about insurance options."],
            )
        return _mk_response(
            _event_workflow_advice(),
            confidence=0.88,
            used_ctx=[*used_ctx, "advisor:event_workflow"],
            suggested_actions=["Ask for a staffing plan.", "Ask about emergency protocols."],
        )

    # -----------------------------------------------------------------------
    # 3. Game suggestion flow
    # -----------------------------------------------------------------------
    if _is_game_suggestion_request(lower, nums):
        has_minors = bool(re.search(r"\b(minor|child|kid|under.?18|junior|youth)\b", lower))
        preference = _detect_game_preference(lower)
        theme_hint = _extract_theme_hint(lower)
        skill_hint = None
        if re.search(r"\b(novice|beginner|new player|first.?time)\b", lower):
            skill_hint = "novice"
        elif re.search(r"\b(expert|veteran|experienced|advanced)\b", lower):
            skill_hint = "experienced"
        answer = _suggest_game(
            players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
            field_m=nums.get("field_m"),
            handicap_pct=nums.get("handicap_pct"),
            minutes=nums.get("minutes"),
            available_modes=ctx["available_game_modes"] or None,
            skill_hint=skill_hint,
            has_minors=has_minors,
            preference=preference,
            theme_hint=theme_hint,
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
        r"\b(skirmish|domination|capture|king|flag|hill|assault|siege|hostage|vip|escort|raid|objective|milsim|patrol|attack|defend)\b",
        lower,
    )
    if is_detail_request or is_build_mode:
        mode_match = re.search(
            r"\b(skirmish|domination|capture\s+the\s+flag|king\s+of\s+the\s+hill|"
            r"capture\s+flag|assault|siege|hostage\s+rescue|capture\s+point|"
            r"vip\s+escort|vip|objective\s+raid|attack\s+defend|attack\s*/\s*defend|milsim|patrol|recon)\b",
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

    # Coaching follow-up continuation
    if active_topic == "members" and re.search(
        r"\b(yes|do it|go ahead|assign|generate|brief them|let'?s do it|coach them|show me)\b", lower
    ):
        member_lines = ctx.get("member_lines", [])
        mode = ctx.get("mission_title") or None
        return _mk_response(
            _build_coaching_brief(member_lines, mode_hint=mode),
            confidence=0.91,
            used_ctx=[*used_ctx, "history:coaching_followup"],
            suggested_actions=["Ask for a radio callout plan or objective assignments."],
        )

    if re.search(r"\bmarshal\b|\bbriefing\b", lower):
        mode = ctx.get("available_game_modes", [None])[0] if ctx["available_game_modes"] else None
        answer = (
            f"**Marshal Briefing Checklist{f' — {mode}' if mode else ''}:**\n\n"
            "1. **Safety** — sealed eye protection at all times in active zones; full-face for CQB, beginners, minors, and rental players\n"
            "2. **Chrono** — all guns tagged after passing; adults ≤0.98 J, under-18 ≤0.135 J, or venue CQB cap (whichever is lower)\n"
            "3. **Close-range rule** — state the venue policy: self-hit, courtesy surrender, or hard MED\n"
            "4. **Hit calls** — loud verbal call, hand up, dead rag on; no disputing hits — marshal ruling is final\n"
            "5. **No blind fire** — muzzle must follow line of sight at all times\n"
            "6. **Field boundaries** — brief all zone limits and spectator areas\n"
            "7. **Emergency halt** — universal phrase 'CODE RED, ALL STOP'; all marshals must know and repeat this\n"
            "8. **AED location** — confirm with all marshals before play begins\n"
            "9. **Radio check** — all marshals on ch.1 before game start\n"
            "10. **Dispute protocol** — pause play, marshal decision is final, no player-enforced arguments\n\n"
            "Ready to print? I can format this as a full briefing card, or add the Japan chrono procedure."
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

    if _is_true_greeting(text):
        state = ctx["game_state"]
        r, b = ctx["red_score"], ctx["blue_score"]
        status_line = ""
        if state == "running":
            status_line = f"\n\nCurrent game: **running** — Red {r} / Blue {b}, {_fmt_timer(ctx['timer_seconds'])} remaining."
        elif state == "paused":
            status_line = f"\n\nCurrent game: **paused** — Red {r} / Blue {b}."
        answer = (
            "Hi! I'm Christy, your AOJ field advisor for airsoft events in Japan. Here's what I can help with:\n\n"
            "- **Live data** — 'what's the score?', 'how long is left?', 'which devices are offline?'\n"
            "- **Game suggestions** — 'suggest a game for 16 players on a 4000m² field'\n"
            "- **Rule sets** — 'build VIP escort rules for 20 players, 25 minutes'\n"
            "- **Japan safety & chrono** — 'what are the chrono rules?', 'what's the power limit for minors?'\n"
            "- **Legal guidance** — 'how do I classify a replica?', 'what are import rules?'\n"
            "- **Heat & emergency** — 'what are the WBGT thresholds?', 'give me the 119 protocol'\n"
            "- **Event operations** — 'how do I plan an event?', 'how many staff do I need?'\n"
            "- **Marshal briefings** — 'generate a marshal briefing'\n"
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
        # Better general fallback: answer conversationally instead of always forcing AOJ menus.
        topic = _topic_hint_from_text(lower)
        if topic == "loadout":
            answer = _airsoft_loadout_advice(nums.get("players"))
        elif topic == "tactics":
            answer = _airsoft_tactics_advice(ctx.get("mission_title"))
        elif topic == "safety":
            answer = _airsoft_safety_advice()
        elif topic == "legal":
            answer = _build_compliance_clarification(text) if _needs_compliance_clarification(text) else _japan_legal_advice()
        else:
            answer = (
                "I can help with that. Give me the objective and any limits — for example player count, field, time, device involved, or the exact question — and I’ll give you a direct answer."
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
    prompt = (prompt or "").strip()
    if not prompt:
        return _mk_response("Ready. What do you need?", confidence=0.9, used_ctx=["advisor:empty_prompt"])

    # Fast-path common requests for lower latency and higher consistency.
    # This keeps conversational UX snappy for greeting/identity/game-selection prompts.
    lower = prompt.lower()
    nums = _extract_numbers(lower)
    if (
        not OLLAMA_STRICT
        and (
            _detect_response_mode(prompt) == "casual"
            or re.search(r"\b(what(?:'s| is) your name|who are you)\b", lower)
            or _is_game_suggestion_request(lower, nums)
        )
    ):
        return _handle_conversation(
            prompt=prompt,
            history=history,
            injected_context=injected_context,
        )

    # ------------------------------------------------------------------
    # Attempt Ollama (re-check once per cold start, then cache result)
    # ------------------------------------------------------------------
    global _ollama_available, _ollama_model
    if _ollama_available is None:
        _check_ollama()

    if OLLAMA_STRICT and not _ollama_available:
        return _mk_response(
            (
                "Ollama is required but currently unavailable. "
                "Please start Ollama and ensure at least one model is installed."
            ),
            confidence=0.1,
            used_ctx=["advisor:ollama_required", "provider:ollama_unavailable"],
            warnings=["OLLAMA_STRICT is enabled and fallback provider is disabled."],
            model="ollama-required",
        )

    if _ollama_available:
        llm_answer = _ollama_chat(
            prompt=prompt,
            context=injected_context,
            history=history,
            model=_ollama_model,
        )
        if llm_answer:
            return _handle_ollama_response(
                prompt=prompt,
                llm_answer=llm_answer,
                history=history,
                injected_context=injected_context,
                model=_ollama_model or "unknown",
            )
        # Ollama request failed at runtime — retry on next request instead of
        # permanently disabling it for this process.
        if OLLAMA_STRICT:
            return _mk_response(
                "Ollama request failed. Fallback is disabled in strict mode.",
                confidence=0.1,
                used_ctx=["advisor:ollama_required", "provider:ollama_error"],
                warnings=["OLLAMA_STRICT is enabled and fallback provider is disabled."],
                model="ollama-required",
            )
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
