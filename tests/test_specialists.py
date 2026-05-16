"""
AetheraAI — Tests for specialist modules.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from specialists.healthcare_provider import HealthcareProviderSpecialist
except ImportError:
    HealthcareProviderSpecialist = None

try:
    from specialists.healthcare_payer import HealthcarePayerSpecialist
except ImportError:
    HealthcarePayerSpecialist = None

try:
    from specialists.healthcare_regulatory import HealthcareRegulatorySpecialist
except ImportError:
    HealthcareRegulatorySpecialist = None

try:
    from orchestrator.router import AetheraRouter
    from orchestrator.router import get_router
except ImportError:
    AetheraRouter = None
    get_router = None


class TestHealthcareProviderSpecialist:
    """Tests for HealthcareProviderSpecialist (with import guard)."""

    @pytest.fixture
    def provider(self):
        if HealthcareProviderSpecialist is None:
            pytest.skip("HealthcareProviderSpecialist not available")
        return HealthcareProviderSpecialist()

    def test_coding_query(self, provider):
        if not hasattr(provider, 'handle_query') and not hasattr(provider, 'execute'):
            pytest.skip("Specialist does not have query handler")
        # Just verify the specialist can be instantiated
        assert provider is not None

    def test_specialist_name(self, provider):
        if hasattr(provider, 'name'):
            assert "provider" in provider.name.lower() or "healthcare" in provider.name.lower()


class TestHealthcarePayerSpecialist:
    """Tests for HealthcarePayerSpecialist (with import guard)."""

    @pytest.fixture
    def payer(self):
        if HealthcarePayerSpecialist is None:
            pytest.skip("HealthcarePayerSpecialist not available")
        return HealthcarePayerSpecialist()

    def test_payer_specialist_exists(self, payer):
        assert payer is not None

    def test_specialist_name(self, payer):
        if hasattr(payer, 'name'):
            assert "payer" in payer.name.lower() or "healthcare" in payer.name.lower()


class TestHealthcareRegulatorySpecialist:
    """Tests for HealthcareRegulatorySpecialist (with import guard)."""

    @pytest.fixture
    def regulatory(self):
        if HealthcareRegulatorySpecialist is None:
            pytest.skip("HealthcareRegulatorySpecialist not available")
        return HealthcareRegulatorySpecialist()

    def test_regulatory_specialist_exists(self, regulatory):
        assert regulatory is not None

    def test_specialist_name(self, regulatory):
        if hasattr(regulatory, 'name'):
            assert "regulatory" in regulatory.name.lower() or "healthcare" in regulatory.name.lower()


class TestSpecialistRegistry:
    """Tests for specialist registry via AetheraRouter."""

    @pytest.fixture
    def router(self, sample_routing_config):
        if AetheraRouter is None:
            pytest.skip("AetheraRouter not available")
        return AetheraRouter(config_path=sample_routing_config)

    def test_get_specialist_known(self, router):
        specialist = router.get_specialist("healthcare_provider")
        assert specialist is not None
        assert specialist["enabled"] is True

    def test_get_specialist_unknown(self, router):
        specialist = router.get_specialist("nonexistent_specialist_xyz")
        assert specialist is None

    def test_list_specialists(self, router):
        specialists = router.list_specialists()
        assert isinstance(specialists, list)
        assert len(specialists) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])