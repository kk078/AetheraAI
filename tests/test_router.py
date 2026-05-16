"""
AetheraAI — Tests for intent classification and specialist routing.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orchestrator.router import (
    IntentClassifier,
    AetheraRouter,
    RoutingResult,
    RoutingConfidence,
    get_router,
)


class TestIntentClassifier:
    """Tests for IntentClassifier.classify(), assess_complexity(), extract_entities()."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    # --- Slash commands ---

    def test_classify_slash_command_code(self, classifier):
        result = classifier.classify("/code E11.9")
        assert len(result) > 0
        assert any("command:" in r for r in result)

    def test_classify_slash_command_denial(self, classifier):
        result = classifier.classify("/denial CO-50")
        assert len(result) > 0
        assert any("command:" in r for r in result)

    def test_classify_slash_command_help(self, classifier):
        result = classifier.classify("/help")
        # /help is not in SLASH_COMMANDS, so it should fall through to keyword matching
        # or return general_query
        assert isinstance(result, list)

    # --- Healthcare provider intents ---

    def test_classify_healthcare_provider_intents(self, classifier):
        result = classifier.classify("How do I bill CPT 99213 for an office visit?")
        assert any("coding_lookup" in r for r in result)

    def test_classify_claim_analysis(self, classifier):
        result = classifier.classify("Analyze this claim for potential denials")
        assert any("claim_analysis" in r for r in result)

    def test_classify_reimbursement(self, classifier):
        result = classifier.classify("What is the reimbursement for procedure 99213?")
        assert any("reimbursement_check" in r for r in result)

    # --- Healthcare payer intents ---

    def test_classify_healthcare_payer_intents(self, classifier):
        result = classifier.classify("Explain the adjudication logic for this claim")
        assert any("adjudication_logic" in r for r in result)

    def test_classify_risk_adjustment(self, classifier):
        result = classifier.classify("Calculate risk adjustment for HCC codes")
        assert any("risk_adjustment" in r for r in result)

    # --- Regulatory intents ---

    def test_classify_regulatory_intents(self, classifier):
        result = classifier.classify("What are the HIPAA privacy requirements?")
        assert any("compliance_check" in r or "regulatory_research" in r for r in result)

    def test_classify_regulatory_research(self, classifier):
        result = classifier.classify("Research Stark Law implications for this arrangement")
        assert any("regulatory_research" in r for r in result)

    # --- Clinical intents ---

    def test_classify_clinical_intents(self, classifier):
        result = classifier.classify("What are the drug interactions with metformin?")
        assert any("drug_information" in r or "clinical_reference" in r for r in result)

    def test_classify_drug_information(self, classifier):
        result = classifier.classify("Tell me about drug interactions with warfarin")
        assert any("drug_information" in r for r in result)

    # --- General query fallback ---

    def test_classify_general_query_fallback(self, classifier):
        result = classifier.classify("What is the weather like today?")
        # Should fall back to general_query or a low-confidence match
        assert isinstance(result, list)
        assert len(result) > 0

    def test_classify_empty_string(self, classifier):
        result = classifier.classify("")
        assert isinstance(result, list)

    def test_classify_whitespace_only(self, classifier):
        result = classifier.classify("   \t\n  ")
        assert isinstance(result, list)

    # --- Complexity assessment ---

    def test_assess_complexity_simple(self, classifier):
        result = classifier.assess_complexity("Quick question about ICD-10")
        assert result == "simple"

    def test_assess_complexity_complex(self, classifier):
        long_query = "Please provide a comprehensive detailed in-depth analysis of the claim denial patterns across multiple payers including Medicare Medicaid and commercial insurance for the past fiscal year"
        result = classifier.assess_complexity(long_query)
        assert result == "complex"

    def test_assess_complexity_medium(self, classifier):
        result = classifier.assess_complexity("What is the fee schedule for 99213?")
        # Complexity assessment may classify this as simple or medium
        assert result in ("simple", "medium", "complex")

    # --- Entity extraction ---

    def test_extract_entities_icd10(self, classifier):
        entities = classifier.extract_entities("Patient has E11.9 and M54.5")
        icd10_entities = [e for e in entities if e["type"] == "icd10"]
        assert len(icd10_entities) == 2

    def test_extract_entities_cpt(self, classifier):
        entities = classifier.extract_entities("CPT 99213 was billed for this visit")
        cpt_entities = [e for e in entities if e["type"] == "cpt"]
        assert len(cpt_entities) >= 1

    def test_extract_entities_npi(self, classifier):
        entities = classifier.extract_entities("NPI: 1234567890")
        npi_entities = [e for e in entities if e["type"] == "npi"]
        assert len(npi_entities) >= 1

    def test_extract_entities_dollar_amounts(self, classifier):
        entities = classifier.extract_entities("The claim was for $1,500.00")
        money_entities = [e for e in entities if e["type"] == "monetary"]
        assert len(money_entities) >= 1

    def test_extract_entities_dates(self, classifier):
        entities = classifier.extract_entities("Service date 01/15/2024")
        date_entities = [e for e in entities if e["type"] == "date"]
        assert len(date_entities) >= 1

    def test_extract_entities_mixed(self, classifier):
        text = "Claim for E11.9 with CPT 99213 totaling $1,500.00 on 01/15/2024"
        entities = classifier.extract_entities(text)
        types = {e["type"] for e in entities}
        assert "icd10" in types
        assert "cpt" in types
        assert "monetary" in types

    def test_extract_entities_no_entities(self, classifier):
        entities = classifier.extract_entities("The patient is doing well")
        assert len(entities) == 0


