"""Tests for coding/clinical skills."""

import pytest

from skills.healthcare.em_level_advisor import EMLevelAdvisorSkill
from skills.healthcare.modifier_recommender import ModifierRecommenderSkill
from skills.healthcare.medical_necessity_builder import MedicalNecessityBuilderSkill
from skills.healthcare.hcc_gap_finder import HCCGapFinderSkill


# ------------------------------------------------------------------ E/M advisor
async def test_em_by_time():
    skill = EMLevelAdvisorSkill()
    res = await skill.run(method="time", patient_type="established", total_time_minutes=35)
    assert res.success
    assert res.data["recommended_code"] == "99214"


async def test_em_new_by_time():
    skill = EMLevelAdvisorSkill()
    res = await skill.run(patient_type="new", total_time_minutes=50)
    assert res.data["recommended_code"] == "99204"


async def test_em_by_mdm_direct():
    skill = EMLevelAdvisorSkill()
    res = await skill.run(method="mdm", patient_type="established", mdm_level="moderate")
    assert res.data["recommended_code"] == "99214"


async def test_em_mdm_two_of_three():
    skill = EMLevelAdvisorSkill()
    # moderate, moderate, low -> 2-of-3 = moderate
    res = await skill.run(method="mdm", patient_type="new",
                          problems_level="moderate", data_level="moderate", risk_level="low")
    assert res.data["mdm_level"] == "moderate"
    assert res.data["recommended_code"] == "99204"


async def test_em_below_threshold():
    skill = EMLevelAdvisorSkill()
    res = await skill.run(method="time", patient_type="established", total_time_minutes=5)
    assert res.success is False


# --------------------------------------------------------------- modifier rec
async def test_modifier_em_with_procedure():
    skill = ModifierRecommenderSkill()
    res = await skill.run(cpt="99213", scenario={"separate_em_same_day_procedure": True})
    assert "25" in res.data["modifiers"]


async def test_modifier_multiple_and_side():
    skill = ModifierRecommenderSkill()
    res = await skill.run(scenario={"bilateral_procedure": True, "side": "left", "multiple_procedures": True})
    mods = set(res.data["modifiers"])
    assert {"50", "LT", "51"}.issubset(mods)


async def test_modifier_x_subset_preferred():
    skill = ModifierRecommenderSkill()
    res = await skill.run(scenario={"distinct_procedural_service": True, "x_subset": "separate_structure"})
    assert "XS" in res.data["modifiers"]


async def test_modifier_none():
    skill = ModifierRecommenderSkill()
    res = await skill.run(scenario={})
    assert res.success
    assert res.data["recommended_modifiers"] == []


# --------------------------------------------------------- medical necessity
async def test_medical_necessity_strong():
    skill = MedicalNecessityBuilderSkill()
    res = await skill.run(
        cpt="72148", service_description="lumbar MRI",
        diagnoses=["M54.5 low back pain", "M51.16 radiculopathy"],
        clinical_indications=["progressive radicular pain", "positive straight-leg raise"],
        failed_conservative=["6 weeks PT", "NSAIDs"],
        supporting_findings=["diminished ankle reflex"],
    )
    assert res.success
    assert res.data["strength"] == "strong"
    assert "medically necessary" in res.data["rationale"].lower()
    assert res.data["missing_documentation"] == []


async def test_medical_necessity_missing_docs():
    skill = MedicalNecessityBuilderSkill()
    res = await skill.run(cpt="72148", diagnoses=["M54.5"])
    assert res.success
    assert res.data["strength"] == "weak"
    assert len(res.data["missing_documentation"]) >= 1


async def test_medical_necessity_requires_dx():
    skill = MedicalNecessityBuilderSkill()
    res = await skill.run(cpt="72148", diagnoses=[])
    assert res.success is False


# ------------------------------------------------------------------ HCC gaps
async def test_hcc_gap_detects_unrecaptured():
    skill = HCCGapFinderSkill()
    res = await skill.run(
        prior_year_hccs=["HCC19", "HCC85"],
        current_year_dx=["E11.9"],          # supports HCC19 only
        revenue_per_raf=10000,
    )
    assert res.success
    gap_hccs = [g["hcc"] for g in res.data["recapture_gaps"]]
    assert "HCC85" in gap_hccs       # CHF not recaptured
    assert "HCC19" not in gap_hccs   # diabetes recaptured
    assert res.data["raf_at_risk"] == pytest.approx(0.331, abs=0.001)
    assert res.data["estimated_revenue_at_risk"] == pytest.approx(3310.0, abs=1)


async def test_hcc_suspected_new():
    skill = HCCGapFinderSkill()
    res = await skill.run(prior_year_hccs=[], current_year_dx=["J44.1"])  # COPD -> HCC111
    suspected = [s["hcc"] for s in res.data["suspected_new_hccs"]]
    assert "HCC111" in suspected
