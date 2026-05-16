"""
Aethera AI - Router Tests

Tests for intent classification and specialist routing.
"""
import pytest
import sys
sys.path.insert(0, '..')

from orchestrator.router import Router


class TestRouter:
    """Test router functionality."""

    @pytest.fixture
    def router(self):
        return Router()

    def test_healthcare_provider_routing(self, router):
        """Test routing to healthcare provider specialist."""
        queries = [
            "How do I bill for CPT 99214?",
            "What's the ICD-10 code for diabetes?",
            "Claim denied for CO-50, what do I do?",
            "Explain DRG assignment",
        ]

        for query in queries:
            result = router.classify_intent(query)
            assert result['specialist'] == 'healthcare_provider'

    def test_healthcare_payer_routing(self, router):
        """Test routing to healthcare payer specialist."""
        queries = [
            "What are the Medicare prior auth rules?",
            "Explain risk adjustment",
            "How is Star Rating calculated?",
        ]

        for query in queries:
            result = router.classify_intent(query)
            assert result['specialist'] == 'healthcare_payer'

    def test_regulatory_routing(self, router):
        """Test routing to regulatory specialist."""
        queries = [
            "What are the HIPAA requirements?",
            "Explain Stark Law exceptions",
            "Anti-Kickback statute compliance",
        ]

        for query in queries:
            result = router.classify_intent(query)
            assert result['specialist'] == 'healthcare_regulatory'

    def test_clinical_routing(self, router):
        """Test routing to clinical specialist."""
        queries = [
            "What's the treatment for hypertension?",
            "Drug interaction between warfarin and aspirin",
            "Lab results interpretation for HbA1c",
        ]

        for query in queries:
            result = router.classify_intent(query)
            assert result['specialist'] == 'healthcare_clinical'

    def test_slash_command_routing(self, router):
        """Test slash command routing."""
        commands = [
            ("/code", "code_lookup"),
            ("/denial", "denial_analysis"),
            ("/fee", "fee_schedule"),
            ("/drug", "drug_info"),
        ]

        for command, expected_tool in commands:
            result = router.classify_intent(command)
            assert result['tool'] == expected_tool

    def test_fallback_routing(self, router):
        """Test fallback to general specialist."""
        result = router.classify_intent("Hello, how are you?")
        assert result['specialist'] == 'general'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
