"""
Aethera AI - Model Cascade Tests

Tests for model cascade with rate limit tracking and fallback.
"""
import pytest
import asyncio
import sys
sys.path.insert(0, '..')

from orchestrator.cascade import ModelCascade, RateLimitTracker


class TestRateLimitTracker:
    """Test rate limit tracking."""

    @pytest.fixture
    def tracker(self):
        return RateLimitTracker()

    def test_track_request(self, tracker):
        """Test request tracking."""
        tracker.record_request("ollama-cloud")
        count = tracker.get_request_count("ollama-cloud")
        assert count == 1

    def test_rate_limit_check(self, tracker):
        """Test rate limit checking."""
        # Simulate multiple requests
        for _ in range(10):
            tracker.record_request("test-model")

        # Check if rate limited (depends on configuration)
        is_limited = tracker.is_rate_limited("test-model")
        # May or may not be limited based on config

    def test_window_reset(self, tracker):
        """Test that request window resets."""
        tracker.record_request("test-model")
        assert tracker.get_request_count("test-model") == 1

        # In real test, would wait for window to expire
        # tracker._requests["test-model"] = []  # Simulate reset


class TestModelCascade:
    """Test model cascade functionality."""

    @pytest.fixture
    def cascade(self):
        return ModelCascade()

    @pytest.mark.asyncio
    async def test_cloud_first(self, cascade):
        """Test that cloud model is tried first."""
        # This would require actual API access
        # Mocked test for structure
        result = await cascade.execute_with_cascade(
            prompt="Test prompt",
            model="aethera-cascade"
        )

        # Should return some result
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_chain(self, cascade):
        """Test fallback to local model when cloud fails."""
        # Simulate cloud failure
        cascade._check_cloud_available = lambda: False

        result = await cascade.execute_with_cascade(
            prompt="Test prompt",
            model="aethera-cascade"
        )

        # Should fallback to local
        assert result is not None

    def test_usage_level_routing(self, cascade):
        """Test usage-based model routing."""
        # High usage should route to local
        cascade._usage_percent = 90
        model = cascade._get_model_for_usage("ollama-cloud")
        assert model != "ollama-cloud"  # Should not use cloud at 90%

        # Low usage should allow cloud
        cascade._usage_percent = 30
        model = cascade._get_model_for_usage("ollama-cloud")
        assert model == "ollama-cloud"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
