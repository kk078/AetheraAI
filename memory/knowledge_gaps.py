"""
Aethera AI - Knowledge Gaps Module

Track and auto-fill knowledge gaps. Identifies topics where Aethera
lacks sufficient information and manages the research lifecycle.

Tracks: gap topic, detected_from (query that revealed gap), priority,
research_status, filled_date.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class KnowledgeGapStore:
    """
    SQLite-backed knowledge gap tracker.

    Schema:
    - knowledge_gaps: id, topic, description, detected_from, detected_date,
      priority, category, research_status, research_notes, filled_date,
      source_url, created_at, updated_at
    """

    # Valid research statuses and their allowed transitions
    VALID_STATUSES = {"detected", "researching", "filled", "expired", "irrelevant"}

    STATUS_TRANSITIONS = {
        "detected": {"researching", "expired", "irrelevant"},
        "researching": {"filled", "expired", "irrelevant"},
        "filled": set(),  # Terminal state
        "expired": set(),  # Terminal state
        "irrelevant": set(),  # Terminal state
    }

    def __init__(self, db_path: str = "/data/aethera.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self):
        """Initialize database schema."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                description TEXT,
                detected_from TEXT,
                detected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority INTEGER DEFAULT 5,
                category TEXT DEFAULT 'general',
                research_status TEXT DEFAULT 'detected',
                research_notes JSON,
                filled_date TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_gaps_status
                ON knowledge_gaps(research_status);

            CREATE INDEX IF NOT EXISTS idx_gaps_priority
                ON knowledge_gaps(priority DESC);

            CREATE INDEX IF NOT EXISTS idx_gaps_category
                ON knowledge_gaps(category);

            CREATE INDEX IF NOT EXISTS idx_gaps_topic
                ON knowledge_gaps(topic);
        """)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    # ---- Gap Detection ----

    def detect_gap(
        self,
        topic: str,
        detected_from: str = "",
        description: str = "",
        priority: int = 5,
        category: str = "general"
    ) -> str:
        """
        Record a newly detected knowledge gap.

        If a gap for this topic already exists and is still active,
        updates its priority instead of creating a duplicate.

        Args:
            topic: The topic area where knowledge is lacking
            detected_from: The query or interaction that revealed the gap
            description: Human-readable description of the gap
            priority: 1 (low) to 10 (critical)
            category: Domain category

        Returns:
            Gap ID
        """
        # Check for existing active gap on the same topic
        cursor = self._conn.execute(
            """SELECT id, priority, research_status FROM knowledge_gaps
               WHERE topic = ? AND research_status IN ('detected', 'researching')""",
            (topic,)
        )
        existing = cursor.fetchone()

        if existing:
            # Bump priority if this gap is being detected again
            new_priority = max(existing["priority"], priority)
            now = datetime.now().isoformat()
            self._conn.execute(
                """UPDATE knowledge_gaps
                   SET priority = ?, updated_at = ?
                   WHERE id = ?""",
                (new_priority, now, existing["id"])
            )
            self._conn.commit()
            return existing["id"]

        gap_id = f"gap_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO knowledge_gaps
               (id, topic, description, detected_from, detected_date,
                priority, category, research_status, research_notes,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                gap_id, topic, description, detected_from, now,
                max(1, min(10, priority)), category, "detected",
                json.dumps([]), now, now
            )
        )
        self._conn.commit()
        return gap_id

    def list_gaps(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        min_priority: int = 1,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List knowledge gaps with optional filtering.

        Args:
            status: Filter by research status
            category: Filter by category
            min_priority: Minimum priority threshold
            limit: Maximum results
            offset: Result offset

        Returns:
            List of gap records
        """
        conditions = ["priority >= ?"]
        params: List[Any] = [min_priority]

        if status:
            conditions.append("research_status = ?")
            params.append(status)

        if category:
            conditions.append("category = ?")
            params.append(category)

        where = " AND ".join(conditions)

        cursor = self._conn.execute(
            f"""SELECT * FROM knowledge_gaps
                WHERE {where}
                ORDER BY priority DESC, detected_date ASC
                LIMIT ? OFFSET ?""",
            params + [limit, offset]
        )

        results = []
        for row in cursor.fetchall():
            gap = dict(row)
            gap["research_notes"] = json.loads(gap["research_notes"]) if gap["research_notes"] else []
            results.append(gap)

        return results

    def get_gap(self, gap_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single gap by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM knowledge_gaps WHERE id = ?", (gap_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        gap = dict(row)
        gap["research_notes"] = json.loads(gap["research_notes"]) if gap["research_notes"] else []
        return gap

    def research_gap(self, gap_id: str, notes: Optional[str] = None) -> bool:
        """
        Mark a gap for research (overnight or background research).

        Transitions status from 'detected' to 'researching'.

        Args:
            gap_id: Gap to mark for research
            notes: Optional research notes

        Returns:
            True if transition succeeded
        """
        gap = self.get_gap(gap_id)
        if not gap:
            return False

        current_status = gap["research_status"]
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())

        if "researching" not in allowed:
            return False

        now = datetime.now().isoformat()
        existing_notes = gap.get("research_notes", [])

        if notes:
            existing_notes.append({
                "note": notes,
                "added_at": now,
                "action": "research_started"
            })

        self._conn.execute(
            """UPDATE knowledge_gaps
               SET research_status = 'researching',
                   research_notes = ?,
                   updated_at = ?
               WHERE id = ?""",
            (json.dumps(existing_notes), now, gap_id)
        )
        self._conn.commit()
        return True

    def mark_filled(
        self,
        gap_id: str,
        source_url: str = "",
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark a gap as filled with research results.

        Transitions status to 'filled'.

        Args:
            gap_id: Gap to mark as filled
            source_url: URL or reference where the information was found
            notes: Notes about the research findings

        Returns:
            True if transition succeeded
        """
        gap = self.get_gap(gap_id)
        if not gap:
            return False

        current_status = gap["research_status"]
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())

        if "filled" not in allowed:
            return False

        now = datetime.now().isoformat()
        existing_notes = gap.get("research_notes", [])

        if notes:
            existing_notes.append({
                "note": notes,
                "added_at": now,
                "action": "filled"
            })

        self._conn.execute(
            """UPDATE knowledge_gaps
               SET research_status = 'filled',
                   filled_date = ?,
                   source_url = ?,
                   research_notes = ?,
                   updated_at = ?
               WHERE id = ?""",
            (now, source_url, json.dumps(existing_notes), now, gap_id)
        )
        self._conn.commit()
        return True

    def mark_expired(self, gap_id: str, reason: str = "") -> bool:
        """
        Mark a gap as expired (no longer relevant).

        Args:
            gap_id: Gap to expire
            reason: Reason for expiration

        Returns:
            True if transition succeeded
        """
        gap = self.get_gap(gap_id)
        if not gap:
            return False

        current_status = gap["research_status"]
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())

        if "expired" not in allowed:
            return False

        now = datetime.now().isoformat()
        existing_notes = gap.get("research_notes", [])
        existing_notes.append({
            "note": reason or "Expired",
            "added_at": now,
            "action": "expired"
        })

        self._conn.execute(
            """UPDATE knowledge_gaps
               SET research_status = 'expired',
                   research_notes = ?,
                   updated_at = ?
               WHERE id = ?""",
            (json.dumps(existing_notes), now, gap_id)
        )
        self._conn.commit()
        return True

    def mark_irrelevant(self, gap_id: str, reason: str = "") -> bool:
        """
        Mark a gap as irrelevant.

        Args:
            gap_id: Gap to mark irrelevant
            reason: Reason

        Returns:
            True if transition succeeded
        """
        gap = self.get_gap(gap_id)
        if not gap:
            return False

        current_status = gap["research_status"]
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())

        if "irrelevant" not in allowed:
            return False

        now = datetime.now().isoformat()
        existing_notes = gap.get("research_notes", [])
        existing_notes.append({
            "note": reason or "Marked irrelevant",
            "added_at": now,
            "action": "irrelevant"
        })

        self._conn.execute(
            """UPDATE knowledge_gaps
               SET research_status = 'irrelevant',
                   research_notes = ?,
                   updated_at = ?
               WHERE id = ?""",
            (json.dumps(existing_notes), now, gap_id)
        )
        self._conn.commit()
        return True

    def add_research_note(self, gap_id: str, note: str) -> bool:
        """
        Add a research note to a gap without changing its status.

        Args:
            gap_id: Gap to annotate
            note: Note text

        Returns:
            True if gap was found
        """
        gap = self.get_gap(gap_id)
        if not gap:
            return False

        now = datetime.now().isoformat()
        existing_notes = gap.get("research_notes", [])
        existing_notes.append({
            "note": note,
            "added_at": now,
            "action": "note"
        })

        self._conn.execute(
            """UPDATE knowledge_gaps
               SET research_notes = ?, updated_at = ?
               WHERE id = ?""",
            (json.dumps(existing_notes), now, gap_id)
        )
        self._conn.commit()
        return True

    # ---- Auto-detection Helpers ----

    def auto_detect_from_query(self, query: str, low_confidence_response: bool = False) -> Optional[str]:
        """
        Analyze a query to detect potential knowledge gaps.

        Looks for patterns like:
        - Queries about very specific drugs/codes without known context
        - Questions about recent regulatory changes
        - Low-confidence responses from the system

        Args:
            query: User query text
            low_confidence_response: Whether the system gave a low-confidence answer

        Returns:
            Gap ID if a gap was detected, None otherwise
        """
        # Healthcare-specific gap indicators
        gap_patterns = [
            (r"\b(?:ICD-10|CPT|HCPCS)\s+code\s+(\w+)", "medical_coding",
             "Medical code lookup: {0}"),
            (r"\b(?:formulary|coverage)\s+(?:for|of)\s+([\w\s]+)", "insurance",
             "Insurance formulary/coverage query: {0}"),
            (r"\b(?:guideline|recommendation)\s+(?:for|on)\s+([\w\s]+)", "clinical_guidelines",
             "Clinical guideline query: {0}"),
            (r"\b(?:interaction|contraindication)\s+(?:between|with)\s+([\w\s]+)", "drug_interactions",
             "Drug interaction query: {0}"),
            (r"\b(?:latest|recent|new|updated)\s+([\w\s]+?)\s+(?:regulation|rule|policy|law)", "regulatory",
             "Recent regulatory query: {0}"),
            (r"\b(?:does|is)\s+([\w]+)\s+(?:cover|covered)\s+(?:by|under)", "coverage",
             "Coverage verification: {0}"),
        ]

        for pattern, category, description_template in gap_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                description = description_template.format(topic)
                priority = 7 if low_confidence_response else 5
                return self.detect_gap(
                    topic=topic,
                    detected_from=query,
                    description=description,
                    priority=priority,
                    category=category
                )

        # If low confidence and no specific pattern, create a general gap
        if low_confidence_response:
            keywords = re.findall(r"\b[a-z]{4,}\b", query.lower())
            topic = " ".join(keywords[:3]) if keywords else query[:50]
            return self.detect_gap(
                topic=topic,
                detected_from=query,
                description=f"Low confidence response to: {query[:200]}",
                priority=6,
                category="general"
            )

        return None

    # ---- Batch Operations ----

    def get_gaps_for_research(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get gaps that should be queued for research.

        Returns detected gaps sorted by priority (highest first).

        Args:
            limit: Maximum gaps to return

        Returns:
            List of gap records ready for research
        """
        cursor = self._conn.execute(
            """SELECT * FROM knowledge_gaps
               WHERE research_status = 'detected'
               ORDER BY priority DESC, detected_date ASC
               LIMIT ?""",
            (limit,)
        )

        results = []
        for row in cursor.fetchall():
            gap = dict(row)
            gap["research_notes"] = json.loads(gap["research_notes"]) if gap["research_notes"] else []
            results.append(gap)

        return results

    def get_stale_gaps(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get gaps that have been in 'detected' or 'researching' status
        for longer than the specified number of days.

        Args:
            days: Staleness threshold in days

        Returns:
            List of stale gap records
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = self._conn.execute(
            """SELECT * FROM knowledge_gaps
               WHERE research_status IN ('detected', 'researching')
                 AND detected_date < ?
               ORDER BY priority DESC""",
            (cutoff,)
        )

        results = []
        for row in cursor.fetchall():
            gap = dict(row)
            gap["research_notes"] = json.loads(gap["research_notes"]) if gap["research_notes"] else []
            results.append(gap)

        return results

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge gap statistics."""
        total_cursor = self._conn.execute("SELECT COUNT(*) as count FROM knowledge_gaps")
        total = total_cursor.fetchone()["count"]

        status_cursor = self._conn.execute(
            "SELECT research_status, COUNT(*) as count FROM knowledge_gaps GROUP BY research_status"
        )
        by_status = {row["research_status"]: row["count"] for row in status_cursor.fetchall()}

        category_cursor = self._conn.execute(
            "SELECT category, COUNT(*) as count FROM knowledge_gaps GROUP BY category"
        )
        by_category = {row["category"]: row["count"] for row in category_cursor.fetchall()}

        avg_priority_cursor = self._conn.execute(
            "SELECT AVG(priority) as avg FROM knowledge_gaps WHERE research_status IN ('detected', 'researching')"
        )
        avg_priority = avg_priority_cursor.fetchone()["avg"] or 0.0

        return {
            "total_gaps": total,
            "by_status": by_status,
            "by_category": by_category,
            "average_open_priority": round(avg_priority, 2),
            "open_gaps": by_status.get("detected", 0) + by_status.get("researching", 0)
        }


# Singleton instance
_knowledge_gap_store: Optional[KnowledgeGapStore] = None


def get_knowledge_gap_store(db_path: str = "/data/aethera.db") -> KnowledgeGapStore:
    """Get or create the knowledge gap store instance."""
    global _knowledge_gap_store
    if _knowledge_gap_store is None:
        _knowledge_gap_store = KnowledgeGapStore(db_path)
    return _knowledge_gap_store