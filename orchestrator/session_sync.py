"""
Cross-device session continuity.

When Aethera is accessed from multiple devices (laptop via localhost,
phone via Cloudflare Tunnel), this module keeps conversations in sync
using a shared SQLite database and optimistic concurrency.

Key features:
- Session tokens identify a user across devices
- Conversation state is stored server-side (SQLite)
- Each device gets a session_id; conversations are shared by user_id
- Last-read position tracked per device for notification badges
- Conflict resolution: last-write-wins for messages, merge for metadata
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DeviceSession:
    session_id: str
    user_id: str
    device_name: str
    device_type: str  # "desktop", "mobile", "tablet"
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    last_conversation_id: str | None = None
    push_token: str | None = None


@dataclass
class SessionState:
    """State that syncs across devices for a user."""
    user_id: str
    active_conversation_id: str | None = None
    open_views: list[str] = field(default_factory=list)  # ["chat", "dashboard", "code-lookup"]
    last_read_positions: dict[str, int] = field(default_factory=dict)  # conversation_id -> message_index
    ui_preferences: dict[str, Any] = field(default_factory=dict)  # theme, sidebar state, etc.


class SessionSync:
    """
    Cross-device session management.

    All devices connecting to Aethera (whether via localhost or
    Cloudflare Tunnel) share the same backend. This module:
    1. Assigns session tokens to identify devices
    2. Tracks which conversation each device is viewing
    3. Syncs last-read positions for notification badges
    4. Persists UI preferences across devices
    """

    def __init__(self, db_path: str = "/data/aethera.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS device_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_name TEXT,
                    device_type TEXT DEFAULT 'desktop',
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    last_conversation_id TEXT,
                    push_token TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON device_sessions(user_id);

                CREATE TABLE IF NOT EXISTS session_state (
                    user_id TEXT PRIMARY KEY,
                    active_conversation_id TEXT,
                    open_views TEXT DEFAULT '[]',
                    last_read_positions TEXT DEFAULT '{}',
                    ui_preferences TEXT DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    event_data TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_user ON session_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_events_time ON session_events(created_at);
            """)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ------------------------------------------------------------------
    # Device session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        user_id: str,
        device_name: str = "Unknown",
        device_type: str = "desktop",
    ) -> DeviceSession:
        session = DeviceSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            device_name=device_name,
            device_type=device_type,
        )
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO device_sessions
                   (session_id, user_id, device_name, device_type, created_at, last_active)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session.session_id,
                    session.user_id,
                    session.device_name,
                    session.device_type,
                    session.created_at.isoformat(),
                    session.last_active.isoformat(),
                ),
            )
        return session

    def get_session(self, session_id: str) -> DeviceSession | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM device_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            return DeviceSession(
                session_id=row["session_id"],
                user_id=row["user_id"],
                device_name=row["device_name"],
                device_type=row["device_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_active=datetime.fromisoformat(row["last_active"]),
                last_conversation_id=row["last_conversation_id"],
                push_token=row["push_token"],
            )

    def update_activity(self, session_id: str, conversation_id: str | None = None):
        with self._get_conn() as conn:
            now = datetime.now().isoformat()
            if conversation_id:
                conn.execute(
                    """UPDATE device_sessions
                       SET last_active = ?, last_conversation_id = ?
                       WHERE session_id = ?""",
                    (now, conversation_id, session_id),
                )
            else:
                conn.execute(
                    "UPDATE device_sessions SET last_active = ? WHERE session_id = ?",
                    (now, session_id),
                )

    def list_user_sessions(self, user_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT session_id, device_name, device_type, last_active, last_conversation_id
                   FROM device_sessions WHERE user_id = ?
                   ORDER BY last_active DESC""",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM device_sessions WHERE session_id = ?", (session_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Shared session state
    # ------------------------------------------------------------------

    def get_state(self, user_id: str) -> SessionState:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM session_state WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return SessionState(user_id=user_id)
            return SessionState(
                user_id=row["user_id"],
                active_conversation_id=row["active_conversation_id"],
                open_views=json.loads(row["open_views"]),
                last_read_positions=json.loads(row["last_read_positions"]),
                ui_preferences=json.loads(row["ui_preferences"]),
            )

    def update_state(self, user_id: str, updates: dict) -> SessionState:
        current = self.get_state(user_id)

        if "active_conversation_id" in updates:
            current.active_conversation_id = updates["active_conversation_id"]
        if "open_views" in updates:
            current.open_views = updates["open_views"]
        if "last_read_positions" in updates:
            current.last_read_positions.update(updates["last_read_positions"])
        if "ui_preferences" in updates:
            current.ui_preferences.update(updates["ui_preferences"])

        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO session_state
                   (user_id, active_conversation_id, open_views, last_read_positions, ui_preferences, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       active_conversation_id = excluded.active_conversation_id,
                       open_views = excluded.open_views,
                       last_read_positions = excluded.last_read_positions,
                       ui_preferences = excluded.ui_preferences,
                       updated_at = excluded.updated_at""",
                (
                    current.user_id,
                    current.active_conversation_id,
                    json.dumps(current.open_views),
                    json.dumps(current.last_read_positions),
                    json.dumps(current.ui_preferences),
                    datetime.now().isoformat(),
                ),
            )
        return current

    def update_read_position(self, user_id: str, conversation_id: str, message_index: int):
        state = self.get_state(user_id)
        state.last_read_positions[conversation_id] = message_index
        self.update_state(user_id, {"last_read_positions": state.last_read_positions})

    def get_unread_counts(self, user_id: str, conversation_message_counts: dict[str, int]) -> dict[str, int]:
        """Calculate unread message counts for conversations.

        Args:
            conversation_message_counts: {conversation_id: total_messages}
        """
        state = self.get_state(user_id)
        unread = {}
        for conv_id, total in conversation_message_counts.items():
            last_read = state.last_read_positions.get(conv_id, 0)
            unread[conv_id] = max(0, total - last_read)
        return unread

    # ------------------------------------------------------------------
    # Session events (for cross-device notifications)
    # ------------------------------------------------------------------

    def log_event(self, user_id: str, event_type: str, event_data: dict | None = None, session_id: str | None = None):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO session_events (user_id, session_id, event_type, event_data, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    session_id,
                    event_type,
                    json.dumps(event_data or {}),
                    datetime.now().isoformat(),
                ),
            )

    def get_events_since(self, user_id: str, since: datetime, event_type: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            if event_type:
                rows = conn.execute(
                    """SELECT * FROM session_events
                       WHERE user_id = ? AND created_at > ? AND event_type = ?
                       ORDER BY created_at DESC LIMIT 100""",
                    (user_id, since.isoformat(), event_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM session_events
                       WHERE user_id = ? AND created_at > ?
                       ORDER BY created_at DESC LIMIT 100""",
                    (user_id, since.isoformat()),
                ).fetchall()
            return [dict(r) for r in rows]

    def cleanup_old_events(self, days: int = 30):
        cutoff = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM session_events WHERE created_at < datetime('now', ?)",
                (f"-{days} days",),
            )