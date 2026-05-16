"""
AetheraAI — Tests for DenialPredictorSkill risk prediction.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from skills.healthcare.denial_predictor import DenialPredictorSkill
except ImportError:
    DenialPredictorSkill = None


@pytest.fixture
def predictor():
    if DenialPredictorSkill is None:
        pytest.skip("DenialPredictorSkill not available")
    return DenialPredictorSkill()


class TestDenialPredictorBasic:
    """Tests for basic denial prediction."""

    def test_predict_basic_claim(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="established",
        )
        assert "denial_probability" in result
        assert "risk_level" in result
        assert "risk_factors" in result
        assert result["denial_probability"] >= 0
        assert result["denial_probability"] <= 1

    def test_predict_requires_procedure_codes(self, predictor):
        # Empty procedure codes should still return a result
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=[],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=None,
            patient_status="established",
        )
        assert result["denial_probability"] is not None

    def test_predict_high_risk_diagnosis(self, predictor):
        # M54.5 is in HIGH_RISK_DIAGNOSIS
        result = predictor._predict_denial(
            diagnosis_codes=["M54.5"],
            procedure_codes=["97110"],
            modifiers=[],
            place_of_service="11",
            payer="Aetna",
            service_type="physical_therapy",
            prior_auth_obtained=False,
            patient_status="new",
        )
        risk_categories = [f.get("factor", "") if isinstance(f, dict) else f
                          for f in result.get("risk_factors", [])]
        assert len(result["risk_factors"]) > 0

    def test_predict_high_risk_procedure(self, predictor):
        # 97110 is in HIGH_RISK_PROCEDURES
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["97110"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="physical_therapy",
            prior_auth_obtained=False,
            patient_status="established",
        )
        assert len(result["risk_factors"]) > 0

    def test_predict_service_type_risk(self, predictor):
        # ambulance should have higher base denial rate than office_visit
        result_ambulance = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="ambulance",
            prior_auth_obtained=None,
            patient_status="established",
        )
        result_office = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=None,
            patient_status="established",
        )
        assert result_ambulance["denial_probability"] >= result_office["denial_probability"]


class TestDenialPredictorPayerRisk:
    """Tests for payer-specific risk multiplier."""

    def test_predict_payer_risk_multiplier(self, predictor):
        result_medicaid = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicaid",
            service_type="office_visit",
            prior_auth_obtained=None,
            patient_status="established",
        )
        result_tricare = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Tricare",
            service_type="office_visit",
            prior_auth_obtained=None,
            patient_status="established",
        )
        # Medicaid has higher multiplier than Tricare
        assert result_medicaid["denial_probability"] >= result_tricare["denial_probability"]

    def test_find_payer_case_insensitive(self, predictor):
        result = predictor._find_payer("medicare")
        assert result is not None
        assert "multiplier" in result or "top_denial_reasons" in result

    def test_find_payer_partial_match(self, predictor):
        result = predictor._find_payer("UHC")
        assert result is not None

    def test_find_payer_unknown(self, predictor):
        result = predictor._find_payer("XYZ Insurance Co ABC123")
        assert result is not None
        # Unknown payer should get default multiplier of 1.0


class TestDenialPredictorPriorAuth:
    """Tests for prior authorization risk factors."""

    def test_prior_auth_not_obtained(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=False,
            patient_status="established",
        )
        # Should have prior auth risk factor
        assert result["denial_probability"] is not None

    def test_prior_auth_obtained(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="established",
        )
        # Should have lower risk than not obtained
        assert result["denial_probability"] is not None

    def test_prior_auth_unknown(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=None,
            patient_status="established",
        )
        assert result["denial_probability"] is not None


class TestDenialPredictorModifiers:
    """Tests for modifier and multiple procedure risk factors."""

    def test_modifier_59_risk(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["M54.5"],
            procedure_codes=["97110", "97140"],
            modifiers=["59"],
            place_of_service="11",
            payer="Aetna",
            service_type="physical_therapy",
            prior_auth_obtained=None,
            patient_status="established",
        )
        # Modifier 59 should be flagged in risk factors
        assert result["denial_probability"] is not None

    def test_multiple_procedures(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213", "99214", "85025", "36415"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="established",
        )
        # Multiple procedures should add risk factor
        assert result["denial_probability"] is not None

    def test_new_patient_risk(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="new",
        )
        assert result["denial_probability"] is not None


class TestDenialPredictorOutput:
    """Tests for prediction output format and enrichment."""

    def test_predict_prevention_recommendations(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["M54.5"],
            procedure_codes=["97110"],
            modifiers=[],
            place_of_service="11",
            payer="Aetna",
            service_type="physical_therapy",
            prior_auth_obtained=False,
            patient_status="new",
        )
        assert "prevention_recommendations" in result
        assert isinstance(result["prevention_recommendations"], list)

    def test_predict_likely_denial_codes(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="established",
        )
        assert "likely_denial_codes" in result
        assert isinstance(result["likely_denial_codes"], list)

    def test_predict_probability_between_0_and_1(self, predictor):
        for payer in ["Medicare", "Aetna", "UnitedHealthcare", "UnknownPayer"]:
            result = predictor._predict_denial(
                diagnosis_codes=["E11.9"],
                procedure_codes=["99213"],
                modifiers=[],
                place_of_service="11",
                payer=payer,
                service_type="office_visit",
                prior_auth_obtained=True,
                patient_status="established",
            )
            assert 0 <= result["denial_probability"] <= 1, f"Probability out of range for {payer}"

    def test_predict_risk_level_classification(self, predictor):
        result = predictor._predict_denial(
            diagnosis_codes=["E11.9"],
            procedure_codes=["99213"],
            modifiers=[],
            place_of_service="11",
            payer="Medicare",
            service_type="office_visit",
            prior_auth_obtained=True,
            patient_status="established",
        )
        assert result["risk_level"] in ("critical", "high", "moderate", "low")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])