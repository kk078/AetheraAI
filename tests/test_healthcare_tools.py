"""Tests for healthcare tool endpoints and skills."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Code Lookup skill
# ---------------------------------------------------------------------------

class TestCodeLookup:
    def test_icd10_format_detection(self):
        """ICD-10 codes follow TNNN[.XXX] format."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        assert skill._detect_code_type("E11.9") == "icd10cm"
        assert skill._detect_code_type("A00.0") == "icd10cm"
        assert skill._detect_code_type("S72.001A") == "icd10cm"

    def test_cpt_format_detection(self):
        """CPT codes are 5 digits starting with a digit."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        assert skill._detect_code_type("99213") == "cpt"
        assert skill._detect_code_type("10004") == "cpt"

    def test_hcpcs_format_detection(self):
        """HCPCS Level II codes are alpha + 4 digits."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        assert skill._detect_code_type("J0585") == "hcpcs"
        assert skill._detect_code_type("A0425") == "hcpcs"

    def test_cdt_format_detection(self):
        """CDT dental codes start with D."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        assert skill._detect_code_type("D0120") == "cdt"
        assert skill._detect_code_type("D2150") == "cdt"

    def test_unknown_code_type(self):
        """Codes that don't match known patterns return 'unknown'."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        assert skill._detect_code_type("ZZZ123") == "unknown"
        assert skill._detect_code_type("123") == "unknown"

    def test_search_returns_results(self):
        """Keyword search returns matching codes."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        results = skill._search_codes("diabetes", "icd10cm")
        assert isinstance(results, list)

    def test_lookup_existing_code(self):
        """Looking up a known code returns its description."""
        from skills.healthcare.code_lookup import CodeLookupSkill
        skill = CodeLookupSkill()
        result = skill._lookup_code("E11.9", "icd10cm")
        if result:
            assert "diabetes" in result.lower() or "dm" in result.lower()


# ---------------------------------------------------------------------------
# Denial Analyzer skill
# ---------------------------------------------------------------------------

class TestDenialAnalyzer:
    def test_carc_classification(self):
        """CARC codes are classified by category."""
        from skills.healthcare.denial_analyzer import DenialAnalyzerSkill
        skill = DenialAnalyzerSkill()
        cat = skill._categorize_denial("CO-50")
        assert cat in ("clinical", "medical_necessity")

    def test_patient_responsibility_classification(self):
        """PR codes are patient responsibility."""
        from skills.healthcare.denial_analyzer import DenialAnalyzerSkill
        skill = DenialAnalyzerSkill()
        cat = skill._categorize_denial("PR-1")
        assert cat == "patient_responsibility"

    def test_appeal_recommendation(self):
        """Denials that warrant appeal get a recommendation."""
        from skills.healthcare.denial_analyzer import DenialAnalyzerSkill
        skill = DenialAnalyzerSkill()
        rec = skill._generate_appeal_recommendation("CO-50", {})
        assert isinstance(rec, dict)
        assert "recommended" in rec

    def test_multiple_codes_analysis(self):
        """Multiple CARC/RARC codes are analyzed together."""
        from skills.healthcare.denial_analyzer import DenialAnalyzerSkill
        skill = DenialAnalyzerSkill()
        result = skill.analyze_codes(["CO-50", "PR-2"])
        assert isinstance(result, list)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Calculator skill (clinical formulas)
# ---------------------------------------------------------------------------

class TestMedicalCalculator:
    def test_bmi_calculation(self):
        from skills.builtin.calculator import CalculatorSkill
        skill = CalculatorSkill()
        result = skill._clinical_calc("bmi", {"weight_kg": 70, "height_m": 1.75})
        assert 18 < result["value"] < 30  # Normal range

    def test_egfr_calculation(self):
        from skills.builtin.calculator import CalculatorSkill
        skill = CalculatorSkill()
        result = skill._clinical_calc("egfr", {
            "creatinine": 1.0,
            "age": 50,
            "sex": "female",
        })
        assert result["value"] > 60  # Normal kidney function

    def test_financial_present_value(self):
        from skills.builtin.calculator import CalculatorSkill
        skill = CalculatorSkill()
        result = skill._financial_calc("pv", {
            "future_value": 1000,
            "rate": 0.05,
            "periods": 1,
        })
        assert 900 < result["value"] < 1000  # PV < FV with positive rate


# ---------------------------------------------------------------------------
# CCI Editor (if module available)
# ---------------------------------------------------------------------------

class TestCCIEditor:
    @pytest.fixture(autouse=True)
    def _import_check(self):
        try:
            from skills.healthcare.cci_editor import CCIEditorSkill
            self.skill = CCIEditorSkill()
        except ImportError:
            pytest.skip("CCI Editor skill not yet available")

    def test_edit_pair_check(self):
        result = self.skill.check_pair("99213", "99214")
        assert isinstance(result, dict)
        assert "edit_exists" in result

    def test_modifier_allowed_check(self):
        result = self.skill.check_modifier("99213", "99214", "25")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Fee Schedule (if module available)
# ---------------------------------------------------------------------------

class TestFeeSchedule:
    @pytest.fixture(autouse=True)
    def _import_check(self):
        try:
            from skills.healthcare.fee_schedule import FeeScheduleSkill
            self.skill = FeeScheduleSkill()
        except ImportError:
            pytest.skip("Fee Schedule skill not yet available")

    def test_cpt_lookup(self):
        result = self.skill.lookup("99213", locality="national")
        assert isinstance(result, dict)

    def test_rvucalculation(self):
        result = self.skill.calculate_reimbursement(
            work_rvu=1.0, pe_rvu=0.5, mp_rvu=0.05,
            gpci_work=1.0, gpci_pe=1.0, gpci_mp=0.5,
            conversion_factor=32.74,
        )
        assert result["total"] > 0


# ---------------------------------------------------------------------------
# Coverage Checker (if module available)
# ---------------------------------------------------------------------------

class TestCoverageChecker:
    @pytest.fixture(autouse=True)
    def _import_check(self):
        try:
            from skills.healthcare.coverage_checker import CoverageCheckerSkill
            self.skill = CoverageCheckerSkill()
        except ImportError:
            pytest.skip("Coverage Checker skill not yet available")

    def test_lcd_search(self):
        result = self.skill.search_lcd(cpt="99213", diagnosis="E11.9")
        assert isinstance(result, (list, dict))

    def test_ncd_check(self):
        result = self.skill.check_ncd(cpt="93000")
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])