"""
Aethera AI - Conversation PHI taint tracking.

Sensitivity is detected per message, and the model cascade forces PHI/PII to a
local model. But PHI from an earlier turn lives on in the conversation history
and injected memory context, so a *later* message that looks clean could route a
PHI-bearing prompt to a cloud model.

This module pins a conversation to local models for its entire lifetime once any
turn in it is flagged PHI/PII. The taint set is persisted (SQLite) so a restart
can't silently un-taint a conversation.
"""

import logging
import os
import sqlite3
from typing import Optional

logger = logging.getLogger("aethera.phi_guard")

DEFAULT_DB_PATH = os.environ.get(
    "PHI_GUARD_DB_PATH",
    os.path.join(os.environ.get("DATA_DIR", "./data"), "phi_taint.db"),
)


class ConversationSensitivityTracker:
    """Persisted record of which conversations have ever contained PHI/PII."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS tainted_conversations (
                   conversation_id TEXT PRIMARY KEY,
                   tainted_at TEXT NOT NULL DEFAULT (datetime('now'))
               )"""
        )
        self._conn.commit()

    def mark_tainted(self, conversation_id: Optional[str]) -> None:
        """Record that a conversation has carried PHI/PII. No-op for empty ids."""
        if not conversation_id:
            return
        self._conn.execute(
            "INSERT OR IGNORE INTO tainted_conversations (conversation_id) VALUES (?)",
            (conversation_id,),
        )
        self._conn.commit()

    def is_tainted(self, conversation_id: Optional[str]) -> bool:
        if not conversation_id:
            return False
        row = self._conn.execute(
            "SELECT 1 FROM tainted_conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def apply_taint(
    tracker: "ConversationSensitivityTracker",
    conversation_id: Optional[str],
    contains_phi: bool,
    contains_pii: bool,
) -> tuple[bool, bool]:
    """Record current-turn sensitivity and return effective (phi, pii) flags.

    If this turn is sensitive, the conversation is marked tainted; the returned
    flags are the OR of this turn and any prior taint, so a clean follow-up in a
    PHI conversation still routes locally.
    """
    if contains_phi or contains_pii:
        tracker.mark_tainted(conversation_id)
    tainted = tracker.is_tainted(conversation_id)
    return (contains_phi or tainted, contains_pii or tainted)


_tracker: Optional[ConversationSensitivityTracker] = None


def get_tracker(db_path: str = DEFAULT_DB_PATH) -> ConversationSensitivityTracker:
    """Get or create the singleton tracker."""
    global _tracker
    if _tracker is None:
        _tracker = ConversationSensitivityTracker(db_path=db_path)
    return _tracker
