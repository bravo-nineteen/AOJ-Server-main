"""Scheduled announcement service.

Runs every 60 seconds.  For every enabled AnnouncementRule it looks at
today's schedule items and broadcasts a Christy announcement (via WebSocket)
when the current time is within a ±30-second window of
  (item.start_time - trigger_minutes_before)

A fired-for key is stored in memory so each rule/item pair fires exactly once
per server process lifetime (restarting the server resets the set, which is
fine – the window prevents double-firing within the same minute).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class ScheduledAnnouncementsService:
    """Watches schedule items and fires configurable timed announcements."""

    def __init__(self) -> None:
        # Set of (rule_id, schedule_item_id) that have already fired today
        self._fired: set[tuple[int, int]] = set()
        # Reset fired set at midnight UTC
        self._last_reset_day: int = datetime.utcnow().day

    async def ticker(self) -> None:
        """Run every 60 seconds."""
        await asyncio.sleep(15)  # small startup delay
        while True:
            try:
                await self._check()
            except Exception:
                logger.exception("Scheduled announcements ticker error")
            await asyncio.sleep(60)

    async def _check(self) -> None:
        from app.core.websocket import websocket_manager
        from app.database import SessionLocal
        from app.models.announcement_rule import AnnouncementRule
        from app.models.schedule import ScheduleItem

        now_utc = datetime.now(timezone.utc)

        # Reset fired set each UTC day so rules re-fire the next day
        if now_utc.day != self._last_reset_day:
            self._fired.clear()
            self._last_reset_day = now_utc.day

        if websocket_manager.connected_count == 0:
            return

        db = SessionLocal()
        try:
            rules = (
                db.query(AnnouncementRule)
                .filter(AnnouncementRule.enabled == True)  # noqa: E712
                .all()
            )
            if not rules:
                return

            # Today's schedule items (naive UTC boundaries)
            day_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            items = (
                db.query(ScheduleItem)
                .filter(
                    ScheduleItem.start_time >= day_start.replace(tzinfo=None),
                    ScheduleItem.start_time < day_end.replace(tzinfo=None),
                    ScheduleItem.is_complete == False,  # noqa: E712
                )
                .all()
            )

            for rule in rules:
                allowed_types = [
                    t.strip() for t in rule.trigger_activity_types.split(",") if t.strip()
                ]
                for item in items:
                    fire_key = (rule.id, item.id)
                    if fire_key in self._fired:
                        continue

                    if allowed_types and item.activity_type not in allowed_types:
                        continue

                    # start_time is stored naive UTC
                    item_start = item.start_time
                    if item_start.tzinfo is None:
                        item_start = item_start.replace(tzinfo=timezone.utc)

                    fire_at = item_start - timedelta(minutes=rule.trigger_minutes_before)
                    delta = abs((now_utc - fire_at).total_seconds())

                    # Fire within a ±30-second window
                    if delta <= 30:
                        text = self._render(rule.message_template, item)
                        self._fired.add(fire_key)
                        await websocket_manager.broadcast(
                            {
                                "event": "christy.announcement",
                                "payload": {
                                    "type": "scheduled_rule",
                                    "rule_id": rule.id,
                                    "rule_name": rule.name,
                                    "content": text,
                                },
                            }
                        )
                        logger.info(
                            "Scheduled announcement fired: rule=%s item=%s text=%r",
                            rule.id,
                            item.id,
                            text,
                        )
        finally:
            db.close()

    @staticmethod
    def _render(template: str, item: "ScheduleItem") -> str:
        start_fmt = item.start_time.strftime("%I:%M %p") if item.start_time else ""
        return (
            template
            .replace("{title}", item.title or "")
            .replace("{activity_type}", item.activity_type or "")
            .replace("{start_time}", start_fmt)
        )


scheduled_announcements_service = ScheduledAnnouncementsService()
