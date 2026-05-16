"""
Aethera AI - Fact Store Module

Verified facts with source tracking and confidence scoring.
Supports: store, search, verify, find contradictions, and expire outdated facts.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class FactStore:
    """
    SQLite-backed fact store with source tracking and confidence scores.

    Schema:
    - facts: id, fact_text, source, source_type, confidence, verified_date,
             category, tags (JSON), status, created_at, updated_at, expires_at
    """

    def __init__(self, db_path: str = "/data/aethera.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self):
        """Initialize database schema."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                fact_text TEXT NOT NULL,
                source TEXT,
                source_type TEXT DEFAULT 'document',
                confidence REAL DEFAULT 0.5,
                verified_date TEXT,
                category TEXT DEFAULT 'general',
                tags JSON,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_facts_category
                ON facts(category);

            CREATE INDEX IF NOT EXISTS idx_facts_status
                ON facts(status);

            CREATE INDEX IF NOT EXISTS idx_facts_confidence
                ON facts(confidence);

            CREATE INDEX IF NOT EXISTS idx_facts_source
                ON facts(source);

            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
                USING FTS5(fact_text, category, tags, source);
        """)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    # ---- Core Operations ----

    def store_fact(
        self,
        fact_text: str,
        source: str = "",
        source_type: str = "document",
        confidence: float = 0.5,
        category: str = "general",
        tags: Optional[List[str]] = None,
        expires_at: Optional[str] = None
    ) -> str:
        """
        Store a new fact.

        Args:
            fact_text: The factual statement
            source: URL, document name, or origin identifier
            source_type: 'document', 'url', 'user', 'system', 'api'
            confidence: 0.0 to 1.0 confidence score
            category: Fact category for grouping
            tags: List of string tags
            expires_at: ISO datetime when this fact should be considered outdated

        Returns:
            Fact ID
        """
        fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO facts
               (id, fact_text, source, source_type, confidence, category,
                tags, status, created_at, updated_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact_id,
                fact_text,
                source,
                source_type,
                max(0.0, min(1.0, confidence)),
                category,
                json.dumps(tags or []),
                "active",
                now,
                now,
                expires_at
            )
        )

        # Insert into FTS index
        try:
            self._conn.execute(
                "INSERT INTO facts_fts (rowid, fact_text, category, tags, source) VALUES (?, ?, ?, ?, ?)",
                (
                    int(fact_id.replace("fact_", ""), 16) % (2**63),
                    fact_text,
                    category,
                    " ".join(tags or []),
                    source
                )
            )
        except Exception:
            pass

        self._conn.commit()
        return fact_id

    def get_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single fact by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM facts WHERE id = ?", (fact_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        fact = dict(row)
        fact["tags"] = json.loads(fact["tags"]) if fact["tags"] else []
        return fact

    def search_facts(
        self,
        query: str,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search for facts.

        Args:
            query: Search query text
            category: Filter by category
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching facts
        """
        results: List[Dict[str, Any]] = []

        # Try FTS5 search first
        try:
            fts_query = query
            if category:
                fts_query = f"{query} {category}"

            cursor = self._conn.execute(
                """SELECT rowid FROM facts_fts WHERE facts_fts MATCH ? LIMIT ?""",
                (fts_query, limit)
            )
            rowids = [row["rowid"] for row in cursor.fetchall()]

            if rowids:
                placeholders = ",".join(["?"] * len(rowids))
                cursor = self._conn.execute(
                    f"""SELECT * FROM facts
                        WHERE id IN (
                            SELECT id FROM facts WHERE rowid IN ({placeholders})
                        ) AND confidence >= ?
                        ORDER BY confidence DESC""",
                    rowids + [min_confidence]
                )
                for row in cursor.fetchall():
                    fact = dict(row)
                    fact["tags"] = json.loads(fact["tags"]) if fact["tags"] else []
                    results.append(fact)
        except Exception:
            pass

        # Fallback: LIKE search if FTS yields nothing
        if not results:
            conditions = ["fact_text LIKE ?", "confidence >= ?"]
            params: List[Any] = [f"%{query}%", min_confidence]
            if category:
                conditions.append("category = ?")
                params.append(category)

            where = " AND ".join(conditions)
            cursor = self._conn.execute(
                f"SELECT * FROM facts WHERE {where} ORDER BY confidence DESC LIMIT ?",
                params + [limit]
            )
            for row in cursor.fetchall():
                fact = dict(row)
                fact["tags"] = json.loads(fact["tags"]) if fact["tags"] else []
                results.append(fact)

        return results

    def get_by_category(
        self,
        category: str,
        status: str = "active",
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all facts in a category.

        Args:
            category: Category name
            status: Filter by status
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of facts
        """
        cursor = self._conn.execute(
            """SELECT * FROM facts
               WHERE category = ? AND status = ? AND confidence >= ?
               ORDER BY confidence DESC, updated_at DESC
               LIMIT ?""",
            (category, status, min_confidence, limit)
        )

        results = []
        for row in cursor.fetchall():
            fact = dict(row)
            fact["tags"] = json.loads(fact["tags"]) if fact["tags"] else []
            results.append(fact)

        return results

    # ---- Verification ----

    def verify_fact(self, fact_id: str, new_confidence: Optional[float] = None) -> bool:
        """
        Mark a fact as verified, optionally updating its confidence.

        Args:
            fact_id: Fact to verify
            new_confidence: Updated confidence score (None = keep existing)

        Returns:
            True if fact was found and updated
        """
        now = datetime.now().isoformat()

        if new_confidence is not None:
            new_confidence = max(0.0, min(1.0, new_confidence))
            self._conn.execute(
                """UPDATE facts
                   SET verified_date = ?, confidence = ?, updated_at = ?
                   WHERE id = ?""",
                (now, new_confidence, now, fact_id)
            )
        else:
            self._conn.execute(
                """UPDATE facts
                   SET verified_date = ?, updated_at = ?
                   WHERE id = ?""",
                (now, now, fact_id)
            )

        self._conn.commit()
        return self._conn.total_changes > 0

    def find_contradictions(self) -> List[Dict[str, Any]]:
        """
        Find pairs of facts that may contradict each other.

        Uses heuristics:
        - Negation detection: one fact contains a negated form of another
        - Opposing values: "active" vs "resolved", "increased" vs "decreased"
        - Same entity with conflicting attribute values

        Returns:
            List of contradiction candidates: {fact_a, fact_b, reason}
        """
        contradictions: List[Dict[str, Any]] = []

        # Get all active facts
        cursor = self._conn.execute(
            "SELECT * FROM facts WHERE status = 'active' ORDER BY category, created_at"
        )
        facts = []
        for row in cursor.fetchall():
            fact = dict(row)
            fact["tags"] = json.loads(fact["tags"]) if fact["tags"] else []
            facts.append(fact)

        # Opposing term pairs
        opposing_terms = [
            ("active", "resolved"),
            ("active", "inactive"),
            ("increased", "decreased"),
            ("positive", "negative"),
            ("present", "absent"),
            ("elevated", "low"),
            ("high", "low"),
            ("yes", "no"),
            ("true", "false"),
            ("approved", "denied"),
            ("covered", "excluded"),
        ]

        negation_words = {"not", "never", "no", "denies", "denied", "doesn't",
                          "does not", "isn't", "is not", "cannot", "can't",
                          "won't", "will not", "neither", "nor", "without"}

        # Compare facts within same category
        by_category: Dict[str, List[Dict]] = {}
        for f in facts:
            cat = f.get("category", "general")
            by_category.setdefault(cat, []).append(f)

        for cat, cat_facts in by_category.items():
            for i, fact_a in enumerate(cat_facts):
                for fact_b in cat_facts[i + 1:]:
                    reason = self._check_contradiction(
                        fact_a["fact_text"], fact_b["fact_text"],
                        negation_words, opposing_terms
                    )
                    if reason:
                        contradictions.append({
                            "fact_a": fact_a,
                            "fact_b": fact_b,
                            "reason": reason
                        })

        return contradictions

    def _check_contradiction(
        self,
        text_a: str,
        text_b: str,
        negation_words: set,
        opposing_terms: list
    ) -> Optional[str]:
        """
        Check if two fact texts may contradict each other.

        Returns reason string or None.
        """
        words_a = set(re.findall(r"\b\w+\b", text_a.lower()))
        words_b = set(re.findall(r"\b\w+\b", text_b.lower()))

        # Check negation: one contains a negation word the other doesn't
        neg_a = words_a & negation_words
        neg_b = words_b & negation_words

        if neg_a != neg_b:
            # Check if the non-negated words overlap significantly
            content_a = words_a - negation_words
            content_b = words_b - negation_words
            overlap = content_a & content_b
            if len(overlap) >= 2:
                if neg_a and not neg_b:
                    return f"Negation conflict: '{text_a[:80]}' negates terms also in '{text_b[:80]}'"
                if neg_b and not neg_a:
                    return f"Negation conflict: '{text_b[:80]}' negates terms also in '{text_a[:80]}'"

        # Check opposing value pairs
        for term_pos, term_neg in opposing_terms:
            if term_pos in words_a and term_neg in words_b:
                return f"Opposing values: '{term_pos}' vs '{term_neg}'"
            if term_neg in words_a and term_pos in words_b:
                return f"Opposing values: '{term_neg}' vs '{term_pos}'"

        return None

    # ---- Expiration ----

    def expire_outdated(self, dry_run: bool = False) -> List[str]:
        """
        Mark facts past their expiration date as expired.

        Args:
            dry_run: If True, return IDs that would be expired without changing them

        Returns:
            List of expired fact IDs
        """
        now = datetime.now().isoformat()

        cursor = self._conn.execute(
            """SELECT id FROM facts
               WHERE expires_at IS NOT NULL
                 AND expires_at <= ?
                 AND status = 'active'""",
            (now,)
        )

        expired_ids = [row["id"] for row in cursor.fetchall()]

        if not dry_run and expired_ids:
            placeholders = ",".join(["?"] * len(expired_ids))
            self._conn.execute(
                f"""UPDATE facts
                    SET status = 'expired', updated_at = ?
                    WHERE id IN ({placeholders})""",
                [now] + expired_ids
            )
            self._conn.commit()

        return expired_ids

    def set_expiration(self, fact_id: str, expires_at: str) -> bool:
        """
        Set or update the expiration date for a fact.

        Args:
            fact_id: Fact to update
            expires_at: ISO datetime string

        Returns:
            True if updated
        """
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE facts SET expires_at = ?, updated_at = ? WHERE id = ?",
            (expires_at, now, fact_id)
        )
        self._conn.commit()
        return self._conn.total_changes > 0

    def store_facts_batch(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store multiple facts in a single transaction.

        Args:
            facts: List of dicts with keys: fact_text, source, source_type,
                   confidence, category, tags, expires_at

        Returns:
            List of fact IDs
        """
        fact_ids = []
        now = datetime.now().isoformat()
        try:
            for f in facts:
                fact_id = f"fact_{uuid.uuid4().hex[:12]}"
                fact_ids.append(fact_id)
                self._conn.execute(
                    """INSERT INTO facts
                       (id, fact_text, source, source_type, confidence, category,
                        tags, status, created_at, updated_at, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fact_id,
                        f.get("fact_text", ""),
                        f.get("source", ""),
                        f.get("source_type", "document"),
                        max(0.0, min(1.0, f.get("confidence", 0.5))),
                        f.get("category", "general"),
                        json.dumps(f.get("tags") or []),
                        "active",
                        now,
                        now,
                        f.get("expires_at"),
                    )
                )
                try:
                    self._conn.execute(
                        "INSERT INTO facts_fts (rowid, fact_text, category, tags, source) VALUES (?, ?, ?, ?, ?)",
                        (
                            int(fact_id.replace("fact_", ""), 16) % (2**63),
                            f.get("fact_text", ""),
                            f.get("category", "general"),
                            " ".join(f.get("tags") or []),
                            f.get("source", ""),
                        )
                    )
                except Exception:
                    pass
            self._conn.commit()
        except Exception:
            self._conn.rollback()
        return fact_ids

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get fact store statistics."""
        total_cursor = self._conn.execute("SELECT COUNT(*) as count FROM facts")
        total = total_cursor.fetchone()["count"]

        status_cursor = self._conn.execute(
            "SELECT status, COUNT(*) as count FROM facts GROUP BY status"
        )
        by_status = {row["status"]: row["count"] for row in status_cursor.fetchall()}

        category_cursor = self._conn.execute(
            "SELECT category, COUNT(*) as count FROM facts GROUP BY category"
        )
        by_category = {row["category"]: row["count"] for row in category_cursor.fetchall()}

        avg_confidence_cursor = self._conn.execute(
            "SELECT AVG(confidence) as avg FROM facts WHERE status = 'active'"
        )
        avg_confidence = avg_confidence_cursor.fetchone()["avg"] or 0.0

        unverified_cursor = self._conn.execute(
            """SELECT COUNT(*) as count FROM facts
               WHERE status = 'active' AND verified_date IS NULL"""
        )
        unverified = unverified_cursor.fetchone()["count"]

        return {
            "total_facts": total,
            "by_status": by_status,
            "by_category": by_category,
            "average_confidence": round(avg_confidence, 3),
            "unverified_count": unverified
        }


# Singleton instance
_fact_store: Optional[FactStore] = None


def get_fact_store(db_path: str = "/data/aethera.db") -> FactStore:
    """Get or create the fact store instance."""
    global _fact_store
    if _fact_store is None:
        _fact_store = FactStore(db_path)
    return _fact_store