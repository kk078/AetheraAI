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

import logging

logger = logging.getLogger("aethera.proactive")

# Failure-tolerant imports: a missing optional dependency (e.g. apscheduler)
# for one subsystem must not make the whole package — including lightweight
# pieces like KnowledgeUpdater — unimportable. Mirrors specialists/__init__.py.
_OPTIONAL_EXPORTS = {
    "ProactiveScheduler": ("proactive.scheduler", "ProactiveScheduler"),
    "MorningBriefingGenerator": ("proactive.morning_briefing", "MorningBriefingGenerator"),
    "AlertManager": ("proactive.alerts", "AlertManager"),
    "ActionQueue": ("proactive.action_queue", "ActionQueue"),
    "WeeklyReportGenerator": ("proactive.weekly_reports", "WeeklyReportGenerator"),
    "KnowledgeUpdater": ("proactive.knowledge_updater", "KnowledgeUpdater"),
    "NewsAggregator": ("proactive.news_aggregator", "NewsAggregator"),
    "AutomationEngine": ("proactive.automations", "AutomationEngine"),
}

__all__ = []

for _name, (_module, _attr) in _OPTIONAL_EXPORTS.items():
    try:
        _mod = __import__(_module, fromlist=[_attr])
        globals()[_name] = getattr(_mod, _attr)
        __all__.append(_name)
    except Exception as _exc:  # ImportError for missing deps, etc.
        logger.debug("Proactive export '%s' unavailable: %s", _name, _exc)