"""
Aethera AI - Alert Manager

Threshold-based alert system with priority levels and escalation.

Alert types:
- system_health: System component failures or degradation
- usage_limit: Approaching or exceeding usage quotas
- deadline_approaching: Time-sensitive deadlines approaching
- compliance_deadline: Regulatory/compliance filing deadlines
- knowledge_update_available: New CMS/FDA/CVE data available
- claim_status_change: Claim denial, approval, or status change

Priority levels: info, warning, urgent, critical

Supports: create, acknowledge, get unacknowledged, escalate stale alerts.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("ALERTS_DB_PATH", "/data/proactive_alerts.db")

PRIORITY_LEVELS = ["info", "warning", "urgent", "critical"]
PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITY_LEVELS)}

ALERT_TYPES = [
    "system_health",
    "usage_limit",
    "deadline_approaching",
    "compliance_deadline",
    "knowledge_update_available",
    "claim_status_change",
]


class Alert:
    """Represents a single alert."""

    __slots__ = (
        "id", "alert_type", "title", "message", "priority",
        "source", "threshold", "current_value", "metadata",
        "created_at", "acknowledged_at", "acknowledged_by",
        "escalated_at", "escalated_to", "resolved_at",
    )

    def __init__(
        self,
        id: str,
        alert_type: str,
        title: str,
        message: str,
        priority: str = "info",
        source: str = "",
        threshold: Optional[float] = None,
        current_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        acknowledged_at: Optional[str] = None,
        acknowledged_by: Optional[str] = None,
        escalated_at: Optional[str] = None,
        escalated_to: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ):
        self.id = id
        self.alert_type = alert_type
        self.title = title
        self.message = message
        self.priority = priority
        self.source = source
        self.threshold = threshold
        self.current_value = current_value
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.acknowledged_at = acknowledged_at
        self.acknowledged_by = acknowledged_by
        self.escalated_at = escalated_at
        self.escalated_to = escalated_to
        self.resolved_at = resolved_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "source": self.source,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "escalated_at": self.escalated_at,
            "escalated_to": self.escalated_to,
            "resolved_at": self.resolved_at,
        }


class AlertManager:
    """
    Threshold-based alert system with priority levels and automatic escalation.

    Alerts are persisted in SQLite. Stale unacknowledged alerts can be
    automatically escalated based on configurable timeouts per priority level.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        escalation_timeouts: Optional[Dict[str, int]] = None,
    ):
        """
        Args:
            db_path: Path to SQLite database for alert persistence.
            escalation_timeouts: Dict mapping priority to seconds before auto-escalation.
                Default: {"info": 86400, "warning": 14400, "urgent": 3600, "critical": 900}
        """
        self._db_path = db_path
        self._escalation_timeouts = escalation_timeouts or {
            "info": 86400,       # 24 hours
            "warning": 14400,    # 4 hours
            "urgent": 3600,      # 1 hour
            "critical": 900,     # 15 minutes
        }
        self._conn: Optional[sqlite3.Connection] = None
        self._callbacks: Dict[str, List[Callable]] = {
            "created": [],
            "acknowledged": [],
            "escalated": [],
        }
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the alerts table if it does not exist."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'info',
                source TEXT DEFAULT '',
                threshold REAL,
                current_value REAL,
                metadata JSON DEFAULT '{}',
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                escalated_at TEXT,
                escalated_to TEXT,
                resolved_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority);
            CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
            CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged_at);
            CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
        """)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------------
    # Create Alert
    # ---------------------------------------------------------------------------

    def create_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        priority: str = "info",
        source: str = "",
        threshold: Optional[float] = None,
        current_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Create a new alert.

        Args:
            alert_type: One of the ALERT_TYPES constants.
            title: Short descriptive title.
            message: Detailed message.
            priority: One of info, warning, urgent, critical.
            source: Origin system/component.
            threshold: The threshold that was crossed.
            current_value: The current measured value.
            metadata: Additional key-value data.

        Returns:
            The created Alert object.
        """
        if alert_type not in ALERT_TYPES:
            logger.warning("Unknown alert_type '%s', creating anyway", alert_type)
        if priority not in PRIORITY_LEVELS:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of {PRIORITY_LEVELS}")

        alert = Alert(
            id=f"alert_{uuid.uuid4().hex[:12]}",
            alert_type=alert_type,
            title=title,
            message=message,
            priority=priority,
            source=source,
            threshold=threshold,
            current_value=current_value,
            metadata=metadata or {},
        )

        self._conn.execute(
            """INSERT INTO alerts
               (id, alert_type, title, message, priority, source,
                threshold, current_value, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert.id, alert.alert_type, alert.title, alert.message,
                alert.priority, alert.source, alert.threshold,
                alert.current_value, json.dumps(alert.metadata), alert.created_at,
            ),
        )
        self._conn.commit()

        self._fire_callbacks("created", alert)
        logger.info("Created %s alert [%s]: %s", priority, alert.id, title)
        return alert

    # ---------------------------------------------------------------------------
    # Acknowledge
    # ---------------------------------------------------------------------------

    def acknowledge(self, alert_id: str, acknowledged_by: str = "user") -> Optional[Alert]:
        """
        Acknowledge an alert. Returns the updated Alert, or None if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()

        if not row:
            logger.warning("Alert %s not found for acknowledgement", alert_id)
            return None

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE alerts SET acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
            (now, acknowledged_by, alert_id),
        )
        self._conn.commit()

        alert = self._row_to_alert(row)
        alert.acknowledged_at = now
        alert.acknowledged_by = acknowledged_by

        self._fire_callbacks("acknowledged", alert)
        logger.info("Alert %s acknowledged by %s", alert_id, acknowledged_by)
        return alert

    # ---------------------------------------------------------------------------
    # Query Unacknowledged
    # ---------------------------------------------------------------------------

    def get_unacknowledged(
        self,
        priority: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all unacknowledged alerts, optionally filtered by priority and type.

        Returns list of alert dicts ordered by priority (critical first), then by age.
        """
        query = "SELECT * FROM alerts WHERE acknowledged_at IS NULL"
        params: List[Any] = []

        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)

        # Order: highest priority first, then oldest first
        query += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 WHEN 'warning' THEN 2 WHEN 'info' THEN 3 END, created_at ASC"
        query += " LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_alert(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Get Alerts
    # ---------------------------------------------------------------------------

    def get_alerts(
        self,
        priority: Optional[str] = None,
        alert_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        resolved: Optional[bool] = None,
        since: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query alerts with flexible filtering.
        """
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List[Any] = []

        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)
        if acknowledged is True:
            query += " AND acknowledged_at IS NOT NULL"
        elif acknowledged is False:
            query += " AND acknowledged_at IS NULL"
        if resolved is True:
            query += " AND resolved_at IS NOT NULL"
        elif resolved is False:
            query += " AND resolved_at IS NULL"
        if since:
            query += " AND created_at >= ?"
            params.append(since)

        query += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 WHEN 'warning' THEN 2 WHEN 'info' THEN 3 END, created_at DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_alert(r).to_dict()) for r in rows]

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a single alert by ID."""
        row = self._conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not row:
            return None
        return dict(self._row_to_alert(row).to_dict())

    # ---------------------------------------------------------------------------
    # Resolve
    # ---------------------------------------------------------------------------

    def resolve(self, alert_id: str) -> Optional[Alert]:
        """Mark an alert as resolved."""
        row = self._conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not row:
            return None

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE alerts SET resolved_at = ? WHERE id = ?",
            (now, alert_id),
        )
        self._conn.commit()

        alert = self._row_to_alert(row)
        alert.resolved_at = now
        logger.info("Alert %s resolved", alert_id)
        return alert

    # ---------------------------------------------------------------------------
    # Escalation
    # ---------------------------------------------------------------------------

    def escalate_stale_alerts(self) -> List[Alert]:
        """
        Escalate unacknowledged alerts that have exceeded their priority's timeout.

        Escalation moves the alert up one priority level:
        info -> warning -> urgent -> critical (critical stays critical but is re-notified).

        Returns list of escalated alerts.
        """
        now = datetime.now(timezone.utc)
        escalated: List[Alert] = []

        # Get all unacknowledged, unresolved alerts
        rows = self._conn.execute(
            "SELECT * FROM alerts WHERE acknowledged_at IS NULL AND resolved_at IS NULL"
        ).fetchall()

        for row in rows:
            alert = self._row_to_alert(row)
            try:
                created = datetime.fromisoformat(alert.created_at)
            except (ValueError, TypeError):
                continue

            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            age_seconds = (now - created).total_seconds()
            timeout = self._escalation_timeouts.get(alert.priority, 86400)

            if age_seconds >= timeout:
                # Determine escalated priority
                current_rank = PRIORITY_RANK.get(alert.priority, 0)
                new_rank = min(current_rank + 1, len(PRIORITY_LEVELS) - 1)
                new_priority = PRIORITY_LEVELS[new_rank]

                now_iso = now.isoformat()
                self._conn.execute(
                    "UPDATE alerts SET priority = ?, escalated_at = ?, escalated_to = ? WHERE id = ?",
                    (new_priority, now_iso, new_priority, alert.id),
                )

                escalated_alert = alert
                escalated_alert.priority = new_priority
                escalated_alert.escalated_at = now_iso
                escalated_alert.escalated_to = new_priority
                escalated.append(escalated_alert)

                self._fire_callbacks("escalated", escalated_alert)
                logger.warning(
                    "Escalated alert %s from %s to %s (age: %.0fs)",
                    alert.id, alert.priority, new_priority, age_seconds,
                )

        if escalated:
            self._conn.commit()

        return escalated

    # ---------------------------------------------------------------------------
    # Threshold Monitoring
    # ---------------------------------------------------------------------------

    def check_threshold(
        self,
        alert_type: str,
        source: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        comparison: str = "gt",
        title: Optional[str] = None,
        message: Optional[str] = None,
        priority: str = "warning",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """
        Check a metric against a threshold and create an alert if crossed.

        Args:
            alert_type: Alert category.
            source: Origin system/component.
            metric_name: Name of the metric being checked.
            current_value: The current value of the metric.
            threshold: The threshold value.
            comparison: "gt" (greater than), "lt" (less than), "gte", "lte", "eq".
            title: Custom title (auto-generated if None).
            message: Custom message.
            priority: Alert priority if threshold is crossed.
            metadata: Additional data.

        Returns:
            Alert if threshold crossed, None otherwise.
        """
        crossed = False
        if comparison == "gt":
            crossed = current_value > threshold
        elif comparison == "lt":
            crossed = current_value < threshold
        elif comparison == "gte":
            crossed = current_value >= threshold
        elif comparison == "lte":
            crossed = current_value <= threshold
        elif comparison == "eq":
            crossed = current_value == threshold

        if not crossed:
            return None

        # Check for duplicate recent alert
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta
        cutoff_iso = (cutoff - timedelta(hours=1)).isoformat()
        existing = self._conn.execute(
            """SELECT id FROM alerts
               WHERE alert_type = ? AND source = ? AND acknowledged_at IS NULL
               AND created_at > ?
               LIMIT 1""",
            (alert_type, source, cutoff_iso),
        ).fetchone()

        if existing:
            logger.debug("Threshold alert already exists for %s/%s, skipping", alert_type, source)
            return None

        if not title:
            title = f"{metric_name} {comparison} {threshold}"
        if not message:
            message = f"{source} {metric_name} is {current_value}, threshold is {threshold} ({comparison})"

        return self.create_alert(
            alert_type=alert_type,
            title=title,
            message=message,
            priority=priority,
            source=source,
            threshold=threshold,
            current_value=current_value,
            metadata=metadata or {"metric_name": metric_name, "comparison": comparison},
        )

    # ---------------------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------------------

    def get_counts(self) -> Dict[str, Any]:
        """Get alert counts by priority and acknowledgement status."""
        total = self._conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        unacknowledged = self._conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL"
        ).fetchone()[0]
        unresolved = self._conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE resolved_at IS NULL"
        ).fetchone()[0]

        by_priority = {}
        for p in PRIORITY_LEVELS:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE priority = ? AND acknowledged_at IS NULL",
                (p,),
            ).fetchone()[0]
            by_priority[p] = count

        by_type = {}
        for t in ALERT_TYPES:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE alert_type = ? AND acknowledged_at IS NULL",
                (t,),
            ).fetchone()[0]
            if count > 0:
                by_type[t] = count

        return {
            "total": total,
            "unacknowledged": unacknowledged,
            "unresolved": unresolved,
            "by_priority": by_priority,
            "by_type": by_type,
        }

    # ---------------------------------------------------------------------------
    # Callbacks
    # ---------------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for alert events: 'created', 'acknowledged', 'escalated'."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _fire_callbacks(self, event: str, alert: Alert) -> None:
        """Fire all registered callbacks for an event."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(alert.to_dict())
            except Exception as exc:
                logger.error("Alert callback error (%s): %s", event, exc)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_alert(row: sqlite3.Row) -> Alert:
        """Convert a database row to an Alert object."""
        d = dict(row)
        metadata_raw = d.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = metadata_raw or {}

        return Alert(
            id=d["id"],
            alert_type=d["alert_type"],
            title=d["title"],
            message=d["message"],
            priority=d["priority"],
            source=d.get("source", ""),
            threshold=d.get("threshold"),
            current_value=d.get("current_value"),
            metadata=metadata,
            created_at=d["created_at"],
            acknowledged_at=d.get("acknowledged_at"),
            acknowledged_by=d.get("acknowledged_by"),
            escalated_at=d.get("escalated_at"),
            escalated_to=d.get("escalated_to"),
            resolved_at=d.get("resolved_at"),
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: Optional[AlertManager] = None


def get_alert_manager(db_path: str = DEFAULT_DB_PATH) -> AlertManager:
    """Get or create the singleton AlertManager instance."""
    global _manager
    if _manager is None:
        _manager = AlertManager(db_path=db_path)
    return _manager