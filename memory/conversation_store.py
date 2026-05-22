"""
Aethera AI - Conversation Store Module

SQLite-based conversation history storage.
Stores full conversation history with search and retrieval.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class ConversationStore:
    """
    SQLite conversation history store.

    Schema:
    - conversations: id, user_id, title, created_at, updated_at, metadata
    - messages: id, conversation_id, role, content, timestamp, metadata
    """

    def __init__(self, db_path: str = "/data/aethera.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self):
        """Initialize database schema."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        # Create tables
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                specialist TEXT,
                model TEXT,
                confidence REAL,
                metadata JSON,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id);

            CREATE INDEX IF NOT EXISTS idx_conversations_user
            ON conversations(user_id);
        """)

        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def create_conversation(self, user_id: str, conversation_id: str, title: str = "") -> bool:
        """Create a new conversation."""
        try:
            self._conn.execute(
                """INSERT INTO conversations (id, user_id, title, metadata)
                   VALUES (?, ?, ?, ?)""",
                (conversation_id, user_id, title, json.dumps({}))
            )
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return False

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        specialist: Optional[str] = None,
        model: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Add a message to a conversation."""
        import uuid
        message_id = str(uuid.uuid4())

        try:
            self._conn.execute(
                """INSERT INTO messages
                   (id, conversation_id, role, content, specialist, model, confidence, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    specialist,
                    model,
                    confidence,
                    json.dumps(metadata or {})
                )
            )

            # Update conversation timestamp
            self._conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )

            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation with all messages."""
        cursor = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        conversation = dict(row)
        conversation["metadata"] = json.loads(conversation["metadata"]) if conversation["metadata"] else {}

        # Get messages
        cursor = self._conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            msg["metadata"] = json.loads(msg["metadata"]) if msg["metadata"] else {}
            messages.append(msg)

        conversation["messages"] = messages
        return conversation

    def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations for a user."""
        cursor = self._conn.execute(
            """SELECT * FROM conversations
               WHERE user_id = ?
               ORDER BY updated_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset)
        )

        conversations = []
        for row in cursor.fetchall():
            conv = dict(row)
            conv["metadata"] = json.loads(conv["metadata"]) if conv["metadata"] else {}
            conversations.append(conv)

        return conversations

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all messages."""
        try:
            self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            self._conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False

    def search_messages(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search messages for a user."""
        cursor = self._conn.execute(
            """SELECT m.*, c.title as conversation_title
               FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.user_id = ? AND m.content LIKE ?
               ORDER BY m.timestamp DESC
               LIMIT ?""",
            (user_id, f"%{query}%", limit)
        )

        results = []
        for row in cursor.fetchall():
            msg = dict(row)
            msg["metadata"] = json.loads(msg["metadata"]) if msg["metadata"] else {}
            results.append(msg)

        return results

    def get_conversation_count(self, user_id: str) -> int:
        """Get total conversation count for a user."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) as count FROM conversations WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def delete_user_data(self, user_id: str) -> int:
        """Delete all conversations and messages for a user (HIPAA right-to-delete).

        Returns the number of conversations removed.
        """
        try:
            rows = self._conn.execute(
                "SELECT id FROM conversations WHERE user_id = ?", (user_id,)
            ).fetchall()
            conversation_ids = [r["id"] for r in rows]
            for cid in conversation_ids:
                self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
            self._conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            self._conn.commit()
            return len(conversation_ids)
        except Exception as e:
            print(f"Error deleting user data: {e}")
            return 0

    def purge_older_than(self, days: int) -> int:
        """Delete conversations (and their messages) not updated within `days`.

        Implements a data-retention policy. Returns conversations removed.
        """
        try:
            cutoff = datetime.now().timestamp() - days * 86400
            rows = self._conn.execute(
                "SELECT id, updated_at FROM conversations"
            ).fetchall()
            stale = []
            for r in rows:
                ts = r["updated_at"]
                try:
                    when = datetime.fromisoformat(str(ts)).timestamp()
                except (ValueError, TypeError):
                    continue  # unparseable timestamp → leave it alone
                if when < cutoff:
                    stale.append(r["id"])
            for cid in stale:
                self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
                self._conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
            self._conn.commit()
            return len(stale)
        except Exception as e:
            print(f"Error purging old conversations: {e}")
            return 0


# Singleton instance
_conversation_store: Optional[ConversationStore] = None


def get_conversation_store(db_path: str = "/data/aethera.db") -> ConversationStore:
    """Get or create the conversation store instance."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore(db_path)
    return _conversation_store
