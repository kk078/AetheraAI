"""Tests for general-productivity builtin skills."""

import pytest

from skills.builtin.structured_extractor import StructuredExtractorSkill
from skills.builtin.data_insights import DataInsightsSkill


# ----------------------------------------------------------- structured extractor
async def test_extract_builtin_types():
    skill = StructuredExtractorSkill()
    text = "Contact jane@doe.com or 555-123-4567. DOB 03/14/1980. Claim total $1,250.00."
    res = await skill.run(text=text, fields=[
        {"name": "email", "type": "email"},
        {"name": "phone", "type": "phone"},
        {"name": "dob", "type": "date"},
        {"name": "amount", "type": "money"},
    ])
    assert res.success
    ex = res.data["extracted"]
    assert ex["email"] == "jane@doe.com"
    assert ex["dob"] == "03/14/1980"
    assert res.data["fields_found"] == 4


async def test_extract_keyword_and_all():
    skill = StructuredExtractorSkill()
    text = "Provider: Dr. Smith\nNPI 1234567890\nNPI 9876543210"
    res = await skill.run(action="extract", text=text, fields=[
        {"name": "provider", "keyword": "Provider"},
    ])
    assert res.data["extracted"]["provider"].startswith("Dr. Smith")

    res_all = await skill.run(action="extract_all", text=text, fields=[
        {"name": "npis", "type": "npi"},
    ])
    assert res_all.data["extracted"]["npis"] == ["1234567890", "9876543210"]


async def test_extract_custom_regex_and_missing():
    skill = StructuredExtractorSkill()
    res = await skill.run(text="Order #A1B2 placed.", fields=[
        {"name": "order", "regex": r"#([A-Z0-9]+)"},
        {"name": "absent", "type": "email"},
    ])
    assert res.data["extracted"]["order"] == "A1B2"
    assert res.data["extracted"]["absent"] is None


async def test_extract_requires_text():
    skill = StructuredExtractorSkill()
    res = await skill.run(text="", fields=[{"name": "x", "type": "email"}])
    assert res.success is False


# ----------------------------------------------------------------- data insights
SAMPLE = [
    {"payer": "A", "amount": 100},
    {"payer": "A", "amount": 300},
    {"payer": "B", "amount": 200},
    {"payer": "B", "amount": 5000},
]


async def test_describe():
    skill = DataInsightsSkill()
    res = await skill.run(action="describe", records=SAMPLE, fields=["amount"])
    assert res.success
    f = res.data["fields"]["amount"]
    assert f["count"] == 4
    assert f["sum"] == 5600
    assert f["max"] == 5000


async def test_group_by_sum():
    skill = DataInsightsSkill()
    res = await skill.run(action="group_by", records=SAMPLE,
                          group_field="payer", agg_field="amount", agg="sum")
    by = {g["group"]: g["value"] for g in res.data["groups"]}
    assert by["A"] == 400
    assert by["B"] == 5200


async def test_group_by_count():
    skill = DataInsightsSkill()
    res = await skill.run(action="group_by", records=SAMPLE, group_field="payer", agg="count")
    by = {g["group"]: g["value"] for g in res.data["groups"]}
    assert by["A"] == 2 and by["B"] == 2


async def test_outliers():
    skill = DataInsightsSkill()
    res = await skill.run(action="outliers", records=SAMPLE, field="amount", z_threshold=1.4)
    assert res.success
    vals = [o["value"] for o in res.data["outliers"]]
    assert 5000 in vals


async def test_describe_infers_numeric_fields():
    skill = DataInsightsSkill()
    res = await skill.run(action="describe", records=SAMPLE)
    assert "amount" in res.data["fields"]
