"""Tests for PHI retention + right-to-delete on the conversation store."""

import pytest

from memory.conversation_store import ConversationStore
from orchestrator.phi_logging import redact_text


@pytest.fixture
def store(tmp_path):
    s = ConversationStore(db_path=str(tmp_path / "conv.db"))
    s.initialize()
    yield s
    s.close()


def test_delete_user_data_removes_everything(store):
    store.create_conversation("user-a", "c1", "t1")
    store.add_message("c1", "user", "hello")
    store.create_conversation("user-a", "c2", "t2")
    store.create_conversation("user-b", "c3", "t3")

    removed = store.delete_user_data("user-a")
    assert removed == 2
    assert store.get_conversation("c1") is None
    assert store.get_conversation("c2") is None
    # Other users are untouched.
    assert store.get_conversation("c3") is not None
    assert store.get_conversation_count("user-a") == 0


def test_delete_user_data_unknown_user(store):
    assert store.delete_user_data("nobody") == 0


def test_purge_older_than(store):
    store.create_conversation("u", "old", "old")
    store.create_conversation("u", "new", "new")
    # Age the "old" conversation well past the retention window.
    store._conn.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        ("2000-01-01 00:00:00", "old"),
    )
    store._conn.commit()

    purged = store.purge_older_than(days=30)
    assert purged == 1
    assert store.get_conversation("old") is None
    assert store.get_conversation("new") is not None


def test_redact_text_helper():
    out = redact_text("patient SSN 123-45-6789")
    assert "123-45-6789" not in out
    assert redact_text("") == ""
    assert redact_text("no phi here") == "no phi here"
