"""Tests for the RCM revenue-ops skills."""

import pytest

from skills.healthcare.ar_prioritizer import ARPrioritizerSkill
from skills.healthcare.rcm_kpi_calculator import RCMKPICalculatorSkill
from skills.healthcare.underpayment_detector import UnderpaymentDetectorSkill


# --------------------------------------------------------------------------- AR
async def test_ar_prioritizer_ranks_by_score_and_buckets():
    skill = ARPrioritizerSkill()
    res = await skill.run(action="prioritize", accounts=[
        {"account_id": "A", "balance": 100, "age_days": 10, "payer_class": "commercial"},
        {"account_id": "B", "balance": 100, "age_days": 200, "payer_class": "commercial"},
        {"account_id": "C", "balance": 5000, "age_days": 45, "payer_class": "self_pay"},
    ])
    assert res.success
    wl = res.data["worklist"]
    # Highest dollar account should top the list.
    assert wl[0]["account_id"] == "C"
    # Older account outranks the newer same-balance one.
    order = [w["account_id"] for w in wl]
    assert order.index("B") < order.index("A")
    assert res.data["summary"]["total_ar"] == 5200.0


async def test_ar_prioritizer_timely_filing_flags():
    skill = ARPrioritizerSkill()
    res = await skill.run(action="prioritize", accounts=[
        {"account_id": "X", "balance": 50, "age_days": 85, "payer_class": "commercial"},  # 90-day window
        {"account_id": "Y", "balance": 50, "age_days": 95, "payer_class": "commercial"},
    ])
    by_id = {w["account_id"]: w for w in res.data["worklist"]}
    assert by_id["X"]["timely_filing_at_risk"] is True
    assert by_id["Y"]["timely_filing_expired"] is True


async def test_ar_aging_summary_only():
    skill = ARPrioritizerSkill()
    res = await skill.run(action="aging_summary", accounts=[
        {"account_id": "A", "balance": 100, "age_days": 10},
        {"account_id": "B", "balance": 200, "age_days": 100},
    ])
    assert res.success
    assert "worklist" not in res.data
    labels = {b["bucket"] for b in res.data["buckets"]}
    assert "0-30" in labels and "91-120" in labels


# -------------------------------------------------------------------------- KPI
async def test_kpi_calculates_and_grades():
    skill = RCMKPICalculatorSkill()
    res = await skill.run(
        total_ar=400000, average_daily_charges=10000,
        total_claims=1000, clean_claims=970, denied_claims=40,
        total_charges=1000000, total_payments=600000, contractual_adjustments=380000,
        ar_over_90=80000,
    )
    assert res.success
    kpis = res.data["kpis"]
    assert kpis["days_in_ar"]["value"] == 40.0
    assert kpis["days_in_ar"]["status"] == "good"
    assert kpis["clean_claim_rate"]["value"] == 97.0
    assert kpis["denial_rate"]["value"] == 4.0
    # net collection = 600000 / (1000000-380000) = 96.77%
    assert kpis["net_collection_rate"]["value"] == pytest.approx(96.8, abs=0.1)


async def test_kpi_requires_some_input():
    skill = RCMKPICalculatorSkill()
    res = await skill.run(total_ar=100)  # no denominator → nothing computable
    assert res.success is False


async def test_kpi_partial_inputs():
    skill = RCMKPICalculatorSkill()
    res = await skill.run(total_claims=100, denied_claims=12)
    assert res.success
    assert res.data["kpis"]["denial_rate"]["value"] == 12.0
    assert res.data["kpis"]["denial_rate"]["status"] == "poor"
    assert "denial_rate" in res.data["needs_attention"]


# ----------------------------------------------------------------- underpayment
async def test_underpayment_detects_variance():
    skill = UnderpaymentDetectorSkill()
    res = await skill.run(lines=[
        {"cpt": "99214", "units": 1, "expected_rate": 120.0, "paid_amount": 100.0},
        {"cpt": "85025", "units": 1, "expected_rate": 15.0, "paid_amount": 15.0},  # fully paid
        {"cpt": "99214", "units": 2, "expected_rate": 120.0, "paid_amount": 200.0},  # 40 short
    ])
    assert res.success
    s = res.data["summary"]
    assert s["lines_underpaid"] == 2
    assert s["total_recoverable_variance"] == 60.0
    # Largest variance first.
    assert res.data["underpaid_lines"][0]["variance"] == 40.0
    # By-CPT aggregation.
    cpt_map = {c["cpt"]: c["variance"] for c in res.data["by_cpt"]}
    assert cpt_map["99214"] == 60.0


async def test_underpayment_tolerance():
    skill = UnderpaymentDetectorSkill()
    res = await skill.run(
        lines=[{"cpt": "X", "units": 1, "expected_rate": 100.0, "paid_amount": 99.5}],
        tolerance=1.0,
    )
    assert res.data["summary"]["lines_underpaid"] == 0  # within tolerance
