"""
Aethera AI - Specialist Tests

Tests for specialist modules.
"""
import pytest
import sys
sys.path.insert(0, '..')

from specialists.healthcare_provider import HealthcareProviderSpecialist
from specialists.healthcare_payer import HealthcarePayerSpecialist
from specialists.healthcare_regulatory import HealthcareRegulatorySpecialist


class TestHealthcareProviderSpecialist:
    """Test healthcare provider specialist."""

    @pytest.fixture
    def provider(self):
        return HealthcareProviderSpecialist()

    def test_coding_query(self, provider):
        """Test coding query handling."""
        response = provider.handle_query("What is the ICD-10 code for Type 2 diabetes?")
        assert response is not None
        assert "E11" in response or "diabetes" in response.lower()

    def test_billing_query(self, provider):
        """Test billing query handling."""
        response = provider.handle_query("How do I bill for office visit 99214?")
        assert response is not None
        assert "99214" in response

    def test_denial_query(self, provider):
        """Test denial handling."""
        response = provider.handle_query("Claim denied with CO-50, what does this mean?")
        assert response is not None
        assert "CO-50" in response or "medical necessity" in response.lower()


class TestHealthcarePayerSpecialist:
    """Test healthcare payer specialist."""

    @pytest.fixture
    def payer(self):
        return HealthcarePayerSpecialist()

    def test_prior_auth_query(self, payer):
        """Test prior authorization query."""
        response = payer.handle_query("What are Medicare prior auth requirements?")
        assert response is not None
        assert "prior auth" in response.lower() or "medicare" in response.lower()

    def test_risk_adjustment(self, payer):
        """Test risk adjustment query."""
        response = payer.handle_query("How is risk adjustment calculated?")
        assert response is not None
        assert "risk" in response.lower()


class TestHealthcareRegulatorySpecialist:
    """Test regulatory specialist."""

    @pytest.fixture
    def regulatory(self):
        return HealthcareRegulatorySpecialist()

    def test_hipaa_query(self, regulatory):
        """Test HIPAA query."""
        response = regulatory.handle_query("What are HIPAA privacy requirements?")
        assert response is not None
        assert "HIPAA" in response or "privacy" in response.lower()

    def test_stark_law(self, regulatory):
        """Test Stark Law query."""
        response = regulatory.handle_query("What is Stark Law?")
        assert response is not None
        assert "Stark" in response or "physician" in response.lower()


class TestSpecialistRegistry:
    """Test specialist registry."""

    def test_get_specialist(self):
        """Test getting specialist from registry."""
        from specialists import get_specialist

        provider = get_specialist("healthcare_provider")
        assert provider is not None

    def test_list_specialists(self):
        """Test listing all specialists."""
        from specialists import list_specialists

        specialists = list_specialists()
        assert len(specialists) > 0
        assert "healthcare_provider" in specialists
        assert "healthcare_payer" in specialists


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
