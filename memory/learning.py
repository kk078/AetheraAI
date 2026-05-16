"""
Aethera AI - Adaptive Preference Learning Module

Tracks user interaction patterns and learns preferences over time.
Stores learning weights in SQLite for persistence across sessions.

Tracks: query patterns, preferred specialists, preferred response formats,
correction patterns, and frequently used tools.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter


class LearningStore:
    """
    SQLite-backed adaptive preference learning system.

    Schema:
    - interactions: id, user_id, interaction_type, context (JSON), timestamp
    - preferences: user_id, preference_key, preference_value, weight, updated_at
    - patterns: id, user_id, pattern_type, pattern_data (JSON), frequency,
                confidence, last_seen, created_at
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
            CREATE TABLE IF NOT EXISTS learning_interactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                context JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS learning_preferences (
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, preference_key)
            );

            CREATE TABLE IF NOT EXISTS learning_patterns (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_data JSON NOT NULL,
                frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_interactions_user
                ON learning_interactions(user_id);

            CREATE INDEX IF NOT EXISTS idx_interactions_type
                ON learning_interactions(interaction_type);

            CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
                ON learning_interactions(timestamp);

            CREATE INDEX IF NOT EXISTS idx_patterns_user_type
                ON learning_patterns(user_id, pattern_type);

            CREATE INDEX IF NOT EXISTS idx_preferences_user
                ON learning_preferences(user_id);
        """)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    # ---- Interaction Recording ----

    def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a user interaction for learning.

        Args:
            user_id: User identifier
            interaction_type: Type of interaction
                ('query', 'correction', 'tool_use', 'format_preference',
                 'specialist_choice', 'feedback', 'navigation')
            context: Additional context data

        Returns:
            Interaction ID
        """
        interaction_id = f"int_{uuid.uuid4().hex[:12]}"

        self._conn.execute(
            """INSERT INTO learning_interactions
               (id, user_id, interaction_type, context, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (interaction_id, user_id, interaction_type,
             json.dumps(context or {}), datetime.now().isoformat())
        )
        self._conn.commit()

        # Trigger pattern detection after recording
        self._update_patterns_from_interaction(user_id, interaction_type, context or {})

        return interaction_id

    def _update_patterns_from_interaction(
        self,
        user_id: str,
        interaction_type: str,
        context: Dict[str, Any]
    ):
        """Update pattern data based on a new interaction."""
        now = datetime.now().isoformat()

        # Extract pattern key based on interaction type
        pattern_data = self._extract_pattern(interaction_type, context)
        if not pattern_data:
            return

        pattern_key = json.dumps(pattern_data, sort_keys=True)

        # Check if this pattern already exists
        cursor = self._conn.execute(
            """SELECT id, frequency, confidence FROM learning_patterns
               WHERE user_id = ? AND pattern_type = ? AND pattern_data = ?""",
            (user_id, interaction_type, pattern_key)
        )
        row = cursor.fetchone()

        if row:
            # Increment frequency and update confidence
            new_freq = row["frequency"] + 1
            new_confidence = min(1.0, new_freq / (new_freq + 5))  # Asymptotic confidence
            self._conn.execute(
                """UPDATE learning_patterns
                   SET frequency = ?, confidence = ?, last_seen = ?
                   WHERE id = ?""",
                (new_freq, new_confidence, now, row["id"])
            )
        else:
            pattern_id = f"pat_{uuid.uuid4().hex[:12]}"
            self._conn.execute(
                """INSERT INTO learning_patterns
                   (id, user_id, pattern_type, pattern_data, frequency,
                    confidence, last_seen, created_at)
                   VALUES (?, ?, ?, ?, 1, 0.167, ?, ?)""",
                (pattern_id, user_id, interaction_type, pattern_key, now, now)
            )

        self._conn.commit()

    def _extract_pattern(
        self,
        interaction_type: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract pattern data from an interaction context."""
        if interaction_type == "query":
            # Extract query topic and structure
            query = context.get("query", "")
            if query:
                return {
                    "topic_keywords": self._extract_keywords(query),
                    "query_length": "short" if len(query.split()) <= 5 else "detailed"
                }

        elif interaction_type == "specialist_choice":
            return {
                "specialist": context.get("specialist", ""),
                "domain": context.get("domain", "")
            }

        elif interaction_type == "format_preference":
            return {
                "format": context.get("format", ""),
                "detail_level": context.get("detail_level", "")
            }

        elif interaction_type == "tool_use":
            return {
                "tool_name": context.get("tool_name", ""),
                "tool_category": context.get("tool_category", "")
            }

        elif interaction_type == "correction":
            return {
                "correction_type": context.get("correction_type", ""),
                "original_topic": context.get("original_topic", "")
            }

        elif interaction_type == "feedback":
            return {
                "sentiment": context.get("sentiment", ""),
                "topic": context.get("topic", "")
            }

        return None

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract key terms from text, filtering common stop words."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "shall", "should", "may", "might", "can", "could",
            "i", "me", "my", "we", "our", "you", "your", "it", "its",
            "this", "that", "these", "those", "what", "which", "who",
            "whom", "when", "where", "why", "how", "all", "each", "every",
            "both", "few", "more", "most", "other", "some", "such", "no",
            "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "because", "as", "until", "while", "of", "at", "by",
            "for", "with", "about", "against", "between", "through",
            "during", "before", "after", "above", "below", "to", "from",
            "up", "down", "in", "out", "on", "off", "over", "under",
            "again", "further", "then", "once", "and", "but", "or", "nor",
            "if", "into", "also"
        }

        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        keywords = [w for w in words if w not in stop_words]

        # Return most common keywords
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(max_keywords)]

    # ---- Preference Management ----

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get all learned preferences for a user.

        Returns:
            Dict mapping preference keys to {value, weight} dicts
        """
        cursor = self._conn.execute(
            """SELECT preference_key, preference_value, weight
               FROM learning_preferences
               WHERE user_id = ?
               ORDER BY weight DESC""",
            (user_id,)
        )

        preferences = {}
        for row in cursor.fetchall():
            preferences[row["preference_key"]] = {
                "value": row["preference_value"],
                "weight": row["weight"]
            }

        # Merge with patterns to infer preferences
        inferred = self._infer_preferences_from_patterns(user_id)
        for key, value in inferred.items():
            if key not in preferences:
                preferences[key] = value

        return preferences

    def _infer_preferences_from_patterns(self, user_id: str) -> Dict[str, Any]:
        """Infer preferences from interaction patterns."""
        inferred: Dict[str, Any] = {}

        # Infer preferred specialist
        cursor = self._conn.execute(
            """SELECT pattern_data, frequency, confidence
               FROM learning_patterns
               WHERE user_id = ? AND pattern_type = 'specialist_choice'
               ORDER BY frequency DESC LIMIT 1""",
            (user_id,)
        )
        row = cursor.fetchone()
        if row and row["confidence"] > 0.3:
            data = json.loads(row["pattern_data"])
            if data.get("specialist"):
                inferred["preferred_specialist"] = {
                    "value": data["specialist"],
                    "weight": row["confidence"]
                }

        # Infer preferred response format
        cursor = self._conn.execute(
            """SELECT pattern_data, frequency, confidence
               FROM learning_patterns
               WHERE user_id = ? AND pattern_type = 'format_preference'
               ORDER BY frequency DESC LIMIT 1""",
            (user_id,)
        )
        row = cursor.fetchone()
        if row and row["confidence"] > 0.3:
            data = json.loads(row["pattern_data"])
            if data.get("format"):
                inferred["preferred_format"] = {
                    "value": data["format"],
                    "weight": row["confidence"]
                }

        # Infer most used tools
        cursor = self._conn.execute(
            """SELECT pattern_data, SUM(frequency) as total_freq
               FROM learning_patterns
               WHERE user_id = ? AND pattern_type = 'tool_use'
               GROUP BY pattern_data
               ORDER BY total_freq DESC LIMIT 5""",
            (user_id,)
        )
        top_tools = []
        for row in cursor.fetchall():
            data = json.loads(row["pattern_data"])
            if data.get("tool_name"):
                top_tools.append(data["tool_name"])

        if top_tools:
            inferred["frequently_used_tools"] = {
                "value": json.dumps(top_tools),
                "weight": 0.7
            }

        return inferred

    def update_weight(
        self,
        user_id: str,
        preference_key: str,
        preference_value: str,
        weight: float,
        increment: bool = False
    ) -> bool:
        """
        Set or update a preference weight.

        Args:
            user_id: User identifier
            preference_key: Preference key name
            preference_value: Preference value
            weight: New weight (0.0-1.0+), or increment amount
            increment: If True, add weight to existing; if False, set weight

        Returns:
            True if successful
        """
        now = datetime.now().isoformat()

        if increment:
            self._conn.execute(
                """INSERT INTO learning_preferences
                   (user_id, preference_key, preference_value, weight, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, preference_key) DO UPDATE SET
                       weight = weight + excluded.weight,
                       updated_at = excluded.updated_at""",
                (user_id, preference_key, preference_value, weight, now)
            )
        else:
            self._conn.execute(
                """INSERT INTO learning_preferences
                   (user_id, preference_key, preference_value, weight, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, preference_key) DO UPDATE SET
                       preference_value = excluded.preference_value,
                       weight = excluded.weight,
                       updated_at = excluded.updated_at""",
                (user_id, preference_key, preference_value, weight, now)
            )

        self._conn.commit()
        return True

    # ---- Pattern Detection ----

    def detect_patterns(
        self,
        user_id: str,
        pattern_type: Optional[str] = None,
        min_frequency: int = 2,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Detect learned patterns for a user.

        Args:
            user_id: User identifier
            pattern_type: Filter by pattern type
            min_frequency: Minimum occurrence frequency
            min_confidence: Minimum confidence threshold

        Returns:
            List of detected patterns
        """
        if pattern_type:
            cursor = self._conn.execute(
                """SELECT * FROM learning_patterns
                   WHERE user_id = ? AND pattern_type = ?
                     AND frequency >= ? AND confidence >= ?
                   ORDER BY frequency DESC""",
                (user_id, pattern_type, min_frequency, min_confidence)
            )
        else:
            cursor = self._conn.execute(
                """SELECT * FROM learning_patterns
                   WHERE user_id = ?
                     AND frequency >= ? AND confidence >= ?
                   ORDER BY frequency DESC""",
                (user_id, min_frequency, min_confidence)
            )

        patterns = []
        for row in cursor.fetchall():
            pattern = dict(row)
            pattern["pattern_data"] = json.loads(pattern["pattern_data"])
            patterns.append(pattern)

        return patterns

    def predict_next_action(self, user_id: str) -> Dict[str, Any]:
        """
        Predict the user's next likely action based on learned patterns.

        Uses recent interaction history and weighted patterns to suggest
        the most probable next step.

        Returns:
            Dict with predictions: likely_specialist, likely_format,
            likely_tools, confidence
        """
        predictions: Dict[str, Any] = {
            "likely_specialist": None,
            "likely_format": None,
            "likely_tools": [],
            "confidence": 0.0
        }

        # Get recent interactions (last 10)
        cursor = self._conn.execute(
            """SELECT interaction_type, context FROM learning_interactions
               WHERE user_id = ?
               ORDER BY timestamp DESC LIMIT 10""",
            (user_id,)
        )
        recent = []
        for row in cursor.fetchall():
            recent.append({
                "type": row["interaction_type"],
                "context": json.loads(row["context"]) if row["context"] else {}
            })

        if not recent:
            return predictions

        # Predict specialist from patterns
        specialist_patterns = self.detect_patterns(
            user_id, pattern_type="specialist_choice", min_frequency=1
        )
        if specialist_patterns:
            top = specialist_patterns[0]
            predictions["likely_specialist"] = top["pattern_data"].get("specialist")
            predictions["confidence"] = max(predictions["confidence"], top["confidence"])

        # Predict format from patterns
        format_patterns = self.detect_patterns(
            user_id, pattern_type="format_preference", min_frequency=1
        )
        if format_patterns:
            top = format_patterns[0]
            predictions["likely_format"] = top["pattern_data"].get("format")

        # Predict tools from patterns
        tool_patterns = self.detect_patterns(
            user_id, pattern_type="tool_use", min_frequency=1
        )
        predictions["likely_tools"] = [
            p["pattern_data"].get("tool_name", "")
            for p in tool_patterns[:5]
            if p["pattern_data"].get("tool_name")
        ]

        return predictions

    # ---- Analytics ----

    def get_interaction_history(
        self,
        user_id: str,
        interaction_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get interaction history for a user."""
        if interaction_type:
            cursor = self._conn.execute(
                """SELECT * FROM learning_interactions
                   WHERE user_id = ? AND interaction_type = ?
                   ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (user_id, interaction_type, limit, offset)
            )
        else:
            cursor = self._conn.execute(
                """SELECT * FROM learning_interactions
                   WHERE user_id = ?
                   ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (user_id, limit, offset)
            )

        results = []
        for row in cursor.fetchall():
            record = dict(row)
            record["context"] = json.loads(record["context"]) if record["context"] else {}
            results.append(record)

        return results

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get learning statistics."""
        if user_id:
            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM learning_interactions WHERE user_id = ?",
                (user_id,)
            )
            interaction_count = cursor.fetchone()["count"]

            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM learning_patterns WHERE user_id = ?",
                (user_id,)
            )
            pattern_count = cursor.fetchone()["count"]

            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM learning_preferences WHERE user_id = ?",
                (user_id,)
            )
            preference_count = cursor.fetchone()["count"]

            return {
                "user_id": user_id,
                "interaction_count": interaction_count,
                "pattern_count": pattern_count,
                "preference_count": preference_count
            }
        else:
            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM learning_interactions"
            )
            total_interactions = cursor.fetchone()["count"]

            cursor = self._conn.execute(
                "SELECT COUNT(DISTINCT user_id) as count FROM learning_interactions"
            )
            total_users = cursor.fetchone()["count"]

            return {
                "total_interactions": total_interactions,
                "total_users": total_users
            }


# Singleton instance
_learning_store: Optional[LearningStore] = None


def get_learning_store(db_path: str = "/data/aethera.db") -> LearningStore:
    """Get or create the learning store instance."""
    global _learning_store
    if _learning_store is None:
        _learning_store = LearningStore(db_path)
    return _learning_store