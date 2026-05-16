"""
Aethera AI - Proactive Scheduler

Cron-like job runner using APScheduler with SQLite persistence.
Supports cron, interval, and date triggers.
Built-in jobs: health checks, knowledge updates, briefing generation, alert checks.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("PROACTIVE_SCHEDULER_DB", "sqlite:///data/proactive_jobs.db")


class ProactiveScheduler:
    """
    Cron-like job runner with APScheduler and SQLite persistence.

    Supports:
    - Cron triggers (e.g., "0 7 * * *" for daily 7 AM)
    - Interval triggers (e.g., every 4 hours)
    - Date triggers (one-time execution at specific datetime)
    - Job persistence across restarts via SQLAlchemy job store
    - Pause/resume individual jobs or the entire scheduler
    """

    def __init__(
        self,
        db_url: str = DEFAULT_DB_PATH,
        thread_pool_size: int = 10,
        misfire_grace_time: int = 300,
        coalesce: bool = True,
        max_instances: int = 3,
    ):
        self._db_url = db_url
        self._misfire_grace_time = misfire_grace_time
        self._coalesce = coalesce
        self._max_instances = max_instances

        jobstores = {
            "default": SQLAlchemyJobStore(url=db_url)
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=thread_pool_size)
        }
        job_defaults = {
            "misfire_grace_time": misfire_grace_time,
            "coalesce": coalesce,
            "max_instances": max_instances,
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler. Safe to call if already running."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("ProactiveScheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("ProactiveScheduler shut down (wait=%s)", wait)

    @property
    def running(self) -> bool:
        return self._scheduler.running

    # ---------------------------------------------------------------------------
    # Job Management
    # ---------------------------------------------------------------------------

    def add_cron_job(
        self,
        func: Callable,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        cron_expr: Optional[str] = None,
        *,
        year=None,
        month=None,
        day=None,
        week=None,
        day_of_week=None,
        hour=None,
        minute=None,
        second=None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        replace_existing: bool = True,
        **kwargs,
    ) -> str:
        """
        Add a job with a cron trigger.

        Either pass a cron expression string (e.g., "0 7 * * mon-fri")
        or individual cron fields (hour=7, minute=0, day_of_week="mon-fri").
        """
        job_id = job_id or f"cron_{uuid.uuid4().hex[:12]}"
        name = name or getattr(func, "__name__", job_id)

        if cron_expr:
            parts = cron_expr.split()
            trigger_kwargs: Dict[str, Any] = {}
            cron_field_names = [
                "year", "month", "day", "week", "day_of_week",
                "hour", "minute", "second",
            ]
            # Pad short expressions: minute, hour, day, month, day_of_week
            while len(parts) < 5:
                parts.insert(0, "*")
            # Map 5-field cron: minute hour day month day_of_week
            if len(parts) == 5:
                cron_field_map = ["minute", "hour", "day", "month", "day_of_week"]
                for idx, field_name in enumerate(cron_field_map):
                    if parts[idx] != "*":
                        trigger_kwargs[field_name] = parts[idx]
            else:
                # Extended: second minute hour day month day_of_week year
                for idx, field_name in enumerate(cron_field_names):
                    if idx < len(parts) and parts[idx] != "*":
                        trigger_kwargs[field_name] = parts[idx]
            trigger = CronTrigger(**trigger_kwargs, start_date=start_date, end_date=end_date)
        else:
            trigger = CronTrigger(
                year=year, month=month, day=day, week=week,
                day_of_week=day_of_week, hour=hour, minute=minute,
                second=second, start_date=start_date, end_date=end_date,
            )

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=replace_existing,
            kwargs=kwargs,
        )
        logger.info("Added cron job %s (%s)", job_id, name)
        return job_id

    def add_interval_job(
        self,
        func: Callable,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        *,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        replace_existing: bool = True,
        **kwargs,
    ) -> str:
        """Add a job with an interval trigger."""
        job_id = job_id or f"interval_{uuid.uuid4().hex[:12]}"
        name = name or getattr(func, "__name__", job_id)

        trigger = IntervalTrigger(
            weeks=weeks, days=days, hours=hours, minutes=minutes,
            seconds=seconds, start_date=start_date, end_date=end_date,
        )

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=replace_existing,
            kwargs=kwargs,
        )
        logger.info("Added interval job %s (%s) every %dh%dm%ds", job_id, name, hours, minutes, seconds)
        return job_id

    def add_date_job(
        self,
        func: Callable,
        run_date: datetime,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        replace_existing: bool = True,
        **kwargs,
    ) -> str:
        """Add a one-time job that runs at a specific datetime."""
        job_id = job_id or f"date_{uuid.uuid4().hex[:12]}"
        name = name or getattr(func, "__name__", job_id)

        trigger = DateTrigger(run_date=run_date)

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=replace_existing,
            kwargs=kwargs,
        )
        logger.info("Added date job %s (%s) at %s", job_id, name, run_date.isoformat())
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID. Returns True if job existed."""
        try:
            self._scheduler.remove_job(job_id)
            logger.info("Removed job %s", job_id)
            return True
        except Exception:
            logger.warning("Job %s not found for removal", job_id)
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job. It will not fire until resumed."""
        try:
            self._scheduler.pause_job(job_id)
            logger.info("Paused job %s", job_id)
            return True
        except Exception:
            logger.warning("Job %s not found for pausing", job_id)
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            self._scheduler.resume_job(job_id)
            logger.info("Resumed job %s", job_id)
            return True
        except Exception:
            logger.warning("Job %s not found for resuming", job_id)
            return False

    def modify_job(self, job_id: str, **changes) -> bool:
        """Modify a job's properties (e.g., name, trigger, kwargs)."""
        try:
            self._scheduler.modify_job(job_id, **changes)
            logger.info("Modified job %s: %s", job_id, list(changes.keys()))
            return True
        except Exception:
            logger.warning("Job %s not found for modification", job_id)
            return False

    # ---------------------------------------------------------------------------
    # Listing / Status
    # ---------------------------------------------------------------------------

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs with their details."""
        jobs = self._scheduler.get_jobs()
        result = []
        for job in jobs:
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            trigger_str = str(job.trigger)
            result.append({
                "id": job.id,
                "name": job.name,
                "trigger": trigger_str,
                "next_run_time": next_run,
                "pending": job.pending,
                "max_instances": job.max_instances,
                "misfire_grace_time": job.misfire_grace_time,
            })
        return result

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific job."""
        job = self._scheduler.get_job(job_id)
        if not job:
            return None
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        return {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": next_run,
            "pending": job.pending,
            "max_instances": job.max_instances,
            "misfire_grace_time": job.misfire_grace_time,
        }

    def pause_all(self) -> None:
        """Pause the entire scheduler."""
        self._scheduler.pause()
        logger.info("All jobs paused")

    def resume_all(self) -> None:
        """Resume the entire scheduler."""
        self._scheduler.resume()
        logger.info("All jobs resumed")

    # ---------------------------------------------------------------------------
    # Event Handling
    # ---------------------------------------------------------------------------

    def on_event(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for job events.

        event_type: "success" or "error"
        callback: callable(event_data_dict)
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def _on_job_executed(self, event: JobEvent) -> None:
        """Internal: dispatch success events."""
        data = {
            "job_id": event.job_id,
            "retval": event.retval,
            "scheduled_run_time": event.scheduled_run_time.isoformat() if event.scheduled_run_time else None,
        }
        for cb in self._event_listeners.get("success", []):
            try:
                cb(data)
            except Exception as exc:
                logger.error("Success event callback error: %s", exc)

    def _on_job_error(self, event: JobEvent) -> None:
        """Internal: dispatch error events."""
        data = {
            "job_id": event.job_id,
            "exception": str(event.exception),
            "scheduled_run_time": event.scheduled_run_time.isoformat() if event.scheduled_run_time else None,
        }
        logger.error("Job %s failed: %s", event.job_id, event.exception)
        for cb in self._event_listeners.get("error", []):
            try:
                cb(data)
            except Exception as exc:
                logger.error("Error event callback error: %s", exc)

    # ---------------------------------------------------------------------------
    # Built-in Job Registration Helpers
    # ---------------------------------------------------------------------------

    def register_health_check(
        self,
        health_check_func: Callable,
        interval_minutes: int = 5,
        job_id: str = "builtin_health_check",
    ) -> str:
        """Register a periodic health check job."""
        return self.add_interval_job(
            health_check_func,
            job_id=job_id,
            name="Health Check",
            minutes=interval_minutes,
        )

    def register_knowledge_update(
        self,
        update_func: Callable,
        interval_hours: int = 6,
        job_id: str = "builtin_knowledge_update",
    ) -> str:
        """Register a periodic knowledge update job."""
        return self.add_interval_job(
            update_func,
            job_id=job_id,
            name="Knowledge Update",
            hours=interval_hours,
        )

    def register_briefing_generation(
        self,
        briefing_func: Callable,
        cron_expr: str = "0 7 * * *",
        job_id: str = "builtin_morning_briefing",
    ) -> str:
        """Register the daily morning briefing job."""
        return self.add_cron_job(
            briefing_func,
            job_id=job_id,
            name="Morning Briefing",
            cron_expr=cron_expr,
        )

    def register_alert_check(
        self,
        alert_check_func: Callable,
        interval_minutes: int = 15,
        job_id: str = "builtin_alert_check",
    ) -> str:
        """Register a periodic alert check job."""
        return self.add_interval_job(
            alert_check_func,
            job_id=job_id,
            name="Alert Check",
            minutes=interval_minutes,
        )

    def register_weekly_report(
        self,
        report_func: Callable,
        cron_expr: str = "0 9 * * mon",
        job_id: str = "builtin_weekly_report",
    ) -> str:
        """Register the weekly report generation job."""
        return self.add_cron_job(
            report_func,
            job_id=job_id,
            name="Weekly Report",
            cron_expr=cron_expr,
        )

    def register_news_fetch(
        self,
        fetch_func: Callable,
        interval_hours: int = 2,
        job_id: str = "builtin_news_fetch",
    ) -> str:
        """Register periodic news feed fetching."""
        return self.add_interval_job(
            fetch_func,
            job_id=job_id,
            name="News Fetch",
            hours=interval_hours,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_scheduler: Optional[ProactiveScheduler] = None


def get_scheduler(db_url: str = DEFAULT_DB_PATH) -> ProactiveScheduler:
    """Get or create the singleton ProactiveScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ProactiveScheduler(db_url=db_url)
    return _scheduler