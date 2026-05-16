"""
Aethera AI - Temporal Intelligence

Time-aware processing for deadlines, scheduling, and time-sensitive information.
Persists items to SQLite for durability across restarts.
"""
import json
import logging
import sqlite3
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("aethera.temporal")


@dataclass
class TimeSensitiveItem:
    """Item with time sensitivity."""
    id: str
    description: str
    deadline: Optional[str] = None  # ISO format string for JSON serialization
    priority: str = "medium"
    category: str = "general"
    created_at: str = ""
    completed: bool = False

    def get_deadline_dt(self) -> Optional[datetime]:
        if not self.deadline:
            return None
        try:
            return datetime.fromisoformat(self.deadline)
        except (ValueError, TypeError):
            return None


class TemporalProcessor:
    """
    Processes time-sensitive information and deadlines.

    Healthcare examples:
    - Appeal deadlines (typically 30-180 days from denial)
    - Prior authorization expiration
    - CMS reporting deadlines
    - Quality measure submission windows
    """

    DEADLINE_TEMPLATES = {
        "claim_appeal": {"days": 30, "description": "Claim appeal deadline"},
        "prior_auth": {"days": 90, "description": "Prior authorization validity"},
        "cms_report": {"days": 60, "description": "CMS quality reporting"},
        "star_appeal": {"days": 60, "description": "Star rating appeal"},
        "enrollment": {"days": 30, "description": "Provider enrollment deadline"},
        "medicare_appeal": {"days": 120, "description": "Medicare Level 1 appeal deadline"},
        "credentialing": {"days": 60, "description": "Credentialing revalidation"},
        "claim_filing": {"days": 365, "description": "Claim filing deadline (varies by payer)"},
    }

    def __init__(self, db_path: str = "/data/aethera_temporal.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Initialize SQLite database."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS temporal_items (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                deadline TEXT,
                priority TEXT DEFAULT 'medium',
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    def add_item(
        self,
        description: str,
        deadline: Optional[datetime] = None,
        deadline_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        priority: str = "medium",
        category: str = "general",
    ) -> TimeSensitiveItem:
        """Add a time-sensitive item."""
        if deadline_type and deadline_type in self.DEADLINE_TEMPLATES:
            template = self.DEADLINE_TEMPLATES[deadline_type]
            from_date = from_date or datetime.now()
            deadline = from_date + timedelta(days=template["days"])

        now = datetime.now()
        item = TimeSensitiveItem(
            id=f"tsi_{int(now.timestamp() * 1000)}",
            description=description,
            deadline=deadline.isoformat() if deadline else None,
            priority=priority,
            category=category,
            created_at=now.isoformat(),
        )

        self._conn.execute(
            "INSERT INTO temporal_items (id, description, deadline, priority, category, created_at, completed) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (item.id, item.description, item.deadline, item.priority, item.category, item.created_at),
        )
        self._conn.commit()
        return item

    def get_upcoming(self, days: int = 7) -> List[TimeSensitiveItem]:
        """Get items due within specified days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        rows = self._conn.execute(
            "SELECT id, description, deadline, priority, category, created_at, completed FROM temporal_items WHERE completed = 0 ORDER BY deadline"
        ).fetchall()

        upcoming = []
        for row in rows:
            item = TimeSensitiveItem(
                id=row[0], description=row[1], deadline=row[2],
                priority=row[3], category=row[4], created_at=row[5], completed=bool(row[6]),
            )
            dl = item.get_deadline_dt()
            if dl and now <= dl <= cutoff:
                upcoming.append(item)
        return upcoming

    def get_overdue(self) -> List[TimeSensitiveItem]:
        """Get overdue items."""
        now = datetime.now()

        rows = self._conn.execute(
            "SELECT id, description, deadline, priority, category, created_at, completed FROM temporal_items WHERE completed = 0 AND deadline IS NOT NULL ORDER BY deadline"
        ).fetchall()

        overdue = []
        for row in rows:
            item = TimeSensitiveItem(
                id=row[0], description=row[1], deadline=row[2],
                priority=row[3], category=row[4], created_at=row[5], completed=bool(row[6]),
            )
            dl = item.get_deadline_dt()
            if dl and dl < now:
                overdue.append(item)
        return overdue

    def complete_item(self, item_id: str) -> bool:
        """Mark an item as completed."""
        cursor = self._conn.execute("UPDATE temporal_items SET completed = 1 WHERE id = ?", (item_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def remove_item(self, item_id: str) -> bool:
        """Remove an item by ID."""
        cursor = self._conn.execute("DELETE FROM temporal_items WHERE id = ?", (item_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_all_items(self) -> List[TimeSensitiveItem]:
        """Get all items (including completed)."""
        rows = self._conn.execute(
            "SELECT id, description, deadline, priority, category, created_at, completed FROM temporal_items ORDER BY deadline"
        ).fetchall()
        return [
            TimeSensitiveItem(
                id=row[0], description=row[1], deadline=row[2],
                priority=row[3], category=row[4], created_at=row[5], completed=bool(row[6]),
            )
            for row in rows
        ]

    def parse_deadline_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse deadline information from natural language text.

        Examples:
        - "Appeal must be filed within 30 days of denial"
        - "Prior auth expires on December 31, 2024"
        - "Submit by end of quarter"
        - "Due in 60 days"
        """
        # Pattern: "within X days" or "in X days"
        days_match = re.search(r'(?:within|in)\s+(\d+)\s+days?', text, re.IGNORECASE)
        if days_match:
            days = int(days_match.group(1))
            return {
                "type": "relative",
                "days": days,
                "deadline": (datetime.now() + timedelta(days=days)).isoformat(),
            }

        # Pattern: "by MM/DD/YYYY" or "on MM/DD/YYYY"
        date_match = re.search(r'(?:by|on|before)\s+(\d{1,2}/\d{1,2}/\d{4})', text)
        if date_match:
            date_str = date_match.group(1)
            try:
                deadline = datetime.strptime(date_str, "%m/%d/%Y")
                return {"type": "absolute", "deadline": deadline.isoformat()}
            except ValueError:
                pass

        # Pattern: "by Month DD, YYYY" (e.g., "by December 31, 2025")
        month_date_match = re.search(
            r'(?:by|on|before)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            text, re.IGNORECASE
        )
        if month_date_match:
            try:
                deadline = datetime.strptime(
                    f"{month_date_match.group(1)} {month_date_match.group(2)} {month_date_match.group(3)}",
                    "%B %d %Y"
                )
                return {"type": "absolute", "deadline": deadline.isoformat()}
            except ValueError:
                pass

        # Pattern: "end of month"
        if "end of month" in text.lower():
            now = datetime.now()
            if now.month == 12:
                deadline = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                deadline = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
            return {"type": "absolute", "deadline": deadline.isoformat()}

        # Pattern: "end of quarter"
        if "end of quarter" in text.lower():
            now = datetime.now()
            quarter_end_month = ((now.month - 1) // 3 + 1) * 3
            if quarter_end_month == 12:
                deadline = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                deadline = datetime(now.year, quarter_end_month + 1, 1) - timedelta(days=1)
            return {"type": "absolute", "deadline": deadline.isoformat()}

        # Pattern: "end of year"
        if "end of year" in text.lower():
            now = datetime.now()
            deadline = datetime(now.year, 12, 31)
            return {"type": "absolute", "deadline": deadline.isoformat()}

        return None

    def get_healthcare_deadline(self, event_type: str, event_date: datetime) -> Dict[str, Any]:
        """Get standard healthcare deadline for an event type."""
        templates = {
            "claim_denial": {"days": 30, "description": "Standard claim appeal deadline"},
            "medicare_denial": {"days": 120, "description": "Medicare appeal deadline (Level 1)"},
            "medicare_redetermination": {"days": 180, "description": "Medicare redetermination deadline"},
            "prior_auth_granted": {"days": 90, "description": "Typical prior auth validity period"},
            "service_date": {"days": 365, "description": "Claim filing deadline (varies by payer)"},
            "enrollment_effective": {"days": 90, "description": "Credentialing revalidation"},
            "cms_quality_report": {"days": 60, "description": "CMS quality reporting deadline"},
        }

        template = templates.get(event_type, {"days": 30, "description": "Standard deadline"})

        return {
            "event_type": event_type,
            "event_date": event_date.isoformat(),
            "deadline": (event_date + timedelta(days=template["days"])).isoformat(),
            "days": template["days"],
            "description": template["description"],
        }

    def extract_deadlines_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract all deadline mentions from text and create time-sensitive items."""
        items = []

        # Check for explicit deadline mentions
        parsed = self.parse_deadline_from_text(text)
        if parsed:
            priority = "high" if parsed.get("days", 999) and parsed["days"] <= 14 else "medium"
            item = self.add_item(
                description=f"Deadline detected: {text[:200]}",
                deadline=datetime.fromisoformat(parsed["deadline"]) if parsed.get("deadline") else None,
                priority=priority,
                category="healthcare" if any(kw in text.lower() for kw in ["appeal", "denial", "auth", "claim", "medicare"]) else "general",
            )
            items.append({"id": item.id, "deadline": item.deadline, "priority": item.priority})

        # Check for healthcare-specific event types
        healthcare_patterns = {
            r'appeal.*(?:denied?|denial)': ("claim_denial", 30),
            r'medicare.*(?:appeal|redetermin)': ("medicare_denial", 120),
            r'prior\s*auth(?:orization)?': ("prior_auth_granted", 90),
            r'credentialing': ("enrollment_effective", 90),
        }

        for pattern, (event_type, days) in healthcare_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                deadline = datetime.now() + timedelta(days=days)
                item = self.add_item(
                    description=f"Healthcare deadline: {event_type} - {days} days from now",
                    deadline=deadline,
                    priority="high" if days <= 30 else "medium",
                    category="healthcare",
                    deadline_type=event_type,
                )
                items.append({"id": item.id, "deadline": item.deadline, "priority": item.priority})

        return items

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()


# Singleton instance
_processor: Optional[TemporalProcessor] = None


def get_temporal_processor(db_path: str = "/data/aethera_temporal.db") -> TemporalProcessor:
    """Get the temporal processor."""
    global _processor
    if _processor is None:
        _processor = TemporalProcessor(db_path)
    return _processor