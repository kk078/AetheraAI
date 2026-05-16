"""
Aethera AI - Morning Briefing Generator

Daily morning briefing with:
- Date and weather
- Calendar events
- Critical action items
- New alerts
- Healthcare updates (CMS/FDA)
- System status
- Usage stats
- News digest
- Upcoming deadlines

Generated at user's configured time (default 7:00 AM).
Delivered via chat, Telegram, or push notification.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

USER_TIMEZONE = os.environ.get("USER_TIMEZONE", "America/New_York")
USER_LOCATION = os.environ.get("USER_LOCATION", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


@dataclass
class BriefingSection:
    """A single section of the morning briefing."""
    category: str
    title: str
    summary: str
    details: str
    priority: str = "normal"  # normal, important, critical
    action_required: bool = False
    items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MorningBriefing:
    """Complete morning briefing."""
    id: str
    user_id: str
    generated_at: datetime
    sections: List[BriefingSection] = field(default_factory=list)
    delivered: bool = False
    delivery_channels: List[str] = field(default_factory=list)

    @property
    def has_critical_items(self) -> bool:
        return any(s.priority == "critical" or s.action_required for s in self.sections)

    def to_text(self) -> str:
        """Render the briefing as a plain-text summary."""
        now_str = self.generated_at.strftime("%A, %B %d, %Y")
        lines = [
            f"=== Aethera Morning Briefing ===",
            f"  {now_str}",
            f"  Generated at {self.generated_at.strftime('%H:%M %Z')}",
            "=" * 36,
            "",
        ]
        for section in self.sections:
            marker = "!" if section.action_required else "-"
            lines.append(f"[{marker}] {section.title}")
            lines.append(f"    {section.summary}")
            if section.details:
                for detail_line in section.details.split("\n"):
                    lines.append(f"    {detail_line}")
            lines.append("")

        if self.has_critical_items:
            lines.append(">>> ACTION REQUIRED: Items marked [!] need your attention <<<")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render the briefing as Markdown."""
        now_str = self.generated_at.strftime("%A, %B %d, %Y")
        lines = [
            "# Aethera Morning Briefing",
            f"**{now_str}** | Generated at {self.generated_at.strftime('%H:%M %Z')}",
            "",
        ]
        for section in self.sections:
            icon = ":warning:" if section.action_required else ":information_source:"
            lines.append(f"## {icon} {section.title}")
            lines.append(f"{section.summary}")
            lines.append("")
            if section.details:
                for detail_line in section.details.split("\n"):
                    lines.append(f"- {detail_line.strip().lstrip('- ')}")
                lines.append("")

        if self.has_critical_items:
            lines.append("---")
            lines.append("**ACTION REQUIRED**: Items above need your attention.")

        return "\n".join(lines)


