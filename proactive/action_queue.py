"""
Aethera AI - Action Queue

Prioritized task queue with automatic escalation.

Item types:
- claim_followup: Follow up on submitted claims
- appeal_deadline: Appeal filing deadlines
- credentialing_renewal: Credentialing expiration/renewal
- compliance_task: Regulatory compliance tasks

Priority levels: critical, urgent, normal, low

Auto-escalation: Items that remain incomplete past their due_date
are escalated to the next priority level after a configurable timeout.

Supports: add item, complete item, get next, escalate overdue, get by priority.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("ACTION_QUEUE_DB_PATH", "/data/proactive_action_queue.db")

PRIORITY_LEVELS = ["low", "normal", "urgent", "critical"]
PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITY_LEVELS)}

ITEM_TYPES = [
    "claim_followup",
    "appeal_deadline",
    "credentialing_renewal",
    "compliance_task",
]

# Default escalation timeouts in seconds per priority
DEFAULT_ESCALATION_TIMEOUTS = {
    "low": 172800,       # 48 hours
    "normal": 86400,     # 24 hours
    "urgent": 14400,     # 4 hours
    "critical": 3600,    # 1 hour
}


class ActionItem:
    """Represents a single action item in the queue."""

    __slots__ = (
        "id", "item_type", "title", "description", "priority",
        "due_date", "assigned_to", "source", "metadata",
        "created_at", "updated_at", "completed_at", "completed_by",
        "escalated_at", "escalated_from", "escalation_count",
    )

    def __init__(
        self,
        id: str,
        item_type: str,
        title: str,
        description: str = "",
        priority: str = "normal",
        due_date: Optional[str] = None,
        assigned_to: str = "",
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        completed_by: Optional[str] = None,
        escalated_at: Optional[str] = None,
        escalated_from: Optional[str] = None,
        escalation_count: int = 0,
    ):
        self.id = id
        self.item_type = item_type
        self.title = title
        self.description = description
        self.priority = priority
        self.due_date = due_date
        self.assigned_to = assigned_to
        self.source = source
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or self.created_at
        self.completed_at = completed_at
        self.completed_by = completed_by
        self.escalated_at = escalated_at
        self.escalated_from = escalated_from
        self.escalation_count = escalation_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_type": self.item_type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "due_date": self.due_date,
            "assigned_to": self.assigned_to,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "completed_by": self.completed_by,
            "escalated_at": self.escalated_at,
            "escalated_from": self.escalated_from,
            "escalation_count": self.escalation_count,
        }

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > due
        except (ValueError, TypeError):
            return False

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


class ActionQueue:
    """
    Prioritized task queue with automatic escalation.

    Items are persisted in SQLite. The queue supports:
    - Add items with priority, type, due date
    - Complete items
    - Get next item (highest priority first)
    - Escalate overdue items
    - Get items by priority or type
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        escalation_timeouts: Optional[Dict[str, int]] = None,
    ):
        self._db_path = db_path
        self._escalation_timeouts = escalation_timeouts or DEFAULT_ESCALATION_TIMEOUTS
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the action_items table if it does not exist."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                due_date TEXT,
                assigned_to TEXT DEFAULT '',
                source TEXT DEFAULT '',
                metadata JSON DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                completed_by TEXT,
                escalated_at TEXT,
                escalated_from TEXT,
                escalation_count INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_items_priority ON action_items(priority);
            CREATE INDEX IF NOT EXISTS idx_items_type ON action_items(item_type);
            CREATE INDEX IF NOT EXISTS idx_items_due ON action_items(due_date);
            CREATE INDEX IF NOT EXISTS idx_items_completed ON action_items(completed_at);
        """)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------------
    # Add Item
    # ---------------------------------------------------------------------------

    def add_item(
        self,
        item_type: str,
        title: str,
        description: str = "",
        priority: str = "normal",
        due_date: Optional[str] = None,
        assigned_to: str = "",
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionItem:
        """
        Add a new item to the action queue.

        Args:
            item_type: One of claim_followup, appeal_deadline,
                       credentialing_renewal, compliance_task.
            title: Short description of the action.
            description: Detailed description.
            priority: critical, urgent, normal, or low.
            due_date: ISO 8601 datetime string for the deadline.
            assigned_to: Person or team responsible.
            source: Origin system (e.g., "denial_analyzer", "credentialing_monitor").
            metadata: Additional structured data.

        Returns:
            The created ActionItem.
        """
        if item_type not in ITEM_TYPES:
            logger.warning("Unknown item_type '%s', creating anyway", item_type)
        if priority not in PRIORITY_LEVELS:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of {PRIORITY_LEVELS}")

        now = datetime.now(timezone.utc).isoformat()
        item = ActionItem(
            id=f"act_{uuid.uuid4().hex[:12]}",
            item_type=item_type,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            assigned_to=assigned_to,
            source=source,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self._conn.execute(
            """INSERT INTO action_items
               (id, item_type, title, description, priority, due_date,
                assigned_to, source, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.id, item.item_type, item.title, item.description,
                item.priority, item.due_date, item.assigned_to,
                item.source, json.dumps(item.metadata),
                item.created_at, item.updated_at,
            ),
        )
        self._conn.commit()

        logger.info("Added %s action item [%s]: %s (due: %s)", priority, item.id, title, due_date or "none")
        return item

    # ---------------------------------------------------------------------------
    # Complete Item
    # ---------------------------------------------------------------------------

    def complete_item(self, item_id: str, completed_by: str = "user") -> Optional[ActionItem]:
        """
        Mark an item as completed.

        Returns:
            The completed ActionItem, or None if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM action_items WHERE id = ?", (item_id,)
        ).fetchone()

        if not row:
            logger.warning("Action item %s not found for completion", item_id)
            return None

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE action_items SET completed_at = ?, completed_by = ?, updated_at = ? WHERE id = ?",
            (now, completed_by, now, item_id),
        )
        self._conn.commit()

        item = self._row_to_item(row)
        item.completed_at = now
        item.completed_by = completed_by
        item.updated_at = now
        logger.info("Completed action item %s by %s", item_id, completed_by)
        return item

    # ---------------------------------------------------------------------------
    # Get Next
    # ---------------------------------------------------------------------------

    def get_next(self, assigned_to: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the highest-priority, oldest uncompleted item.

        Optionally filter by assignee.

        Returns:
            Action item dict, or None if queue is empty.
        """
        query = """
            SELECT * FROM action_items
            WHERE completed_at IS NULL
        """
        params: List[Any] = []
        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)

        query += """
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 0
                    WHEN 'urgent' THEN 1
                    WHEN 'normal' THEN 2
                    WHEN 'low' THEN 3
                END ASC,
                due_date ASC NULLS LAST,
                created_at ASC
            LIMIT 1
        """

        row = self._conn.execute(query, params).fetchone()
        if not row:
            return None
        return dict(self._row_to_item(row).to_dict())

    # ---------------------------------------------------------------------------
    # Get by Priority
    # ---------------------------------------------------------------------------

    def get_by_priority(
        self,
        priority: str,
        include_completed: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get items by priority level.

        Args:
            priority: One of critical, urgent, normal, low.
            include_completed: Whether to include completed items.
            limit: Maximum items to return.

        Returns:
            List of action item dicts.
        """
        if priority not in PRIORITY_LEVELS:
            raise ValueError(f"Invalid priority '{priority}'")

        query = "SELECT * FROM action_items WHERE priority = ?"
        params: List[Any] = [priority]

        if not include_completed:
            query += " AND completed_at IS NULL"

        query += " ORDER BY due_date ASC NULLS LAST, created_at ASC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_item(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Get by Type
    # ---------------------------------------------------------------------------

    def get_by_type(
        self,
        item_type: str,
        include_completed: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get items by item type."""
        query = "SELECT * FROM action_items WHERE item_type = ?"
        params: List[Any] = [item_type]

        if not include_completed:
            query += " AND completed_at IS NULL"

        query += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 END, due_date ASC NULLS LAST LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_item(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Escalate Overdue
    # ---------------------------------------------------------------------------

    def escalate_overdue(self) -> List[ActionItem]:
        """
        Escalate items that have exceeded their priority-level timeout.

        Escalation bumps priority up one level (low->normal->urgent->critical).
        Critical items that are overdue are re-notified but stay critical.

        Returns:
            List of escalated ActionItem objects.
        """
        now = datetime.now(timezone.utc)
        escalated: List[ActionItem] = []

        # Only escalate uncompleted items
        rows = self._conn.execute(
            "SELECT * FROM action_items WHERE completed_at IS NULL"
        ).fetchall()

        for row in rows:
            item = self._row_to_item(row)
            try:
                created = datetime.fromisoformat(item.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            age_seconds = (now - created).total_seconds()
            timeout = self._escalation_timeouts.get(item.priority, 86400)

            if age_seconds < timeout:
                continue

            # Already escalated recently? Skip if escalated within last timeout period
            if item.escalated_at:
                try:
                    esc_time = datetime.fromisoformat(item.escalated_at)
                    if esc_time.tzinfo is None:
                        esc_time = esc_time.replace(tzinfo=timezone.utc)
                    if (now - esc_time).total_seconds() < timeout:
                        continue
                except (ValueError, TypeError):
                    pass

            # Escalate priority
            current_rank = PRIORITY_RANK.get(item.priority, 0)
            new_rank = min(current_rank + 1, len(PRIORITY_LEVELS) - 1)
            new_priority = PRIORITY_LEVELS[new_rank]
            old_priority = item.priority

            now_iso = now.isoformat()
            new_count = item.escalation_count + 1

            self._conn.execute(
                """UPDATE action_items
                   SET priority = ?, escalated_at = ?, escalated_from = ?,
                       escalation_count = ?, updated_at = ?
                   WHERE id = ?""",
                (new_priority, now_iso, old_priority, new_count, now_iso, item.id),
            )

            item.priority = new_priority
            item.escalated_at = now_iso
            item.escalated_from = old_priority
            item.escalation_count = new_count
            item.updated_at = now_iso
            escalated.append(item)

            logger.warning(
                "Escalated action item %s from %s to %s (age: %.0fs)",
                item.id, old_priority, new_priority, age_seconds,
            )

        if escalated:
            self._conn.commit()

        return escalated

    # ---------------------------------------------------------------------------
    # Get Overdue Items
    # ---------------------------------------------------------------------------

    def get_overdue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all uncompleted items past their due date."""
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            """SELECT * FROM action_items
               WHERE completed_at IS NULL AND due_date IS NOT NULL AND due_date < ?
               ORDER BY due_date ASC LIMIT ?""",
            (now_iso, limit),
        ).fetchall()
        return [dict(self._row_to_item(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Update Item
    # ---------------------------------------------------------------------------

    def update_item(self, item_id: str, **changes) -> Optional[ActionItem]:
        """Update fields on an existing action item."""
        row = self._conn.execute(
            "SELECT * FROM action_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return None

        allowed_fields = {
            "title", "description", "priority", "due_date",
            "assigned_to", "source", "metadata",
        }
        updates: Dict[str, Any] = {}
        for key, value in changes.items():
            if key in allowed_fields:
                updates[key] = value

        if not updates:
            return self._row_to_item(row)

        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [item_id]

        self._conn.execute(
            f"UPDATE action_items SET {set_clause} WHERE id = ?",
            values,
        )
        self._conn.commit()

        # Re-fetch
        row = self._conn.execute(
            "SELECT * FROM action_items WHERE id = ?", (item_id,)
        ).fetchone()
        item = self._row_to_item(row)
        logger.info("Updated action item %s: %s", item_id, list(updates.keys()))
        return item

    # ---------------------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
        pending = self._conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE completed_at IS NULL"
        ).fetchone()[0]
        completed = self._conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE completed_at IS NOT NULL"
        ).fetchone()[0]
        overdue = self._conn.execute(
            """SELECT COUNT(*) FROM action_items
               WHERE completed_at IS NULL AND due_date IS NOT NULL AND due_date < ?""",
            (datetime.now(timezone.utc).isoformat(),),
        ).fetchone()[0]

        by_priority = {}
        for p in PRIORITY_LEVELS:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE priority = ? AND completed_at IS NULL",
                (p,),
            ).fetchone()[0]
            by_priority[p] = count

        by_type = {}
        for t in ITEM_TYPES:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE item_type = ? AND completed_at IS NULL",
                (t,),
            ).fetchone()[0]
            if count > 0:
                by_type[t] = count

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "overdue": overdue,
            "by_priority": by_priority,
            "by_type": by_type,
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> ActionItem:
        """Convert a database row to an ActionItem."""
        d = dict(row)
        metadata_raw = d.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = metadata_raw or {}

        return ActionItem(
            id=d["id"],
            item_type=d["item_type"],
            title=d["title"],
            description=d.get("description", ""),
            priority=d["priority"],
            due_date=d.get("due_date"),
            assigned_to=d.get("assigned_to", ""),
            source=d.get("source", ""),
            metadata=metadata,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            completed_at=d.get("completed_at"),
            completed_by=d.get("completed_by"),
            escalated_at=d.get("escalated_at"),
            escalated_from=d.get("escalated_from"),
            escalation_count=d.get("escalation_count", 0),
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_queue: Optional[ActionQueue] = None


def get_action_queue(db_path: str = DEFAULT_DB_PATH) -> ActionQueue:
    """Get or create the singleton ActionQueue instance."""
    global _queue
    if _queue is None:
        _queue = ActionQueue(db_path=db_path)
    return _queue