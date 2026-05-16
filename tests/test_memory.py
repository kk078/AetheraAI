"""
Aethera AI - Memory Tests

Tests for vector store and conversation store.
"""
import pytest
import sys
sys.path.insert(0, '..')

from memory.vector_store import VectorStore, get_vector_store
from memory.conversation_store import ConversationStore, get_conversation_store


class TestConversationStore:
    """Test conversation store."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        return ConversationStore(str(db_path))

    def test_create_conversation(self, store):
        """Test conversation creation."""
        result = store.create_conversation(
            conversation_id="test-conv-1",
            user_id="test-user",
            title="Test Conversation"
        )
        assert result is True

    def test_add_message(self, store):
        """Test adding messages."""
        store.create_conversation("test-conv-1", "test-user")

        result = store.add_message(
            conversation_id="test-conv-1",
            role="user",
            content="Hello, how are you?"
        )
        assert result is True

    def test_get_conversation(self, store):
        """Test retrieving conversation with messages."""
        store.create_conversation("test-conv-1", "test-user")
        store.add_message("test-conv-1", "user", "Hello")
        store.add_message("test-conv-1", "assistant", "Hi there!")

        conversation = store.get_conversation("test-conv-1")
        assert conversation is not None
        assert len(conversation.get("messages", [])) == 2

    def test_list_conversations(self, store):
        """Test listing conversations."""
        store.create_conversation("conv-1", "test-user")
        store.create_conversation("conv-2", "test-user")

        conversations = store.list_conversations("test-user")
        assert len(conversations) >= 2

    def test_delete_conversation(self, store):
        """Test deleting conversation."""
        store.create_conversation("test-conv-1", "test-user")
        store.add_message("test-conv-1", "user", "Test message")

        result = store.delete_conversation("test-conv-1")
        assert result is True

        # Verify deletion
        conversation = store.get_conversation("test-conv-1")
        assert conversation is None

    def test_search_messages(self, store):
        """Test searching messages."""
        store.create_conversation("test-conv-1", "test-user")
        store.add_message("test-conv-1", "user", "What is ICD-10 code for diabetes?")

        results = store.search_messages("test-user", "ICD-10")
        assert len(results) > 0


class TestVectorStore:
    """Test vector store (mocked for offline testing)."""

    def test_vector_store_initialization(self):
        """Test vector store can be initialized."""
        # Would require ChromaDB running
        # This tests the class structure
        store = VectorStore()
        assert store is not None

    def test_get_vector_store_singleton(self):
        """Test singleton pattern."""
        store1 = get_vector_store()
        store2 = get_vector_store()
        assert store1 is store2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