class MorningBriefingGenerator:
    """
    Generates a daily morning briefing by aggregating data from
    multiple subsystems: alerts, calendar, action queue, knowledge
    updates, system health, usage stats, and news.
    """

    def __init__(
        self,
        user_id: str = "default",
        user_timezone: str = USER_TIMEZONE,
        user_location: str = USER_LOCATION,
        alert_manager: Optional[Any] = None,
        action_queue: Optional[Any] = None,
        knowledge_updater: Optional[Any] = None,
        news_aggregator: Optional[Any] = None,
        conversation_store: Optional[Any] = None,
        telegram_bot_token: str = TELEGRAM_BOT_TOKEN,
        telegram_chat_id: str = TELEGRAM_CHAT_ID,
    ):
        self.user_id = user_id
        self.user_timezone = user_timezone
        self.user_location = user_location
        self.alert_manager = alert_manager
        self.action_queue = action_queue
        self.knowledge_updater = knowledge_updater
        self.news_aggregator = news_aggregator
        self.conversation_store = conversation_store
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self._briefing_history: List[MorningBriefing] = []

    # ---------------------------------------------------------------------------
    # Main Generation
    # ---------------------------------------------------------------------------

    def generate(self) -> MorningBriefing:
        """
        Generate the full morning briefing by assembling all sections.
        Each section is built independently so failures don't block others.
        """
        briefing = MorningBriefing(
            id=f"briefing_{uuid.uuid4().hex[:12]}",
            user_id=self.user_id,
            generated_at=datetime.now(timezone.utc),
        )

        section_builders = [
            self._build_weather_section,
            self._build_calendar_section,
            self._build_action_items_section,
            self._build_alerts_section,
            self._build_healthcare_updates_section,
            self._build_system_status_section,
            self._build_usage_stats_section,
            self._build_news_digest_section,
            self._build_deadlines_section,
        ]

        for builder in section_builders:
            try:
                section = builder()
                if section:
                    briefing.sections.append(section)
            except Exception as exc:
                logger.error("Briefing section %s failed: %s", builder.__name__, exc)

        self._briefing_history.append(briefing)
        return briefing

    # ---------------------------------------------------------------------------
    # Section Builders
    # ---------------------------------------------------------------------------

    def _build_weather_section(self) -> Optional[BriefingSection]:
        """Build weather section using wttr.in or Open-Meteo."""
        if not self.user_location:
            return BriefingSection(
                category="weather",
                title="Weather",
                summary="No location configured. Set USER_LOCATION in environment.",
                details="",
                priority="normal",
            )

        try:
            # Use Open-Meteo (no API key required)
            geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
            geocode_params = {"name": self.user_location, "count": 1}
            with httpx.Client(timeout=10) as client:
                geo_resp = client.get(geocode_url, params=geocode_params)
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()

            if not geo_data.get("results"):
                return BriefingSection(
                    category="weather",
                    title="Weather",
                    summary=f"Could not geocode location: {self.user_location}",
                    details="",
                    priority="normal",
                )

            loc = geo_data["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            display_name = loc.get("name", self.user_location)

            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "temperature_unit": "fahrenheit",
                "timezone": self.user_timezone,
            }
            with httpx.Client(timeout=10) as client:
                resp = client.get(weather_url, params=weather_params)
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            t_max = daily.get("temperature_2m_max", [None])[0]
            t_min = daily.get("temperature_2m_min", [None])[0]
            precip = daily.get("precipitation_probability_max", [None])[0]
            wcode = daily.get("weathercode", [None])[0]

            weather_desc = self._weather_code_description(wcode)
            summary = f"{display_name}: {weather_desc}, {t_min}F - {t_max}F"
            details_parts = []
            if precip is not None:
                details_parts.append(f"Precipitation chance: {precip}%")
            if wcode is not None:
                details_parts.append(f"Conditions: {weather_desc}")

            return BriefingSection(
                category="weather",
                title="Weather",
                summary=summary,
                details="\n".join(details_parts),
                priority="normal",
            )
        except Exception as exc:
            logger.warning("Weather fetch failed: %s", exc)
            return BriefingSection(
                category="weather",
                title="Weather",
                summary=f"Weather unavailable for {self.user_location}",
                details="",
                priority="normal",
            )

    @staticmethod
    def _weather_code_description(code: Optional[int]) -> str:
        """Convert WMO weather code to description."""
        codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
            82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        if code is None:
            return "Unknown"
        return codes.get(code, f"Weather code {code}")

    def _build_calendar_section(self) -> Optional[BriefingSection]:
        """Build calendar events section."""
        # Integrates with CalDAV if configured, otherwise returns placeholder
        caldav_url = os.environ.get("CALDAV_URL", "")
        if not caldav_url:
            return None

        try:
            import caldav
            username = os.environ.get("CALDAV_USERNAME", "")
            password = os.environ.get("CALDAV_PASSWORD", "")
            client = caldav.DAVClient(url=caldav_url, username=username, password=password)
            principal = client.principal()
            calendars = principal.calendars()
            today_start = datetime.now()
            today_end = today_start.replace(hour=23, minute=59, second=59)
            events = []
            for calendar in calendars:
                results = calendar.date_search(today_start, today_end)
                for event in results:
                    ev = event.vobject_instance.vevent
                    events.append({
                        "title": ev.summary.value if hasattr(ev, "summary") else "Untitled",
                        "time": ev.dtstart.value.isoformat() if hasattr(ev, "dtstart") else "",
                    })

            if not events:
                return BriefingSection(
                    category="calendar",
                    title="Today's Calendar",
                    summary="No events scheduled for today.",
                    details="",
                    priority="normal",
                )

            events.sort(key=lambda e: e["time"])
            details_lines = []
            for ev in events:
                time_str = ev["time"].split("T")[1][:5] if "T" in ev["time"] else "All day"
                details_lines.append(f"{time_str}: {ev['title']}")

            return BriefingSection(
                category="calendar",
                title="Today's Calendar",
                summary=f"{len(events)} event(s) today",
                details="\n".join(details_lines),
                priority="normal",
            )
        except ImportError:
            logger.debug("caldav library not installed, skipping calendar")
            return None
        except Exception as exc:
            logger.warning("Calendar fetch failed: %s", exc)
            return None

    def _build_action_items_section(self) -> Optional[BriefingSection]:
        """Build critical action items section from the action queue."""
        if not self.action_queue:
            return None

        try:
            critical_items = self.action_queue.get_by_priority("critical")
            urgent_items = self.action_queue.get_by_priority("urgent")
            all_items = critical_items + urgent_items

            if not all_items:
                return None

            details_lines = []
            for item in all_items[:10]:
                priority_marker = "[CRITICAL]" if item.get("priority") == "critical" else "[URGENT]"
                due = item.get("due_date", "")
                due_str = f" (Due: {due})" if due else ""
                details_lines.append(f"{priority_marker} {item.get('title', 'Untitled')}{due_str}")

            return BriefingSection(
                category="action_items",
                title="Critical Action Items",
                summary=f"{len(critical_items)} critical, {len(urgent_items)} urgent items",
                details="\n".join(details_lines),
                priority="critical" if critical_items else "important",
                action_required=True,
            )
        except Exception as exc:
            logger.warning("Action items section failed: %s", exc)
            return None

    def _build_alerts_section(self) -> Optional[BriefingSection]:
        """Build new/unacknowledged alerts section."""
        if not self.alert_manager:
            return None

        try:
            alerts = self.alert_manager.get_unacknowledged()
            if not alerts:
                return None

            # Group by priority
            critical = [a for a in alerts if a.get("priority") == "critical"]
            urgent = [a for a in alerts if a.get("priority") == "urgent"]
            warning = [a for a in alerts if a.get("priority") == "warning"]
            info = [a for a in alerts if a.get("priority") == "info"]

            details_lines = []
            for a in critical[:3]:
                details_lines.append(f"[CRITICAL] {a.get('title', '')}: {a.get('message', '')[:80]}")
            for a in urgent[:3]:
                details_lines.append(f"[URGENT] {a.get('title', '')}: {a.get('message', '')[:80]}")
            for a in warning[:2]:
                details_lines.append(f"[WARN] {a.get('title', '')}")
            if info:
                details_lines.append(f"... and {len(info)} info-level alerts")

            return BriefingSection(
                category="alerts",
                title="New Alerts",
                summary=f"{len(alerts)} unacknowledged alert(s): "
                        f"{len(critical)} critical, {len(urgent)} urgent, "
                        f"{len(warning)} warning, {len(info)} info",
                details="\n".join(details_lines),
                priority="critical" if critical else ("important" if urgent else "normal"),
                action_required=bool(critical or urgent),
            )
        except Exception as exc:
            logger.warning("Alerts section failed: %s", exc)
            return None

    def _build_healthcare_updates_section(self) -> Optional[BriefingSection]:
        """Build healthcare regulatory updates section (CMS/FDA)."""
        if not self.knowledge_updater:
            return None

        try:
            changelog = self.knowledge_updater.get_changelog(days=1)
            if not changelog:
                return None

            details_lines = []
            for entry in changelog[:8]:
                source = entry.get("source", "Unknown")
                title = entry.get("title", "Untitled")
                details_lines.append(f"[{source}] {title}")

            return BriefingSection(
                category="healthcare_updates",
                title="Healthcare Regulatory Updates",
                summary=f"{len(changelog)} update(s) in the last 24 hours",
                details="\n".join(details_lines),
                priority="important",
            )
        except Exception as exc:
            logger.warning("Healthcare updates section failed: %s", exc)
            return None

    def _build_system_status_section(self) -> Optional[BriefingSection]:
        """Build system health status section."""
        try:
            checks = self._run_system_checks()
            if not checks:
                return None

            healthy_count = sum(1 for c in checks if c["status"] == "healthy")
            unhealthy = [c for c in checks if c["status"] != "healthy"]
            details_lines = []
            for c in checks:
                marker = "OK" if c["status"] == "healthy" else "FAIL"
                details_lines.append(f"[{marker}] {c['name']}: {c.get('message', c['status'])}")

            return BriefingSection(
                category="system_status",
                title="System Status",
                summary=f"{healthy_count}/{len(checks)} systems healthy",
                details="\n".join(details_lines),
                priority="critical" if unhealthy else "normal",
                action_required=bool(unhealthy),
            )
        except Exception as exc:
            logger.warning("System status section failed: %s", exc)
            return None

    def _run_system_checks(self) -> List[Dict[str, Any]]:
        """Run lightweight system health checks."""
        checks = []

        # Database check
        try:
            import sqlite3
            db_path = os.environ.get("DATABASE_URL", "sqlite:///data/aethera.db")
            if db_path.startswith("sqlite:///"):
                path = db_path.replace("sqlite:///", "")
                if os.path.exists(path):
                    conn = sqlite3.connect(path)
                    conn.execute("SELECT 1")
                    conn.close()
                    checks.append({"name": "Database", "status": "healthy", "message": "Connected"})
                else:
                    checks.append({"name": "Database", "status": "healthy", "message": "Not yet initialized"})
            else:
                checks.append({"name": "Database", "status": "healthy", "message": "External DB configured"})
        except Exception as exc:
            checks.append({"name": "Database", "status": "unhealthy", "message": str(exc)[:60]})

        # Redis check
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            try:
                import redis as rlib
                r = rlib.from_url(redis_url, socket_connect_timeout=3)
                r.ping()
                checks.append({"name": "Redis", "status": "healthy", "message": "Connected"})
            except Exception as exc:
                checks.append({"name": "Redis", "status": "degraded", "message": str(exc)[:60]})
        else:
            checks.append({"name": "Redis", "status": "healthy", "message": "Not configured (optional)"})

        # Disk space check
        try:
            import shutil
            usage = shutil.disk_usage("/")
            free_pct = usage.free / usage.total * 100
            if free_pct < 10:
                checks.append({"name": "Disk Space", "status": "unhealthy",
                                "message": f"Only {free_pct:.1f}% free"})
            elif free_pct < 25:
                checks.append({"name": "Disk Space", "status": "degraded",
                                "message": f"{free_pct:.1f}% free"})
            else:
                checks.append({"name": "Disk Space", "status": "healthy",
                                "message": f"{free_pct:.1f}% free"})
        except Exception:
            pass

        return checks

    def _build_usage_stats_section(self) -> Optional[BriefingSection]:
        """Build usage statistics section."""
        if not self.conversation_store:
            return None

        try:
            yesterday = datetime.now() - timedelta(days=1)
            # This is a simplified view - the actual conversation store
            # may provide richer analytics
            conv_count = self.conversation_store.get_conversation_count(self.user_id)
            recent = self.conversation_store.list_conversations(self.user_id, limit=5)
            recent_count = len(recent)

            details_lines = [
                f"Total conversations: {conv_count}",
                f"Recent activity: {recent_count} conversations",
            ]

            return BriefingSection(
                category="usage_stats",
                title="Usage Statistics",
                summary=f"{conv_count} total conversations",
                details="\n".join(details_lines),
                priority="normal",
            )
        except Exception as exc:
            logger.warning("Usage stats section failed: %s", exc)
            return None

    def _build_news_digest_section(self) -> Optional[BriefingSection]:
        """Build news digest section from the news aggregator."""
        if not self.news_aggregator:
            return None

        try:
            digest = self.news_aggregator.get_digest(category=None, limit=10)
            if not digest:
                return None

            details_lines = []
            for article in digest[:10]:
                cat = article.get("category", "general")
                title = article.get("title", "Untitled")
                source = article.get("source", "Unknown")
                details_lines.append(f"[{cat}] {title} ({source})")

            return BriefingSection(
                category="news_digest",
                title="News Digest",
                summary=f"{len(digest)} articles since last briefing",
                details="\n".join(details_lines),
                priority="normal",
            )
        except Exception as exc:
            logger.warning("News digest section failed: %s", exc)
            return None

    def _build_deadlines_section(self) -> Optional[BriefingSection]:
        """Build upcoming deadlines section."""
        if not self.action_queue:
            return None

        try:
            # Get items with due dates in the next 7 days
            all_items = []
            for priority in ["critical", "urgent", "normal", "low"]:
                items = self.action_queue.get_by_priority(priority)
                all_items.extend(items)

            upcoming = []
            now = datetime.now()
            for item in all_items:
                due = item.get("due_date")
                if not due:
                    continue
                if isinstance(due, str):
                    try:
                        due_dt = datetime.fromisoformat(due)
                    except (ValueError, TypeError):
                        continue
                elif isinstance(due, datetime):
                    due_dt = due
                else:
                    continue

                days_left = (due_dt - now).days
                if 0 <= days_left <= 7:
                    upcoming.append({**item, "days_left": days_left})

            if not upcoming:
                return None

            upcoming.sort(key=lambda x: x["days_left"])
            details_lines = []
            for item in upcoming[:8]:
                days = item["days_left"]
                urgency = "TODAY" if days == 0 else f"{days} day(s) left"
                details_lines.append(f"[{urgency}] {item.get('title', 'Untitled')}")

            return BriefingSection(
                category="deadlines",
                title="Upcoming Deadlines",
                summary=f"{len(upcoming)} deadline(s) within 7 days",
                details="\n".join(details_lines),
                priority="important" if any(d["days_left"] <= 1 for d in upcoming) else "normal",
                action_required=any(d["days_left"] == 0 for d in upcoming),
            )
        except Exception as exc:
            logger.warning("Deadlines section failed: %s", exc)
            return None

    # ---------------------------------------------------------------------------
    # Delivery
    # ---------------------------------------------------------------------------

    def deliver(self, briefing: MorningBriefing, channels: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Deliver the briefing through the specified channels.

        Supported channels: "chat", "telegram", "push"
        Returns a dict mapping channel name to success boolean.
        """
        if channels is None:
            channels = ["chat"]

        results: Dict[str, bool] = {}
        for channel in channels:
            try:
                if channel == "chat":
                    results["chat"] = self._deliver_chat(briefing)
                elif channel == "telegram":
                    results["telegram"] = self._deliver_telegram(briefing)
                elif channel == "push":
                    results["push"] = self._deliver_push(briefing)
                else:
                    logger.warning("Unknown delivery channel: %s", channel)
                    results[channel] = False
            except Exception as exc:
                logger.error("Delivery via %s failed: %s", channel, exc)
                results[channel] = False

        briefing.delivered = True
        briefing.delivery_channels = [ch for ch, ok in results.items() if ok]
        return results

    def _deliver_chat(self, briefing: MorningBriefing) -> bool:
        """Deliver briefing to the chat interface (store in conversation)."""
        if not self.conversation_store:
            logger.info("Briefing delivered to chat (no store, logged only)")
            return True

        try:
            text = briefing.to_text()
            conv_id = f"briefing_{briefing.generated_at.strftime('%Y%m%d')}"
            self.conversation_store.create_conversation(self.user_id, conv_id, f"Morning Briefing - {briefing.generated_at.strftime('%Y-%m-%d')}")
            self.conversation_store.add_message(conv_id, "assistant", text, specialist="proactive")
            return True
        except Exception as exc:
            logger.error("Chat delivery failed: %s", exc)
            return False

    def _deliver_telegram(self, briefing: MorningBriefing) -> bool:
        """Deliver briefing via Telegram bot."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.debug("Telegram not configured, skipping delivery")
            return False

        try:
            text = briefing.to_text()
            # Telegram message limit is 4096 chars
            if len(text) > 4000:
                text = text[:3997] + "..."

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, json={
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                })
                resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Telegram delivery failed: %s", exc)
            return False

    def _deliver_push(self, briefing: MorningBriefing) -> bool:
        """
        Deliver briefing as a push notification via the NotificationsPlugin.
        Falls back to logging if the plugin is not available.
        """
        try:
            from plugins.notifications.notifications_plugin import NotificationsPlugin
            plugin = NotificationsPlugin()
            summary = briefing.sections[0].summary if briefing.sections else "No items"
            plugin.execute("send", {
                "message": f"Morning Briefing: {summary}",
                "title": f"Aethera Briefing - {briefing.generated_at.strftime('%b %d')}",
                "priority": "high" if briefing.has_critical_items else "normal",
                "channels": ["browser"],
            })
            return True
        except Exception as exc:
            logger.info("Push delivery for briefing %s: no NotificationsPlugin available, logged only (%s)", briefing.id, exc)
            return True

    # ---------------------------------------------------------------------------
    # History
    # ---------------------------------------------------------------------------

    def get_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent briefing history."""
        return [
            {
                "id": b.id,
                "generated_at": b.generated_at.isoformat(),
                "sections": len(b.sections),
                "has_critical": b.has_critical_items,
                "delivered": b.delivered,
                "channels": b.delivery_channels,
            }
            for b in self._briefing_history[-limit:]
        ]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_generator: Optional[MorningBriefingGenerator] = None


def get_briefing_generator(**kwargs) -> MorningBriefingGenerator:
    """Get or create the singleton MorningBriefingGenerator instance."""
    global _generator
    if _generator is None:
        _generator = MorningBriefingGenerator(**kwargs)
    return _generator