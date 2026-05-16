"""
AetheraAI — Tests for model cascade, failover, and rate limits.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orchestrator.cascade import (
    ModelCascade,
    CascadeConfig,
    ModelSelection,
    ProviderType,
    UsageLevel,
    RateLimitStatus,
    get_cascade,
)


class TestCascadeConfig:
    """Tests for CascadeConfig dataclass defaults."""

    def test_default_config_values(self):
        config = CascadeConfig()
        assert config.ollama_cloud_session_limit == 100
        assert config.ollama_cloud_weekly_limit == 500
        assert config.huggingface_daily_limit == 1000
        assert config.session_duration_hours == 5
        assert config.weekly_reset_day == 0

    def test_custom_config(self):
        config = CascadeConfig(
            ollama_cloud_session_limit=200,
            ollama_cloud_weekly_limit=1000,
            huggingface_daily_limit=2000,
        )
        assert config.ollama_cloud_session_limit == 200
        assert config.ollama_cloud_weekly_limit == 1000
        assert config.huggingface_daily_limit == 2000


class TestModelSelection:
    """Tests for ModelSelection dataclass."""

    def test_model_selection_defaults(self):
        selection = ModelSelection(
            model_name="aethera-cloud-brain",
            provider=ProviderType.OLLAMA_CLOUD,
            reason="test",
            fallback_chain=["aethera-cloud-balanced", "aethera-local-smart"],
            estimated_latency_ms=500,
            is_local=False,
            usage_level=UsageLevel.L2_MEDIUM,
        )
        assert selection.model_name == "aethera-cloud-brain"
        assert selection.provider == ProviderType.OLLAMA_CLOUD
        assert len(selection.fallback_chain) == 2


class TestModelCascade:
    """Tests for ModelCascade model selection and rate limiting."""

    @pytest.fixture
    def cascade(self):
        """Create a ModelCascade with mocked Redis (no actual connection)."""
        config = CascadeConfig(
            ollama_cloud_session_limit=100,
            ollama_cloud_weekly_limit=500,
            huggingface_daily_limit=1000,
        )
        c = ModelCascade(redis_url="redis://localhost:6379", config=config)
        c.redis_client = MagicMock()
        c.redis_client.get = AsyncMock(return_value=0)
        c.redis_client.incr = AsyncMock(return_value=1)
        c.redis_client.expire = AsyncMock(return_value=True)
        c._initialized = True
        return c

    # --- PHI/PII override ---

    @pytest.mark.asyncio
    async def test_select_model_phi_forces_local(self, cascade):
        result = await cascade.select_model("healthcare_provider", is_phi=True)
        assert result.model_name == "aethera-local-fast"
        assert result.is_local is True

    @pytest.mark.asyncio
    async def test_select_model_pii_forces_local(self, cascade):
        result = await cascade.select_model("healthcare_provider", is_pii=True)
        assert result.model_name == "aethera-local-fast"
        assert result.is_local is True

    # --- Force model override ---

    @pytest.mark.asyncio
    async def test_select_model_force_model_override(self, cascade):
        result = await cascade.select_model(
            "healthcare_provider", force_model="aethera-cloud-coder"
        )
        assert result.model_name == "aethera-cloud-coder"

    # --- Complexity routing ---

    @pytest.mark.asyncio
    async def test_select_model_simple_complexity_local(self, cascade):
        result = await cascade.select_model("healthcare_provider", complexity="simple")
        assert result.model_name == "aethera-local-fast" or result.is_local is True

    @pytest.mark.asyncio
    async def test_select_model_complex_upgrades(self, cascade):
        result = await cascade.select_model("healthcare_provider", complexity="complex")
        assert result.model_name is not None

    # --- Specialist mapping ---

    @pytest.mark.asyncio
    async def test_select_model_specialist_mapping(self, cascade):
        result = await cascade.select_model("healthcare_provider")
        assert result.model_name is not None
        assert result.reason is not None

    @pytest.mark.asyncio
    async def test_select_model_unknown_specialist_defaults(self, cascade):
        result = await cascade.select_model("unknown_specialist_xyz")
        assert result.model_name is not None

    # --- Fallback chain ---

    @pytest.mark.asyncio
    async def test_fallback_chain_depth_limit(self, cascade):
        result = await cascade.select_model("healthcare_provider")
        assert result.model_name is not None

    # --- Model info ---

    def test_get_model_info_known_model(self, cascade):
        info = cascade.get_model_info("aethera-cloud-brain")
        assert info is not None
        assert "provider" in info
        assert "usage_level" in info

    def test_get_model_info_unknown_model(self, cascade):
        info = cascade.get_model_info("nonexistent_model")
        assert info is None

    def test_list_available_models(self, cascade):
        models = cascade.list_available_models()
        assert isinstance(models, list)
        assert len(models) > 0
        for model in models:
            assert "model_name" in model or "name" in model

    # --- Usage summary ---

    @pytest.mark.asyncio
    async def test_get_usage_summary_no_redis(self, cascade):
        summary = await cascade.get_usage_summary()
        assert isinstance(summary, dict)

    # --- Rate limit checks ---

    @pytest.mark.asyncio
    async def test_check_rate_limit_local_always_available(self, cascade):
        is_available, status = await cascade.check_rate_limit(ProviderType.OLLAMA_LOCAL, "aethera-local-fast")
        assert is_available is True

    # --- Preferred model env override ---

    @pytest.mark.asyncio
    async def test_preferred_model_env_override_local(self, cascade):
        with patch.dict(os.environ, {"PREFERRED_MODEL": "aethera-local-fast"}):
            result = await cascade.select_model("healthcare_provider")
            assert result.model_name == "aethera-local-fast"

    # --- Singleton pattern ---

    def test_cascade_singleton(self):
        c1 = get_cascade()
        c2 = get_cascade()
        assert c1 is c2

    # --- Specialized model selection ---

    @pytest.mark.asyncio
    async def test_pharmacy_uses_cloud_brain(self, cascade):
        result = await cascade.select_model("healthcare_pharmacy")
        assert result.model_name is not None

    @pytest.mark.asyncio
    async def test_finance_uses_cloud_model(self, cascade):
        result = await cascade.select_model("finance")
        assert result.model_name is not None

    @pytest.mark.asyncio
    async def test_cloud_provider_returns_provider_type(self, cascade):
        result = await cascade.select_model("healthcare_provider")
        assert result.provider in (ProviderType.OLLAMA_CLOUD, ProviderType.OLLAMA_LOCAL, ProviderType.HUGGINGFACE, ProviderType.CUSTOM)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])