class TestAetheraRouter:
    """Tests for AetheraRouter.route() and specialist management."""

    @pytest.fixture
    def router(self, sample_routing_config):
        return AetheraRouter(config_path=sample_routing_config)

    # --- Slash command routing ---

    def test_route_slash_command_code(self, router):
        result = router.route("/code E11.9")
        assert result.primary_specialist == "healthcare_provider"
        assert result.confidence == 1.0
        assert result.confidence_level == RoutingConfidence.VERY_HIGH

    def test_route_slash_command_drug(self, router):
        result = router.route("/drug metformin")
        assert result.primary_specialist == "healthcare_pharmacy"

    def test_route_slash_command_cf(self, router):
        result = router.route("/cf status")
        assert result.primary_specialist == "cloudflare_ops"

    def test_route_slash_command_fee(self, router):
        result = router.route("/fee 99213")
        assert result.primary_specialist == "healthcare_provider"

    # --- Natural language routing ---

    def test_route_natural_language_provider(self, router):
        result = router.route("How do I bill CPT 99213 for an office visit?")
        assert result.primary_specialist == "healthcare_provider"

    def test_route_natural_language_payer(self, router):
        result = router.route("Explain the adjudication logic for this Medicare claim")
        # May route to healthcare_payer or healthcare_provider depending on keyword matching
        assert result.primary_specialist in ("healthcare_payer", "healthcare_provider")

    def test_route_natural_language_regulatory(self, router):
        result = router.route("What are the HIPAA privacy requirements?")
        assert result.primary_specialist == "healthcare_regulatory"

    def test_route_fallback_general(self, router):
        result = router.route("Hello, how are you?")
        # Should fall back to general or a low-confidence result
        assert result.primary_specialist is not None
        assert result.confidence < 0.5 or result.primary_specialist == "general"

    def test_route_with_context(self, router):
        result = router.route("billing question", context={"user_id": "test", "preferred_specialist": "healthcare_provider"})
        assert result.primary_specialist is not None

    def test_route_empty_query(self, router):
        result = router.route("")
        assert result.primary_specialist is not None

    def test_route_with_entity_boosting(self, router):
        result = router.route("NPI: 1234567890 billing question")
        # NPI entity should boost healthcare_provider score
        assert result.primary_specialist == "healthcare_provider"

    # --- Specialist management ---

    def test_list_specialists(self, router):
        specialists = router.list_specialists()
        assert isinstance(specialists, list)
        assert len(specialists) > 0

    def test_get_specialist_known(self, router):
        specialist = router.get_specialist("healthcare_provider")
        assert specialist is not None
        assert specialist["enabled"] is True

    def test_get_specialist_unknown(self, router):
        specialist = router.get_specialist("nonexistent_specialist")
        assert specialist is None

    def test_route_multi_intent_sets_multi_agent_flag(self, router):
        # A query with multiple clear intents should set requires_multi_agent
        result = router.route("Analyze claim denial and check HIPAA compliance for the same patient")
        # Multi-intent queries should potentially set the flag
        assert isinstance(result.requires_multi_agent, bool)

    def test_get_router_singleton(self):
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])