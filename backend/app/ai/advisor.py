"""AI advisory module – mock advisor with restricted-term detection."""

import re

from app.schemas.ai import AIAskResponse

MOCK_MODEL_NAME = "mock-local-advisor-v1"

SAFETY_NOTICE = (
    "Advisory only. No hardware command is executed. "
    "Admin confirmation is required before any operational action."
)

RESTRICTED_TERMS = {
    "arm",
    "disarm",
    "start",
    "stop",
    "reset",
    "trigger",
    "activate",
    "deactivate",
}


def ask_ai(prompt: str) -> AIAskResponse:
    text = prompt.strip()
    lower = text.lower()

    restricted_detected = any(
        re.search(r"\b" + re.escape(term) + r"\b", lower)
        for term in RESTRICTED_TERMS
    )

    if restricted_detected:
        answer = (
            "I can advise on procedure, risk checks, and confirmation steps, but I cannot "
            "directly execute or authorize hardware actions. Request explicit admin "
            "confirmation before any prop or mission control command."
        )
        return AIAskResponse(
            answer=answer,
            advisory_only=True,
            requires_admin_confirmation=True,
            blocked_action=True,
            safety_notice=SAFETY_NOTICE,
            model=MOCK_MODEL_NAME,
        )

    if "suggest next game" in lower:
        answer = (
            "Recommended next game: Domination with 2 control points and a 20-minute limit. "
            "Use a 5-minute setup window and start with neutral points to reduce spawn bias."
        )
    elif "summarize results" in lower:
        answer = (
            "Summary template: highlight winner, score delta, penalties applied, and one "
            "fairness note for the next round. Include one tactical improvement per team."
        )
    elif "marshal briefing" in lower:
        answer = (
            "Marshal briefing draft: 1) safety priorities, 2) rule reminders, 3) objective "
            "flow, 4) dispute protocol, 5) emergency halt phrase, 6) radio channel checks."
        )
    elif "prop issue" in lower:
        answer = (
            "Prop issue diagnostic flow: check battery and signal first, confirm last seen, "
            "run status request, then isolate by location and firmware version mismatch."
        )
    elif "schedule delay" in lower:
        answer = (
            "Delay recovery recommendation: cut break by 5 minutes, tighten briefing to key "
            "rules only, and move non-critical announcements post-round."
        )
    elif "team announcement" in lower:
        answer = (
            "Team announcement draft: 'Command update: next mission begins in 10 minutes. "
            "Report to assigned staging lanes, confirm radios, and await marshal signal.'"
        )
    else:
        answer = (
            "Mock AI advisor is active. I can provide planning support, diagnostics guidance, "
            "and communication drafts. I do not execute hardware or mission commands."
        )

    return AIAskResponse(
        answer=answer,
        advisory_only=True,
        requires_admin_confirmation=False,
        blocked_action=False,
        safety_notice=SAFETY_NOTICE,
        model=MOCK_MODEL_NAME,
    )
