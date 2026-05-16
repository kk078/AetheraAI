"""
Aethera AI - Skill Effectiveness Tracker

Tracks skill invocations, user feedback, and effectiveness scores.
Uses SQLite for persistence across sessions.

Effectiveness score = (success_rate * 0.4) + (avg_rating / 5 * 0.3) +
                      (1 - min(avg_execution_time_ms / 10000, 1)) * 0.3)
"""

import sqlite3
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("aethera.skills.effectiveness")


class SkillEffectivenessTracker:
    """
    SQLite-backed skill effectiveness tracking.

    Tables:
    - skill_invocations: per-invocation records
    - skill_feedback: user ratings and text feedback
    - skill_effectiveness_summary: aggregated effectiveness scores
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
            CREATE TABLE IF NOT EXISTS skill_invocations (
                id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                user_id TEXT,
                input_hash TEXT,
                success BOOLEAN NOT NULL,
                execution_time_ms REAL,
                error TEXT,
                invoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_feedback (
                id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                user_id TEXT,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                feedback_text TEXT,
                context JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_effectiveness_summary (
                skill_name TEXT PRIMARY KEY,
                total_invocations INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                avg_rating REAL DEFAULT 0.0,
                avg_execution_time_ms REAL DEFAULT 0.0,
                last_invoked TIMESTAMP,
                effectiveness_score REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_invocations_skill
                ON skill_invocations(skill_name);

            CREATE INDEX IF NOT EXISTS idx_invocations_time
                ON skill_invocations(invoked_at);

            CREATE INDEX IF NOT EXISTS idx_feedback_skill
                ON skill_feedback(skill_name);

            CREATE INDEX IF NOT EXISTS idx_feedback_created
                ON skill_feedback(created_at);
        """)

        self._conn.commit()
        logger.info("Skill effectiveness tracker initialized")

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        return self._conn

    def record_invocation(
        self,
        skill_name: str,
        success: bool,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None,
        user_id: str = "default",
        input_hash: Optional[str] = None,
    ) -> str:
        """Record a skill invocation."""
        inv_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO skill_invocations
               (id, skill_name, user_id, input_hash, success, execution_time_ms, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (inv_id, skill_name, user_id, input_hash, success, execution_time_ms, error),
        )
        conn.commit()
        self._update_effectiveness(skill_name)
        return inv_id

    def record_feedback(
        self,
        skill_name: str,
        rating: int,
        feedback_text: Optional[str] = None,
        context: Optional[Dict] = None,
        user_id: str = "default",
    ) -> str:
        """Record user feedback for a skill."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        fb_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO skill_feedback
               (id, skill_name, user_id, rating, feedback_text, context)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fb_id, skill_name, user_id, rating, feedback_text,
             json.dumps(context) if context else None),
        )
        conn.commit()
        self._update_effectiveness(skill_name)
        return fb_id

    def get_effectiveness(self, skill_name: str) -> Optional[Dict]:
        """Get effectiveness summary for a skill."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM skill_effectiveness_summary WHERE skill_name = ?",
            (skill_name,),
        ).fetchone()

        if row:
            return dict(row)
        return None

    def get_low_performing_skills(self, threshold: float = 0.5) -> List[Dict]:
        """Get skills with effectiveness score below threshold."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM skill_effectiveness_summary
               WHERE effectiveness_score < ? AND total_invocations >= 3
               ORDER BY effectiveness_score ASC""",
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_skill_stats(self, skill_name: str) -> Dict:
        """Get detailed stats for a skill including recent invocations."""
        conn = self._get_conn()

        # Summary
        summary = conn.execute(
            "SELECT * FROM skill_effectiveness_summary WHERE skill_name = ?",
            (skill_name,),
        ).fetchone()

        # Recent invocations (last 10)
        recent = conn.execute(
            """SELECT success, execution_time_ms, error, invoked_at
               FROM skill_invocations
               WHERE skill_name = ?
               ORDER BY invoked_at DESC LIMIT 10""",
            (skill_name,),
        ).fetchall()

        # Recent feedback (last 10)
        feedback = conn.execute(
            """SELECT rating, feedback_text, created_at
               FROM skill_feedback
               WHERE skill_name = ?
               ORDER BY created_at DESC LIMIT 10""",
            (skill_name,),
        ).fetchall()

        result = {
            "summary": dict(summary) if summary else None,
            "recent_invocations": [dict(r) for r in recent],
            "recent_feedback": [dict(r) for r in feedback],
        }
        return result

    def recalculate_effectiveness(self):
        """Recompute all effectiveness scores from raw data."""
        conn = self._get_conn()
        skills = conn.execute(
            "SELECT DISTINCT skill_name FROM skill_invocations"
        ).fetchall()

        for (skill_name,) in skills:
            self._update_effectiveness(skill_name)

        logger.info(f"Recalculated effectiveness for {len(skills)} skills")

    def get_optimization_suggestions(self, skill_name: str) -> List[Dict]:
        """
        Generate optimization suggestions for a skill based on effectiveness data.

        Returns a list of suggestion dicts with 'area' and 'description'.
        """
        effectiveness = self.get_effectiveness(skill_name)
        if not effectiveness or effectiveness["total_invocations"] < 3:
            return []

        suggestions = []

        # Low success rate
        if effectiveness["success_rate"] < 0.7:
            suggestions.append({
                "area": "reliability",
                "description": f"Success rate is {effectiveness['success_rate']:.0%} — "
                               f"consider reviewing error patterns and adding fallback logic",
            })

        # Low user rating
        if effectiveness["avg_rating"] > 0 and effectiveness["avg_rating"] < 3.5:
            suggestions.append({
                "area": "quality",
                "description": f"Average rating is {effectiveness['avg_rating']:.1f}/5 — "
                               f"consider refining outputs or adding more detailed responses",
            })

        # Slow execution
        if effectiveness["avg_execution_time_ms"] > 5000:
            suggestions.append({
                "area": "performance",
                "description": f"Average execution time is "
                               f"{effectiveness['avg_execution_time_ms']:.0f}ms — "
                               f"consider caching or optimizing computation",
            })

        # High error rate in recent invocations
        conn = self._get_conn()
        recent_errors = conn.execute(
            """SELECT error, COUNT(*) as count
               FROM skill_invocations
               WHERE skill_name = ? AND success = 0 AND error IS NOT NULL
               GROUP BY error ORDER BY count DESC LIMIT 3""",
            (skill_name,),
        ).fetchall()

        for row in recent_errors:
            suggestions.append({
                "area": "error_pattern",
                "description": f"Recurring error: '{row['error']}' "
                               f"({row['count']} occurrences)",
            })

        return suggestions

    def _update_effectiveness(self, skill_name: str):
        """Recalculate effectiveness score for a single skill."""
        conn = self._get_conn()

        # Compute aggregates from invocations
        inv_stats = conn.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                 AVG(execution_time_ms) as avg_time
               FROM skill_invocations
               WHERE skill_name = ?""",
            (skill_name,),
        ).fetchone()

        total = inv_stats["total"] or 0
        successes = inv_stats["successes"] or 0
        success_rate = successes / total if total > 0 else 0.0
        avg_time = inv_stats["avg_time"] or 0.0

        # Compute average rating from feedback
        rating_stats = conn.execute(
            """SELECT AVG(rating) as avg_rating
               FROM skill_feedback
               WHERE skill_name = ?""",
            (skill_name,),
        ).fetchone()

        avg_rating = rating_stats["avg_rating"] or 0.0

        # Effectiveness formula
        effectiveness_score = (
            (success_rate * 0.4)
            + (avg_rating / 5.0 * 0.3)
            + (1.0 - min(avg_time / 10000.0, 1.0)) * 0.3
        )

        # Get last invocation time
        last_invoked = conn.execute(
            "SELECT MAX(invoked_at) as last FROM skill_invocations WHERE skill_name = ?",
            (skill_name,),
        ).fetchone()["last"]

        now = datetime.now().isoformat()

        # Upsert summary
        conn.execute(
            """INSERT INTO skill_effectiveness_summary
               (skill_name, total_invocations, success_rate, avg_rating,
                avg_execution_time_ms, last_invoked, effectiveness_score, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(skill_name) DO UPDATE SET
                 total_invocations=excluded.total_invocations,
                 success_rate=excluded.success_rate,
                 avg_rating=excluded.avg_rating,
                 avg_execution_time_ms=excluded.avg_execution_time_ms,
                 last_invoked=excluded.last_invoked,
                 effectiveness_score=excluded.effectiveness_score,
                 updated_at=excluded.updated_at""",
            (skill_name, total, success_rate, avg_rating, avg_time,
             last_invoked, effectiveness_score, now),
        )
        conn.commit()


# Singleton
_tracker: Optional[SkillEffectivenessTracker] = None


def get_effectiveness_tracker(db_path: str = "/data/aethera.db") -> SkillEffectivenessTracker:
    """Get the global effectiveness tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = SkillEffectivenessTracker(db_path)
        _tracker.initialize()
    return _tracker