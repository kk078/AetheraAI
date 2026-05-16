"""
Aethera AI - Proactive Intelligence

Delegates to the full proactive subsystem when available,
falls back to basic in-memory implementation otherwise.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("aethera.proactive")


@dataclass
class Alert:
    """Proactive alert."""
    id: str
    title: str
    message: str
    priority: str  # critical, high, medium, low
    category: str
    created_at: datetime
    acknowledged: bool = False


@dataclass
class BriefingItem:
    """Item for morning briefing."""
    category: str
    title: str
    summary: str
    details: str
    action_required: bool = False


class ProactiveIntelligence:
    """
    Proactive intelligence system.

    Delegates to the full proactive subsystem (proactive/ package)
    when available, falls back to basic in-memory implementation.
    """

    def __init__(self):
        self.alerts: List[Alert] = []
        self.subscriptions: List[str] = []
        self.callbacks: Dict[str, List[Callable]] = {}
        self._alert_manager = None
        self._briefing_generator = None
        self._scheduler = None
        self._action_queue = None
        self._automation_engine = None
        self._news_aggregator = None
        self._knowledge_updater = None
        self._temporal_processor = None
        self._init_subsystems()

    def _init_subsystems(self):
        """Try to initialize the full proactive subsystem."""
        try:
            from proactive.alerts import AlertManager
            self._alert_manager = AlertManager()
        except Exception as e:
            logger.debug(f"AlertManager not available: {e}")
        try:
            from proactive.morning_briefing import MorningBriefingGenerator
            self._briefing_generator = MorningBriefingGenerator(
                alert_manager=self._alert_manager,
            )
        except Exception as e:
            logger.debug(f"MorningBriefingGenerator not available: {e}")
        try:
            from proactive.scheduler import ProactiveScheduler
            self._scheduler = ProactiveScheduler()
        except Exception as e:
            logger.debug(f"ProactiveScheduler not available: {e}")
        try:
            from proactive.action_queue import ActionQueue
            self._action_queue = ActionQueue()
        except Exception as e:
            logger.debug(f"ActionQueue not available: {e}")
        try:
            from proactive.automations import AutomationEngine
            self._automation_engine = AutomationEngine(
                scheduler=self._scheduler,
                alert_manager=self._alert_manager,
                action_queue=self._action_queue,
            )
        except Exception as e:
            logger.debug(f"AutomationEngine not available: {e}")
        try:
            from proactive.news_aggregator import NewsAggregator
            self._news_aggregator = NewsAggregator()
        except Exception as e:
            logger.debug(f"NewsAggregator not available: {e}")
        try:
            from proactive.knowledge_updater import KnowledgeUpdater
            self._knowledge_updater = KnowledgeUpdater()
        except Exception as e:
            logger.debug(f"KnowledgeUpdater not available: {e}")
        try:
            from orchestrator.temporal import TemporalProcessor
            self._temporal_processor = TemporalProcessor()
        except Exception as e:
            logger.debug(f"TemporalProcessor not available: {e}")

    # === Alerts ===

    def create_alert(
        self,
        title: str,
        message: str,
        priority: str = "medium",
        category: str = "general"
    ) -> Alert:
        """Create a new alert."""
        if self._alert_manager:
            try:
                result = self._alert_manager.create_alert(
                    title=title,
                    message=message,
                    priority=priority,
                    alert_type=category,
                )
                return Alert(
                    id=str(result.get("id", "")),
                    title=result.get("title", title),
                    message=result.get("message", message),
                    priority=result.get("priority", priority),
                    category=result.get("alert_type", category),
                    created_at=result.get("created_at", datetime.now()),
                    acknowledged=result.get("acknowledged", False),
                )
            except Exception as e:
                logger.warning(f"AlertManager create_alert failed: {e}")

        alert = Alert(
            id=f"alert_{datetime.now().timestamp()}",
            title=title,
            message=message,
            priority=priority,
            category=category,
            created_at=datetime.now()
        )
        self.alerts.append(alert)
        self._notify_alert(alert)
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if self._alert_manager:
            try:
                result = self._alert_manager.acknowledge(alert_id)
                return result is not None
            except Exception as e:
                logger.warning(f"AlertManager acknowledge failed: {e}")

        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_unacknowledged_alerts(self, priority: Optional[str] = None) -> List[Alert]:
        """Get unacknowledged alerts."""
        if self._alert_manager:
            try:
                raw = self._alert_manager.get_alerts(acknowledged=False, priority=priority)
                return [Alert(
                    id=str(a.get("id", "")),
                    title=a.get("title", ""),
                    message=a.get("message", ""),
                    priority=a.get("priority", "medium"),
                    category=a.get("alert_type", "general"),
                    created_at=a.get("created_at", datetime.now()),
                    acknowledged=False,
                ) for a in raw]
            except Exception as e:
                logger.warning(f"AlertManager get_alerts failed: {e}")

        alerts = [a for a in self.alerts if not a.acknowledged]
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        return alerts

    def get_unacknowledged(self, priority: Optional[str] = None) -> List[Alert]:
        """Alias for get_unacknowledged_alerts."""
        return self.get_unacknowledged_alerts(priority)

    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts."""
        if self._alert_manager:
            try:
                raw = self._alert_manager.get_alerts()
                return [Alert(
                    id=str(a.get("id", "")),
                    title=a.get("title", ""),
                    message=a.get("message", ""),
                    priority=a.get("priority", "medium"),
                    category=a.get("alert_type", "general"),
                    created_at=a.get("created_at", datetime.now()),
                    acknowledged=a.get("acknowledged", False),
                ) for a in raw]
            except Exception as e:
                logger.warning(f"AlertManager get_alerts failed: {e}")
        return self.alerts

    def register_callback(self, event: str, callback: Callable):
        """Register callback for alert events."""
        if self._alert_manager:
            try:
                self._alert_manager.on(event, callback)
                return
            except Exception:
                pass
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)

    def _notify_alert(self, alert: Alert):
        """Notify registered callbacks of new alert."""
        if alert.priority in ["critical", "high"]:
            for callback in self.callbacks.get("alert", []):
                try:
                    callback(alert)
                except Exception:
                    pass

    # === Morning Briefing ===

    async def generate_briefing(self) -> Dict[str, Any]:
        """Generate morning briefing."""
        if self._briefing_generator:
            try:
                briefing = self._briefing_generator.generate()
                return {
                    "id": briefing.id,
                    "generated_at": briefing.generated_at.isoformat(),
                    "sections": [
                        {
                            "category": s.category,
                            "title": s.title,
                            "summary": s.summary,
                            "details": s.details,
                            "priority": s.priority,
                            "action_required": s.action_required,
                        }
                        for s in briefing.sections
                    ],
                    "has_critical_items": briefing.has_critical_items,
                    "text": briefing.to_text(),
                    "markdown": briefing.to_markdown(),
                }
            except Exception as e:
                logger.warning(f"BriefingGenerator failed: {e}")

        # Fallback: generate from internal state
        items = await self.generate_morning_briefing("default_user")
        return {
            "sections": [
                {"category": i.category, "title": i.title, "summary": i.summary, "details": i.details}
                for i in items
            ],
            "generated_at": datetime.now().isoformat(),
        }

    async def generate_morning_briefing(self, user_id: str) -> List[BriefingItem]:
        """Generate morning briefing for user (legacy interface)."""
        briefing = []

        # Get overnight alerts
        overnight_alerts = self._get_overnight_alerts()
        if overnight_alerts:
            briefing.append(BriefingItem(
                category="alerts",
                title="Overnight Alerts",
                summary=f"{len(overnight_alerts)} new alerts",
                details="\n".join([f"- {a.title}" for a in overnight_alerts]),
                action_required=any(a.priority in ["critical", "high"] for a in overnight_alerts)
            ))

        # Get upcoming deadlines from temporal processor
        deadlines = self._get_upcoming_deadlines()
        if deadlines:
            briefing.append(BriefingItem(
                category="deadlines",
                title="Upcoming Deadlines",
                summary=f"{len(deadlines)} deadlines this week",
                details="\n".join([f"- {d['description']}: due {d['deadline']}" for d in deadlines]),
                action_required=True
            ))

        # Healthcare news digest
        news = await self._get_news_digest()
        if news:
            briefing.append(BriefingItem(
                category="news",
                title="Healthcare News Digest",
                summary=f"{len(news)} relevant updates",
                details="\n".join([f"- {n.get('title', n.get('description', 'Update'))}" for n in news[:5]]),
                action_required=False
            ))

        # Calendar/events
        events = self._get_calendar_events()
        if events:
            briefing.append(BriefingItem(
                category="schedule",
                title="Today's Schedule",
                summary=f"{len(events)} events today",
                details="\n".join([f"- {e.get('time', 'TBD')}: {e.get('title', 'Event')}" for e in events]),
                action_required=False
            ))

        # Action queue items
        queue_items = self._get_action_queue_items()
        if queue_items:
            briefing.append(BriefingItem(
                category="actions",
                title="Pending Action Items",
                summary=f"{len(queue_items)} items requiring attention",
                details="\n".join([f"- {q.get('title', 'Item')} ({q.get('priority', 'normal')})" for q in queue_items[:5]]),
                action_required=True
            ))

        return briefing

    def _get_overnight_alerts(self) -> List[Alert]:
        """Get alerts from overnight hours."""
        now = datetime.now()
        cutoff = now - timedelta(hours=12)

        if self._alert_manager:
            try:
                raw = self._alert_manager.get_alerts(since=cutoff.isoformat(), acknowledged=False)
                return [Alert(
                    id=str(a.get("id", "")),
                    title=a.get("title", ""),
                    message=a.get("message", ""),
                    priority=a.get("priority", "medium"),
                    category=a.get("alert_type", "general"),
                    created_at=a.get("created_at", now),
                ) for a in raw]
            except Exception:
                pass

        return [a for a in self.alerts if a.created_at > cutoff and not a.acknowledged]

    def _get_upcoming_deadlines(self) -> List[Dict]:
        """Get upcoming deadlines from temporal processor."""
        if self._temporal_processor:
            try:
                upcoming = self._temporal_processor.get_upcoming(days=7)
                overdue = self._temporal_processor.get_overdue()
                results = []
                for item in overdue:
                    results.append({
                        "id": item.id,
                        "description": item.description,
                        "deadline": item.deadline or "overdue",
                        "priority": item.priority,
                        "overdue": True,
                    })
                for item in upcoming:
                    results.append({
                        "id": item.id,
                        "description": item.description,
                        "deadline": item.deadline or "no date",
                        "priority": item.priority,
                        "overdue": False,
                    })
                return results
            except Exception as e:
                logger.warning(f"Temporal deadline lookup failed: {e}")
        return []

    async def _get_news_digest(self) -> List[Dict]:
        """Get healthcare news digest from news aggregator."""
        if self._news_aggregator:
            try:
                articles = self._news_aggregator.get_digest(
                    category="healthcare_regulatory",
                    unread_only=True,
                    limit=5,
                )
                return articles
            except Exception as e:
                logger.warning(f"News digest lookup failed: {e}")
        return []

    def _get_calendar_events(self) -> List[Dict]:
        """Get today's calendar events from calendar plugin."""
        # Calendar integration requires the calendar connector to be configured
        # Returns empty until a calendar is connected
        return []

    def _get_action_queue_items(self) -> List[Dict]:
        """Get pending action queue items."""
        if self._action_queue:
            try:
                overdue = self._action_queue.get_overdue()
                next_items = []
                for _ in range(5):
                    item = self._action_queue.get_next()
                    if item:
                        next_items.append(item)
                return overdue + next_items
            except Exception as e:
                logger.warning(f"Action queue lookup failed: {e}")
        return []

    # === Scheduler ===

    def start_scheduler(self):
        """Start the proactive scheduler with built-in jobs."""
        if not self._scheduler:
            logger.info("ProactiveScheduler not available, skipping startup")
            return

        try:
            def _health_check():
                logger.debug("Scheduled health check")

            def _knowledge_update():
                if self._knowledge_updater:
                    try:
                        self._knowledge_updater.fetch_updates()
                        logger.info("Scheduled knowledge update completed")
                    except Exception as e:
                        logger.warning(f"Knowledge update failed: {e}")

            def _briefing_generation():
                logger.info("Scheduled briefing generation triggered")

            def _alert_check():
                if self._alert_manager:
                    try:
                        self._alert_manager.escalate_stale_alerts()
                        logger.debug("Scheduled alert check completed")
                    except Exception as e:
                        logger.warning(f"Alert check failed: {e}")

            def _weekly_report():
                logger.info("Weekly report generation triggered")

            def _news_fetch():
                if self._news_aggregator:
                    try:
                        self._news_aggregator.fetch_feeds()
                        logger.info("Scheduled news fetch completed")
                    except Exception as e:
                        logger.warning(f"News fetch failed: {e}")

            self._scheduler.register_health_check(health_check_func=_health_check)
            self._scheduler.register_knowledge_update(update_func=_knowledge_update)
            self._scheduler.register_briefing_generation(briefing_func=_briefing_generation)
            self._scheduler.register_alert_check(alert_check_func=_alert_check)
            self._scheduler.register_weekly_report(report_func=_weekly_report)
            self._scheduler.register_news_fetch(fetch_func=_news_fetch)
            self._scheduler.start()
            logger.info("ProactiveScheduler started with built-in jobs")
        except Exception as e:
            logger.warning(f"Failed to start ProactiveScheduler: {e}")

    def stop_scheduler(self):
        """Stop the proactive scheduler."""
        if self._scheduler:
            try:
                self._scheduler.shutdown()
                logger.info("ProactiveScheduler stopped")
            except Exception as e:
                logger.warning(f"Failed to stop ProactiveScheduler: {e}")

    # === Background Monitoring ===

    async def start_monitoring(self):
        """Start background monitoring tasks using the scheduler."""
        if self._scheduler:
            # Use the real scheduler instead of async sleep loops
            self.start_scheduler()
            logger.info("Proactive monitoring started via scheduler")
            # Keep the task alive so the scheduler stays running
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                self.stop_scheduler()
        else:
            # Fallback: basic monitoring loops
            tasks = [
                self._monitor_deadlines(),
                self._monitor_alerts(),
            ]
            await asyncio.gather(*tasks)

    async def _monitor_deadlines(self):
        """Monitor for approaching deadlines."""
        while True:
            await asyncio.sleep(3600)
            try:
                deadlines = self._get_upcoming_deadlines()
                for d in deadlines:
                    if d.get("overdue") or d.get("priority") == "high":
                        self.create_alert(
                            title=f"Deadline: {d['description']}",
                            message=f"Due: {d['deadline']}",
                            priority="high" if d.get("overdue") else "medium",
                            category="deadline",
                        )
            except Exception as e:
                logger.warning(f"Deadline monitoring error: {e}")

    async def _monitor_alerts(self):
        """Escalate stale alerts."""
        while True:
            await asyncio.sleep(300)
            try:
                if self._alert_manager:
                    self._alert_manager.escalate_stale_alerts()
            except Exception:
                pass


# Singleton instance
_intelligence: Optional[ProactiveIntelligence] = None


def get_proactive_intelligence() -> ProactiveIntelligence:
    """Get the proactive intelligence system."""
    global _intelligence
    if _intelligence is None:
        _intelligence = ProactiveIntelligence()
    return _intelligence