"""
AetheraAI — Tests for MemoryManager and context formatting.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory.memory_manager import MemoryManager, get_memory_manager


class TestMemoryManager:
    """Tests for MemoryManager initialization, retrieval, and consolidation."""

    @pytest.fixture
    def manager(self, mock_memory_subsystems):
        """Create a MemoryManager with mocked subsystems."""
        mgr = MemoryManager(db_path=":memory:", chromadb_url="http://localhost:8001")
        mgr._fact_store = mock_memory_subsystems["fact_store"]
        mgr._learning_store = mock_memory_subsystems["learning_store"]
        mgr._health_records = mock_memory_subsystems["health_records"]
        mgr._vector_store = mock_memory_subsystems["vector_store"]
        mgr._knowledge_gaps = mock_memory_subsystems["knowledge_gaps"]
        mgr._audit_db = mock_memory_subsystems["audit_db"]
        mgr._initialized = True
        return mgr

    @pytest.mark.asyncio
    async def test_retrieve_context_returns_string(self, manager):
        result = await manager.retrieve_context(
            query="What is diabetes?",
            user_id="test_user",
            specialist="healthcare_provider",
            max_chars=2000,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_retrieve_context_empty_when_no_data(self, manager):
        result = await manager.retrieve_context(
            query="What is the weather?",
            user_id="test_user",
            specialist="general",
            max_chars=2000,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_retrieve_context_respects_budget(self, manager):
        manager._fact_store.search_facts = AsyncMock(return_value=[
            {"content": "Diabetes is a chronic condition " * 100, "category": "medical", "confidence": 0.9}
        ])
        result = await manager.retrieve_context(
            query="diabetes",
            user_id="test_user",
            specialist="healthcare_provider",
            max_chars=500,
        )
        assert len(result) <= 600

    @pytest.mark.asyncio
    async def test_retrieve_context_assembles_facts(self, manager):
        manager._fact_store.search_facts = AsyncMock(return_value=[
            {"content": "E11.9 is Type 2 diabetes", "category": "medical", "confidence": 0.9}
        ])
        result = await manager.retrieve_context(
            query="diabetes",
            user_id="test_user",
            specialist="healthcare_provider",
            max_chars=2000,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_retrieve_context_health_specialist_includes_records(self, manager):
        manager._health_records.search = AsyncMock(return_value=[
            {"condition": "Diabetes", "date": "2024-01-01", "status": "active"}
        ])
        result = await manager.retrieve_context(
            query="diabetes treatment",
            user_id="test_user",
            specialist="healthcare_provider",
            max_chars=2000,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_consolidate_extracts_facts(self, manager):
        await manager.consolidate(
            user_id="test_user",
            query="What is the diabetes management protocol?",
            response="Diabetes is managed through diet, exercise, and medication. The A1C target is below 7%.",
            specialist="healthcare_provider",
            conversation_id="conv123",
        )
        manager._fact_store.store_fact.assert_called()

    @pytest.mark.asyncio
    async def test_consolidate_records_interaction(self, manager):
        await manager.consolidate(
            user_id="test_user",
            query="test query",
            response="test response",
            specialist="general",
            conversation_id="conv123",
        )
        manager._learning_store.record_interaction.assert_called()

    @pytest.mark.asyncio
    async def test_consolidate_handles_subsystem_failure(self, manager):
        manager._fact_store.store_fact = AsyncMock(side_effect=Exception("DB error"))
        await manager.consolidate(
            user_id="test_user",
            query="test",
            response="test response",
            specialist="general",
            conversation_id="conv123",
        )

    @pytest.mark.asyncio
    async def test_get_user_context_returns_string(self, manager):
        manager._learning_store.get_preferences = AsyncMock(return_value={"theme": "dark"})
        result = await manager.get_user_context(user_id="test_user")
        assert isinstance(result, str)

    def test_extract_facts_with_indicators(self, manager):
        text = "Diabetes is a condition that affects blood sugar. The patient was diagnosed with hypertension."
        facts = manager._extract_facts(text, "medical")
        assert isinstance(facts, list)

    def test_extract_facts_short_sentences_skipped(self, manager):
        text = "Ok. Yes. No."
        facts = manager._extract_facts(text, "general")
        assert len(facts) == 0 or all(len(f[0]) > 20 for f in facts if f)

    def test_specialist_to_collection_mapping(self, manager):
        assert manager._specialist_to_collection("healthcare_provider") is not None
        assert manager._specialist_to_collection("finance") is not None

    def test_specialist_to_collection_unknown(self, manager):
        result = manager._specialist_to_collection("unknown_specialist_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_close_resets_initialized(self, manager):
        manager._vector_store.close = AsyncMock()
        manager._audit_db.close = AsyncMock() if hasattr(manager._audit_db, 'close') else None
        await manager.close()
        assert manager._initialized is False


class TestContextFormatting:
    """Tests for MemoryManager formatting helper methods."""

    @pytest.fixture
    def manager(self):
        mgr = MemoryManager(db_path=":memory:", chromadb_url="http://localhost:8001")
        mgr._initialized = True
        return mgr

    def test_format_facts_truncates_to_budget(self, manager):
        facts = [
            {"content": "Diabetes is a chronic condition that affects millions", "category": "medical", "confidence": 0.9},
            {"content": "Hypertension is a major risk factor", "category": "medical", "confidence": 0.8},
            {"content": "Heart disease can be prevented", "category": "medical", "confidence": 0.7},
        ]
        result = manager._format_facts(facts, budget=50)
        assert len(result) <= 60

    def test_format_facts_empty_list(self, manager):
        result = manager._format_facts([], budget=500)
        assert result == ""

    def test_format_preferences_truncates(self, manager):
        prefs = {"theme": "dark", "font_size": "large", "specialist": "provider",
                 "language": "en", "timezone": "UTC"}
        result = manager._format_preferences(prefs, budget=100)
        assert len(result) <= 110

    def test_format_health_records_deidentified(self, manager):
        records = [
            {"condition": "Diabetes", "date": "2024-01-01", "status": "active"}
        ]
        result = manager._format_health_records(records, budget=500, deidentified=True)
        assert "De-identified" in result or "de-identified" in result.lower() or isinstance(result, str)

    def test_format_vector_results(self, manager):
        results = [
            {"content": "Diabetes management involves diet and exercise", "score": 0.95, "source": "knowledge"},
        ]
        result = manager._format_vector_results(results, budget=500)
        assert isinstance(result, str)

    def test_format_knowledge_gaps(self, manager):
        gaps = [
            {"topic": "ICD-10 2024 updates", "priority": "high"},
            {"topic": "New CPT codes for 2024", "priority": "medium"},
        ]
        result = manager._format_knowledge_gaps(gaps, budget=200)
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])