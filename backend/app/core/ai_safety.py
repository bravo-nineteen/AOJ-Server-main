import re
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_POLICY_NAME = "advisory_only_v1"

_INTENT_RULES: list[tuple[str, str, bool]] = [
    # action: starting games (unsafe)
    (r"\b(start|resume|launch)\b.*\b(game|session|mission)\b|\bstart\s+the\s+next\s+game\b", "START_GAME_SESSION", True),
    # action: ending games (unsafe)
    (r"\b(end|stop|finish|terminate)\b.*\b(game|session|mission)\b", "END_GAME_SESSION", True),
    # action: adjusting scores (unsafe)
    (r"\b(adjust|update|change|set|add|deduct)\b.*\b(score|points?)\b", "ADJUST_TEAM_SCORE", True),
    # action: investigating device issues (advisory)
    (r"\b(investigate|diagnose|check|troubleshoot|debug)\b.*\b(device|prop|sensor|radio|lora)\b", "INVESTIGATE_DEVICE_ISSUE", False),
    # action: schedule delays (advisory)
    (r"\b(schedule\s+delay|delay(ed)?\s+schedule|running\s+late|behind\s+schedule)\b", "HANDLE_SCHEDULE_DELAY", False),
    # explicit hardware/system control (unsafe)
    (r"\barm\b", "ARM_DEVICE", True),
    (r"\bdisarm\b", "DISARM_DEVICE", True),
    (r"\btrigger(?:\s+alarm)?\b", "TRIGGER_ALARM", True),
    (r"\breset\b", "RESET_DEVICE", True),
    (r"\b(shutdown|reboot|restart)\b", "SYSTEM_POWER_CONTROL", True),
]


@dataclass
class AISafetyDecision:
    policy_name: str
    requires_admin_confirmation: bool
    blocked_actions: list[str]
    suggested_actions: list[str]
    used_context: list[str]
    risk_level: str
    confidence: float


@dataclass
class AIActionValidation:
    allowed: bool
    reason: str | None = None


def evaluate_ai_prompt(prompt: str) -> AISafetyDecision:
    text = prompt.strip().lower()
    suggested_actions: list[str] = []
    blocked: list[str] = []

    for pattern, action, unsafe in _INTENT_RULES:
        if re.search(pattern, text):
            suggested_actions.append(action)
            if unsafe:
                blocked.append(action)

    # De-duplicate while preserving order.
    suggested_actions = list(dict.fromkeys(suggested_actions))
    blocked = list(dict.fromkeys(blocked))

    requires_admin_confirmation = len(blocked) > 0
    if requires_admin_confirmation:
        risk_level = "high"
        confidence = 0.45
    elif suggested_actions:
        risk_level = "medium"
        confidence = 0.74
    else:
        risk_level = "low"
        confidence = 0.82

    if requires_admin_confirmation:
        suggested_actions = list(
            dict.fromkeys(
                [
                    *suggested_actions,
                    "ADMIN_CONFIRMATION_REQUIRED",
                    "VERIFY_SAFETY_CONSTRAINTS",
                ]
            )
        )

    return AISafetyDecision(
        policy_name=_POLICY_NAME,
        requires_admin_confirmation=requires_admin_confirmation,
        blocked_actions=blocked,
        suggested_actions=suggested_actions,
        used_context=[f"policy:{_POLICY_NAME}"],
        risk_level=risk_level,
        confidence=confidence,
    )


class AIPolicy:
    def __init__(self, policy_name: str) -> None:
        self.policy_name = policy_name

    def validate_ai_action(self, action: str, requires_admin_confirmation: bool) -> AIActionValidation:
        action_text = action.strip()
        if not action_text:
            return AIActionValidation(allowed=True)

        upper = action_text.upper()
        lower = action_text.lower()

        is_prop_command = (
            any(token in upper for token in ["ARM_DEVICE", "DISARM_DEVICE", "TRIGGER_ALARM", "RESET_DEVICE", "SYSTEM_POWER_CONTROL"])
            or any(token in lower for token in ["arm", "disarm", "trigger", "reset", "shutdown", "reboot", "restart"])
            and any(token in lower for token in ["prop", "device", "sensor", "radio", "lora", "alarm"])
        )
        is_mission_state_change = (
            any(token in upper for token in ["START_GAME_SESSION", "END_GAME_SESSION", "MISSION_STATE_CHANGE"])
            or ("mission" in lower or "session" in lower or "game" in lower)
            and any(token in lower for token in ["start", "resume", "launch", "end", "stop", "finish", "terminate", "pause"])
        )
        is_score_change = (
            "ADJUST_TEAM_SCORE" in upper
            or ("score" in lower or "point" in lower)
            and any(token in lower for token in ["adjust", "update", "change", "set", "add", "deduct"])
        )

        if (is_prop_command or is_mission_state_change or is_score_change) and not requires_admin_confirmation:
            return AIActionValidation(
                allowed=False,
                reason=(
                    "Action requires admin confirmation under advisory-only policy "
                    "(prop command, mission state change, or score change)."
                ),
            )

        return AIActionValidation(allowed=True)


ai_policy = AIPolicy(_POLICY_NAME)


class AISafetyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/ai"):
            request.state.ai_policy = _POLICY_NAME
            request.state.ai_mode = "advisory-only"

        response = await call_next(request)

        if request.url.path.startswith("/api/ai"):
            response.headers["X-AI-Safety-Policy"] = _POLICY_NAME
            response.headers["X-AI-Mode"] = "advisory-only"

        return response
