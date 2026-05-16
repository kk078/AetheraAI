"""
Aethera AI - Proactive Intelligence Package

Automated monitoring, briefing, alerting, and task management:
- Scheduler: Cron-like job runner with APScheduler and SQLite persistence
- Morning Briefing: Daily briefing with weather, calendar, alerts, news
- Alerts: Threshold-based alert system with priority escalation
- Action Queue: Prioritized task queue with auto-escalation
- Weekly Reports: Automated weekly summary and comparison
- Knowledge Updater: Auto-fetch CMS/FDA/CVE/regulatory updates
- News Aggregator: RSS feed monitoring, dedup, categorization, summarization
- Automations: Natural language automation builder (trigger/condition/action)
"""

from proactive.scheduler import ProactiveScheduler
from proactive.morning_briefing import MorningBriefingGenerator
from proactive.alerts import AlertManager
from proactive.action_queue import ActionQueue
from proactive.weekly_reports import WeeklyReportGenerator
from proactive.knowledge_updater import KnowledgeUpdater
from proactive.news_aggregator import NewsAggregator
from proactive.automations import AutomationEngine

__all__ = [
    "ProactiveScheduler",
    "MorningBriefingGenerator",
    "AlertManager",
    "ActionQueue",
    "WeeklyReportGenerator",
    "KnowledgeUpdater",
    "NewsAggregator",
    "AutomationEngine",
]