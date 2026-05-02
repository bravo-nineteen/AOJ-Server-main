"""AI advisory module – conversational advisor with game suggestion engine."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.ai import AIAskResponse

MOCK_MODEL_NAME = "mock-local-advisor-v1"

SAFETY_NOTICE = (
    "Advisory mode active. I will ask for your confirmation before any operational action."
)

# Patterns that indicate the user is confirming a previous request.
_CONFIRM_PATTERNS = re.compile(
    r"\b(yes|yeah|confirm|confirmed|proceed|go ahead|do it|approved|affirmative|ok|okay)\b",
    re.IGNORECASE,
)

# Hardware/state-mutation actions that need a confirm step.
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

# Number extraction helpers for game suggestions.
_NUM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d+)\s*(?:players?|people|participants?|persons?)", re.I), "players"),
    (re.compile(r"(\d+)\s*(?:per\s*team|a\s*side|each\s*team)", re.I), "per_team"),
    (re.compile(r"(?:field|area|site)\s*(?:is\s*)?(\d+)\s*(?:m|meters?|metres?|acres?|hectares?|sqm|sq\s*m)", re.I), "field_m"),
    (re.compile(r"(\d+)\s*(?:m|meters?|metres?|acres?|hectares?)\s*(?:field|area|site|large|wide|big|small)", re.I), "field_m"),
    (re.compile(r"(?:handicap|advantage|bias)\s*(?:of\s*)?(\d+)\s*(?:%|percent|points?)", re.I), "handicap_pct"),
    (re.compile(r"(\d+)\s*(?:min(?:utes?)?|hrs?|hours?)\s*(?:time|limit|available|to\s*play)", re.I), "minutes"),
]


def _extract_numbers(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for pattern, key in _NUM_PATTERNS:
        m = pattern.search(text)
        if m:
            result[key] = int(m.group(1))
    return result


def _detect_operational_action(text: str) -> tuple[str | None, str | None]:
    """Return (action_key, human_label) if text contains an operational command."""
    human_labels = {
        "start_game": "start the game/mission",
        "end_game": "end the game/mission",
        "pause_resume_game": "pause or resume the game",
        "arm_disarm_device": "arm or disarm a device",
        "reset_device": "reset a device/system",
        "trigger_device": "trigger a prop/alarm",
        "system_power": "shut down or reboot the system",
        "adjust_score": "adjust team scores",
    }
    for pattern, key in _OPERATIONAL_PATTERNS:
        if pattern.search(text):
            return key, human_labels.get(key, key)
    return None, None


def _check_history_for_pending_confirmation(history: list[dict[str, Any]]) -> str | None:
    """
    Look back through history: if the last assistant message contained a confirmation
    request for a specific action, return that action key so we can proceed.
    """
    if not history:
        return None
    for entry in reversed(history):
        if entry.get("role") == "assistant":
            content = entry.get("content", "")
            # Look for our confirmation tag embedded in previous response.
            m = re.search(r"\[CONFIRM_ACTION:([^\]]+)\]", content)
            if m:
                return m.group(1)
            break
    return None


def _suggest_game(players: int | None, field_m: int | None, handicap_pct: int | None,
                  minutes: int | None, available_modes: list[str] | None) -> str:
    """
    Return a tailored game mode suggestion based on operational parameters.
    """
    lines: list[str] = []

    # Determine game category
    p = players or 0
    f = field_m or 0
    h = handicap_pct or 0
    t = minutes or 20

    if p == 0:
        lines.append(
            "To give you the best suggestion I'll need a bit more info — "
            "how many players do you have and roughly how large is your field? "
            "For example: 'We have 20 players, field is 5000m²'"
        )
        return "\n".join(lines)

    # Size category
    per_team = p // 2
    if f > 0:
        sqm_per_player = f / max(p, 1)
    else:
        sqm_per_player = 250  # assume medium

    # Pick mode type
    if p <= 8:
        mode_style = "close-quarters, fast-paced"
        recommendations = ["Skirmish", "Capture The Flag", "King of the Hill"]
        rule_note = "Keep rounds short (10–15 min) with a 3-min respawn delay."
    elif p <= 20:
        mode_style = "medium-team tactical"
        recommendations = ["Domination", "Capture Point", "NoCode Assault"]
        rule_note = "Suggest 2 objectives minimum. 20-min rounds work well."
    else:
        mode_style = "large-force strategic"
        recommendations = ["Hostage Rescue", "Domination", "No-Code Siege"]
        rule_note = "Use 3+ objectives and a 30-min session with a 1-min respawn limit."

    # Overlay available custom modes
    if available_modes:
        for mode in available_modes:
            for rec in recommendations:
                if rec.lower() in mode.lower() or mode.lower() in rec.lower():
                    recommendations[recommendations.index(rec)] = mode

    # Handicap adjustment
    handicap_note = ""
    if h > 0:
        if h >= 30:
            handicap_note = (
                f" To compensate for the {h}% team size/skill advantage, "
                "give the weaker team a 2-point head-start and restrict respawns for the stronger team."
            )
        else:
            handicap_note = (
                f" With a {h}% handicap, consider giving the smaller/weaker team "
                "an extra 10 points at game start or one extra respawn ticket."
            )

    lines.append(
        f"Based on **{p} players** ({per_team} per team), "
        + (f"**{f} m²** field, " if f else "")
        + f"**{t} min** sessions — here are my recommendations:"
    )
    lines.append("")
    for i, mode in enumerate(recommendations[:3], 1):
        lines.append(f"{i}. **{mode}**")
    lines.append("")
    lines.append(f"Style: {mode_style}.{handicap_note}")
    lines.append(f"Rule tip: {rule_note}")
    lines.append("")
    lines.append(
        "Want me to build out the full rule set for any of these? "
        "Just say which one and I'll draft objectives, timers, and scoring."
    )
    return "\n".join(lines)


def _build_game_mode_rules(mode_name: str, players: int | None, minutes: int | None) -> str:
    """Draft a full rule set for a requested game mode."""
    p = players or 10
    t = minutes or 20
    per_team = p // 2

    templates: dict[str, str] = {
        "skirmish": (
            f"**Skirmish – {p} players, {t} min**\n"
            f"- Teams: {per_team} vs {per_team}\n"
            "- Objective: Most eliminations wins\n"
            "- Respawn: Unlimited, 1-min delay at base\n"
            "- Scoring: 1 point per elimination, 5 point bonus for last-team-standing\n"
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
    }
    key = mode_name.lower().strip()
    for template_key, content in templates.items():
        if template_key in key or key in template_key:
            return content

    # Generic fallback
    return (
        f"**{mode_name} – {p} players, {t} min**\n"
        f"- Teams: {per_team} vs {per_team}\n"
        "- Objective: Complete the primary objective before time expires\n"
        "- Respawn: 1-min cooldown at designated respawn zone\n"
        "- Scoring: Objective completion = 5 points, elimination = 1 point\n"
        "- Win: Highest score at end of round\n\n"
        "Let me know if you want to customise any rules (timers, scoring, respawn rules)."
    )


def _handle_conversation(
    prompt: str,
    history: list[dict[str, Any]],
    injected_context: str | None,
) -> AIAskResponse:
    """Main conversational response handler."""
    text = prompt.strip()
    lower = text.lower()
    nums = _extract_numbers(lower)

    used_ctx: list[str] = ["advisor:conversational", "provider:mock-local"]
    if injected_context:
        used_ctx.append("context:injected")

    # --- Operational command flow ---
    action_key, action_label = _detect_operational_action(text)
    pending = _check_history_for_pending_confirmation(history)

    if action_key:
        is_confirm = bool(_CONFIRM_PATTERNS.search(lower))
        if is_confirm and pending == action_key:
            # User confirmed — provide action guidance
            answer = (
                f"Confirmed. Here's the procedure to **{action_label}**:\n\n"
                + _action_guidance(action_key)
            )
            return AIAskResponse(
                answer=answer,
                confidence=0.88,
                used_context=[*used_ctx, "advisor:confirmed_action"],
                suggested_actions=[f"Proceed with: {action_label}"],
                blocked_actions=[],
                warnings=[],
                advisory_only=True,
                requires_admin_confirmation=False,
                blocked_action=False,
                safety_notice=SAFETY_NOTICE,
                model=MOCK_MODEL_NAME,
            )
        else:
            # Ask for confirmation
            answer = (
                f"I can help you **{action_label}**. "
                "Before I guide you through this, can you confirm that's what you want to do?\n\n"
                f"Reply **yes** or **confirm** to proceed, or tell me more about what you need.\n\n"
                f"[CONFIRM_ACTION:{action_key}]"
            )
            return AIAskResponse(
                answer=answer,
                confidence=0.75,
                used_context=[*used_ctx, "advisor:awaiting_confirmation"],
                suggested_actions=["Confirm the action to proceed."],
                blocked_actions=[],
                warnings=[],
                advisory_only=True,
                requires_admin_confirmation=True,
                blocked_action=False,
                safety_notice=SAFETY_NOTICE,
                model=MOCK_MODEL_NAME,
            )

    # If user says "yes/confirm" but there's no pending action
    if _CONFIRM_PATTERNS.match(lower) and len(lower.split()) <= 3:
        if pending:
            answer = (
                f"Confirmed. Here's the procedure:\n\n"
                + _action_guidance(pending)
            )
            return AIAskResponse(
                answer=answer, confidence=0.88,
                used_context=[*used_ctx, "advisor:confirmed_action"],
                suggested_actions=[], blocked_actions=[], warnings=[],
                advisory_only=True, requires_admin_confirmation=False,
                blocked_action=False, safety_notice=SAFETY_NOTICE, model=MOCK_MODEL_NAME,
            )
        answer = "Got it! What would you like me to help with?"
        return AIAskResponse(
            answer=answer, confidence=0.9,
            used_context=used_ctx, suggested_actions=[], blocked_actions=[], warnings=[],
            advisory_only=True, requires_admin_confirmation=False,
            blocked_action=False, safety_notice=SAFETY_NOTICE, model=MOCK_MODEL_NAME,
        )

    # --- Game suggestion flow ---
    is_game_suggest = re.search(
        r"\b(suggest|recommend|what.{0,10}game|which.{0,10}game|best\s+game|pick\s+a\s+game|help.{0,10}choose)\b",
        lower,
    )
    is_build_mode = re.search(
        r"\b(build|create|draft|write|make|design)\b.{0,20}\b(game mode|ruleset|rules|mode)\b",
        lower,
    )
    is_detail_request = re.search(
        r"\b(rules?|full|details?|set\s*up|setup|how\s+to\s+play)\b.{0,20}\b(skirmish|domination|capture|king|flag|hill|assault|siege|hostage)\b",
        lower,
    )

    # Extract available modes from injected context
    available_modes: list[str] = []
    if injected_context:
        for line in injected_context.splitlines():
            if "game mode" in line.lower() and ":" in line:
                mode = line.split(":", 1)[-1].strip().strip("-").strip()
                if mode and len(mode) < 60:
                    available_modes.append(mode)

    # Pull context from previous turns for player/field numbers
    if injected_context:
        ctx_nums = _extract_numbers(injected_context.lower())
        for k, v in ctx_nums.items():
            if k not in nums:
                nums[k] = v

    if is_game_suggest:
        answer = _suggest_game(
            players=nums.get("players") or (nums.get("per_team", 0) * 2) or None,
            field_m=nums.get("field_m"),
            handicap_pct=nums.get("handicap_pct"),
            minutes=nums.get("minutes"),
            available_modes=available_modes or None,
        )
        return AIAskResponse(
            answer=answer, confidence=0.86,
            used_context=[*used_ctx, "advisor:game_suggestion"],
            suggested_actions=["Choose a game mode from the list and I'll build the full rule set."],
            blocked_actions=[], warnings=[],
            advisory_only=True, requires_admin_confirmation=False,
            blocked_action=False, safety_notice=SAFETY_NOTICE, model=MOCK_MODEL_NAME,
        )

    if is_detail_request or is_build_mode:
        # Find which mode they're asking about
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
        return AIAskResponse(
            answer=answer, confidence=0.9,
            used_context=[*used_ctx, "advisor:game_mode_builder"],
            suggested_actions=["Save this mode in Admin > Game Modes to use it in Mission Control."],
            blocked_actions=[], warnings=[],
            advisory_only=True, requires_admin_confirmation=False,
            blocked_action=False, safety_notice=SAFETY_NOTICE, model=MOCK_MODEL_NAME,
        )

    # --- Quick prompts ---
    if re.search(r"\bsummariz[e|ing]\b|\bresults\b", lower):
        answer = (
            "Here's a results summary template:\n\n"
            "- **Winner:** [Team name] by [score delta] points\n"
            "- **Final score:** Red [X] — Blue [Y]\n"
            "- **Penalties applied:** [list]\n"
            "- **Fairness note for next round:** [e.g. rotate starting sides]\n"
            "- **Tactical tip — Red:** [one improvement]\n"
            "- **Tactical tip — Blue:** [one improvement]\n\n"
            "Want me to fill this in with the current session data?"
        )
    elif re.search(r"\bmarshal\b|\bbriefing\b", lower):
        answer = (
            "**Marshal Briefing Checklist:**\n\n"
            "1. Safety priorities — hit calls, eye protection mandatory\n"
            "2. Rule reminders — no blind firing, boundaries, mercy rule\n"
            "3. Objective flow — explain win conditions clearly\n"
            "4. Dispute protocol — pause play, marshal ruling is final\n"
            "5. Emergency halt phrase — 'CODE RED, ALL STOP'\n"
            "6. Radio channel check — confirm all marshals on ch.1\n"
            "7. First aid point location\n\n"
            "Ready to print? I can format this as a formatted briefing card."
        )
    elif re.search(r"\bprop\b|\bdevice\b|\bsensor\b|\boffline\b", lower):
        answer = (
            "**Device/Prop Diagnostic Flow:**\n\n"
            "1. Check battery level (>20% required)\n"
            "2. Verify LoRa signal strength\n"
            "3. Confirm last-seen timestamp — if >5 min, investigate\n"
            "4. Run a status ping from Prop Network\n"
            "5. Check firmware version matches other props\n"
            "6. Isolate by moving closer to gateway if signal is low\n\n"
            "Which device is having issues? I can pull its last known state."
        )
    elif re.search(r"\bschedule\b|\bdelay\b|\brunning\s+late\b", lower):
        answer = (
            "**Delay Recovery Plan:**\n\n"
            "- Cut break time by 5 min\n"
            "- Tighten briefing to key rules only (skip examples)\n"
            "- Move non-critical announcements to post-round\n"
            "- Compress game to {t} min if needed\n\n"
            "How far behind are you? I can adjust the full schedule."
        )
    elif re.search(r"\bannouncement\b|\bteam\s+message\b|\bbroadcast\b", lower):
        answer = (
            "**Team Announcement Draft:**\n\n"
            "> 'Attention all players — next mission begins in 10 minutes. "
            "Report to your assigned staging lane, confirm radio is on channel 1, "
            "and await marshal signal. Any questions, see the duty marshal now.'\n\n"
            "Want me to customise this with team names and objective details?"
        )
    elif re.search(r"\b(hello|hi|hey|howdy|good morning|good afternoon|what can you do|help)\b", lower):
        answer = (
            "Hi! I'm your AOJ field advisor. Here's what I can help with:\n\n"
            "- **Game suggestions** — tell me player count and field size\n"
            "- **Rule sets** — ask me to build a mode like 'draft domination rules for 20 players'\n"
            "- **Marshal briefings** — 'generate a marshal briefing'\n"
            "- **Results summaries** — 'summarize today's results'\n"
            "- **Device diagnostics** — 'prop X is offline'\n"
            "- **Operational actions** — start/stop/reset (I'll ask you to confirm first)\n\n"
            "What are we working on today?"
        )
    elif re.search(r"\bwhat.{0,10}(learn|know|remember|remember)\b", lower):
        # Respond with learned context from conversation
        memory_lines: list[str] = []
        if injected_context:
            for line in injected_context.splitlines():
                if "LEARNED:" in line or "TRENDS:" in line or "MEMORY" in line:
                    memory_lines.append(line.strip())
        if memory_lines:
            answer = "Here's what I've picked up from our conversation:\n\n" + "\n".join(memory_lines[:6])
        else:
            answer = "I'm still learning from our conversation. The more you tell me about your field setup, teams, and game preferences, the better my suggestions get!"
    elif re.search(r"\b(handicap|imbalance|uneven|disadvantage|advantage)\b", lower):
        h = nums.get("handicap_pct", 0)
        answer = (
            f"**Handling Team Imbalance{f' ({h}% handicap)' if h else ''}:**\n\n"
            "Options to balance the game:\n"
            "1. **Point head-start** — weaker team starts with 5–10 points\n"
            "2. **Extra respawn tickets** — weaker team gets +1 life per round\n"
            "3. **Objective advantage** — weaker team starts with one objective captured\n"
            "4. **Restricted loadout** — stronger team uses pistols only first 5 min\n"
            "5. **Field advantage** — weaker team starts closer to key objectives\n\n"
            "Which would you like to apply? I can adjust the scoring rules accordingly."
        )
    else:
        # General fallback — use context if available
        if injected_context and len(injected_context) > 100:
            answer = (
                "I'm looking at your current field data. "
                "Based on the active context, everything looks nominal. "
                "I can help with game suggestions, rule sets, briefings, diagnostics, or schedule management. "
                "What do you need?"
            )
        else:
            answer = (
                "I'm your AOJ field advisor, ready to help. "
                "Try asking me to suggest a game, build a rule set, or generate a briefing. "
                "For example: 'suggest a game for 16 players on a 4000m² field'."
            )

    return AIAskResponse(
        answer=answer,
        confidence=0.85,
        used_context=used_ctx,
        suggested_actions=[],
        blocked_actions=[],
        warnings=[],
        advisory_only=True,
        requires_admin_confirmation=False,
        blocked_action=False,
        safety_notice=SAFETY_NOTICE,
        model=MOCK_MODEL_NAME,
    )


def _action_guidance(action_key: str) -> str:
    """Return step-by-step guidance for a confirmed operational action."""
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


def ask_ai(
    prompt: str,
    injected_context: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> AIAskResponse:
    """Entry point for the conversational advisor."""
    return _handle_conversation(
        prompt=prompt,
        history=conversation_history or [],
        injected_context=injected_context,
    )
