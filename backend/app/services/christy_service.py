"""Christy proactive announcement service.

Runs as a background asyncio task alongside the mission control ticker.
Monitors game state transitions and generates Christy announcements that are
broadcast to all connected WebSocket clients as `christy.announcement` events.

The Ollama LLM is used for rich announcement text when available; a built-in
template set provides instant fallback.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


CHRISTY_PROACTIVE_ENABLED = _env_bool("AOJ_CHRISTY_PROACTIVE", default=False)

# ---------------------------------------------------------------------------
# Built-in announcement templates (used when Ollama is unavailable)
# ---------------------------------------------------------------------------

_GAME_END_TEMPLATES = [
    "Game over! {winner} takes the win with {win_score} to {lose_score}. Outstanding performance out there — great game from both sides.",
    "That's a wrap! {winner} wins {win_score} to {lose_score}. Well played by everyone. Ready to run it back?",
    "Mission complete! {winner} secures the victory, {win_score} to {lose_score}. Rest up and hydrate — next brief is coming.",
]

_MODE_SUGGESTION_TEMPLATES = [
    "Looking for something fresh? Consider a round of King of the Hill — fast-paced, intense, and great for smaller squads.",
    "Have you tried Hostage Rescue recently? It's a solid format when you have uneven team sizes — the defender/attacker split adds great tension.",
    "Domination is perfect when you want extended engagements. Great for larger fields with defined capture zones.",
    "For a quick intense session, a Skirmish with a 20-minute timer keeps everyone focused and moving. Short, sharp, and satisfying.",
]

_GAME_START_TEMPLATES = [
    "Mission is live! Stay sharp, communicate with your team, and keep your objectives in sight. Good luck to everyone.",
    "Game on! Both teams are active. Eyes open, stay low, and play smart. Let's have a clean game.",
    "We're rolling! Mission clock is running. Command is watching the board — keep those objectives moving.",
]

_SCORE_LEAD_TEMPLATES = [
    "{team} has pulled ahead {score_a} to {score_b}! {trailing} — keep the pressure on and fight back.",
    "Score update: {team} leads {score_a} to {score_b}. {trailing} — time to regroup and push.",
]


# ---------------------------------------------------------------------------
# Christy Proactive Service
# ---------------------------------------------------------------------------

class ChristyProactiveService:
    """Watches game state and emits proactive announcements via WebSocket."""

    def __init__(self) -> None:
        self._last_game_state: str = "idle"
        self._last_red_score: int = 0
        self._last_blue_score: int = 0
        self._last_mission_id: int | None = None
        self._score_announce_cooldown: int = 0   # ticks until next score lead announce
        self._mode_suggest_cooldown: int = 0     # ticks until next mode suggestion

    async def ticker(self) -> None:
        """Run every 30 seconds, checking for state changes to announce."""
        # Small initial delay to let the server start fully
        await asyncio.sleep(10)

        while True:
            try:
                await self._check_and_announce()
            except asyncio.CancelledError:
                logger.info("Christy service cancelled")
                raise
            except Exception as e:
                logger.exception("Christy proactive ticker error: %s", str(e))
            await asyncio.sleep(30)

    async def _check_and_announce(self) -> None:
        """Compare current mission state against last-known state and broadcast."""
        if not CHRISTY_PROACTIVE_ENABLED:
            return

        # Lazy import to avoid circular deps at module load time
        from app.services.mission_control_service import mission_control_service
        from app.core.websocket import websocket_manager

        if websocket_manager.connected_count == 0:
            return  # No one listening — skip

        state = mission_control_service.get_state()
        current_state = state.get("state", "idle")
        red = state.get("red_team_score", 0)
        blue = state.get("blue_team_score", 0)
        mission_id = state.get("mission_id")

        # ---------------------------------------------------------------
        # Game just started
        # ---------------------------------------------------------------
        if current_state == "running" and self._last_game_state != "running":
            text = random.choice(_GAME_START_TEMPLATES)
            await self._broadcast(websocket_manager, text, "game_start")

        # ---------------------------------------------------------------
        # Game just ended
        # ---------------------------------------------------------------
        elif current_state == "ended" and self._last_game_state in ("running", "paused"):
            text = await self._generate_game_end_text(state, red, blue)
            await self._broadcast(websocket_manager, text, "game_end")
            # After a game ends, suggest a next mode after a short delay
            self._mode_suggest_cooldown = 4  # announce in ~2 min

        # ---------------------------------------------------------------
        # Score lead change announcement (every ~5 min max)
        # ---------------------------------------------------------------
        elif current_state == "running" and self._score_announce_cooldown <= 0:
            if red != blue and (red > 0 or blue > 0):
                if abs(red - blue) >= 2:  # only announce if lead >= 2
                    leading = "Red Team" if red > blue else "Blue Team"
                    trailing = "Blue Team" if red > blue else "Red Team"
                    lead_s, trail_s = (red, blue) if red > blue else (blue, red)
                    tmpl = random.choice(_SCORE_LEAD_TEMPLATES)
                    text = tmpl.format(
                        team=leading, score_a=lead_s, score_b=trail_s, trailing=trailing
                    )
                    await self._broadcast(websocket_manager, text, "score_update")
                    self._score_announce_cooldown = 10  # ~5 min cooldown

        # ---------------------------------------------------------------
        # Periodic mode suggestion (only when idle)
        # ---------------------------------------------------------------
        if current_state == "idle" and self._mode_suggest_cooldown <= 0:
            # Only suggest occasionally — approximately every 10 minutes of idle time
            if random.random() < 0.15:
                text = await self._generate_mode_suggestion(state)
                if text:
                    await self._broadcast(websocket_manager, text, "mode_suggestion")
                    self._mode_suggest_cooldown = 20

        # ---------------------------------------------------------------
        # Decrement cooldowns
        # ---------------------------------------------------------------
        if self._score_announce_cooldown > 0:
            self._score_announce_cooldown -= 1
        if self._mode_suggest_cooldown > 0:
            self._mode_suggest_cooldown -= 1

        # Save state for next tick
        self._last_game_state = current_state
        self._last_red_score = red
        self._last_blue_score = blue
        self._last_mission_id = mission_id

    async def _generate_game_end_text(self, state: dict, red: int, blue: int) -> str:
        """Try Ollama for a rich end-of-game summary; fall back to template."""
        from app.ai.advisor import _ollama_available, _ollama_model, _ollama_chat

        if _ollama_available and _ollama_model:
            game_mode = state.get("game_mode", "Skirmish")
            winner = "Red Team" if red > blue else ("Blue Team" if blue > red else "neither team")
            prompt = (
                f"The {game_mode} game just ended. Red Team scored {red}, Blue Team scored {blue}. "
                f"{winner.title()} won. Write a brief, exciting 2-sentence end-of-game announcement "
                f"as Christy the AOJ field advisor. Keep it natural — no markdown."
            )
            result = _ollama_chat(prompt, None, [], _ollama_model)
            if result:
                return result

        # Fallback template
        if red == blue:
            return f"Game over — it's a draw! Both teams finished at {red} each. What a match!"
        winner = "Red Team" if red > blue else "Blue Team"
        win_s, lose_s = (red, blue) if red > blue else (blue, red)
        tmpl = random.choice(_GAME_END_TEMPLATES)
        return tmpl.format(winner=winner, win_score=win_s, lose_score=lose_s)

    async def _generate_mode_suggestion(self, state: dict) -> str | None:
        """Occasionally suggest a game mode. Returns None to skip."""
        from app.ai.advisor import _ollama_available, _ollama_model, _ollama_chat

        if _ollama_available and _ollama_model:
            prompt = (
                "Give a brief one-sentence suggestion for a fun airsoft game mode to try today. "
                "Keep it natural and friendly — no markdown, no lists."
            )
            result = _ollama_chat(prompt, None, [], _ollama_model)
            if result:
                return result

        return random.choice(_MODE_SUGGESTION_TEMPLATES)

    @staticmethod
    async def _broadcast(manager: Any, text: str, event_type: str) -> None:
        """Broadcast a Christy announcement to all WebSocket clients."""
        await manager.broadcast({
            "event": "christy.announcement",
            "payload": {
                "type": event_type,
                "content": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        })
        logger.info("Christy announcement (%s): %s", event_type, text[:80])


# Singleton instance used by main.py
christy_service = ChristyProactiveService()
