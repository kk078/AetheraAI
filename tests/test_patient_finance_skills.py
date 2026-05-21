"""Tests for patient-financial and timely-filing skills."""

from datetime import date, timedelta

import pytest

from skills.healthcare.patient_cost_estimator import PatientCostEstimatorSkill
from skills.healthcare.timely_filing_calculator import TimelyFilingCalculatorSkill


# --------------------------------------------------------------- cost estimator
async def test_estimate_deductible_and_coinsurance():
    skill = PatientCostEstimatorSkill()
    # allowed 200, deductible remaining 50, 20% coinsurance, no copay
    res = await skill.run(charge=300, allowed_amount=200, deductible_remaining=50,
                          coinsurance_rate=0.2)
    assert res.success
    d = res.data
    # deductible 50 + 20% of (200-50)=30 → 80
    assert d["estimated_patient_responsibility"] == 80.0
    assert d["breakdown"]["deductible_applied"] == 50.0
    assert d["breakdown"]["coinsurance"] == 30.0
    assert d["contractual_adjustment"] == 100.0  # 300 - 200


async def test_estimate_capped_at_oop_max():
    skill = PatientCostEstimatorSkill()
    res = await skill.run(charge=1000, allowed_amount=1000, deductible_remaining=1000,
                          coinsurance_rate=0.0, oop_max_remaining=250)
    assert res.data["estimated_patient_responsibility"] == 250.0
    assert res.data["breakdown"]["capped_at_oop_max"] is True


async def test_good_faith_estimate():
    skill = PatientCostEstimatorSkill()
    res = await skill.run(action="good_faith_estimate", items=[
        {"description": "Office visit", "code": "99213", "charge": 150},
        {"description": "Lab", "code": "85025", "charge": 50},
    ])
    assert res.success
    gfe = res.data["good_faith_estimate"]
    assert gfe["total_estimate"] == 200.0
    assert gfe["dispute_threshold"] == 600.0
    assert "No Surprises Act" in res.data["disclaimer"]


async def test_estimate_requires_charge():
    skill = PatientCostEstimatorSkill()
    res = await skill.run(action="estimate", deductible_remaining=100)
    assert res.success is False


# -------------------------------------------------------------- timely filing
async def test_timely_filing_status_buckets():
    skill = TimelyFilingCalculatorSkill()
    today = date.today()

    ok = await skill.run(date_of_service=today.isoformat(), payer_class="medicare")
    assert ok.data["status"] == "ok"
    assert ok.data["filing_limit_days"] == 365

    at_risk_dos = (today - timedelta(days=85)).isoformat()
    ar = await skill.run(date_of_service=at_risk_dos, payer_class="commercial")  # 90-day
    assert ar.data["status"] == "at_risk"

    expired_dos = (today - timedelta(days=120)).isoformat()
    exp = await skill.run(date_of_service=expired_dos, payer_class="commercial")
    assert exp.data["status"] == "expired"
    assert exp.data["days_remaining"] < 0


async def test_timely_filing_explicit_limit_and_batch():
    skill = TimelyFilingCalculatorSkill()
    today = date.today()
    res = await skill.run(action="batch", as_of=today.isoformat(), claims=[
        {"date_of_service": today.isoformat(), "payer_class": "commercial"},
        {"date_of_service": (today - timedelta(days=400)).isoformat(), "payer_class": "medicare"},
        {"date_of_service": today.isoformat(), "filing_limit_days": 30},
    ])
    assert res.success
    assert res.data["expired"] == 1
    assert len(res.data["results"]) == 3


async def test_timely_filing_requires_dos():
    skill = TimelyFilingCalculatorSkill()
    res = await skill.run(action="calculate", payer_class="medicare")
    assert res.success is False
