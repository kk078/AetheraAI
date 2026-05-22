"""
Tests for the CMS auto-adaptation features of the knowledge updater
(proactive/knowledge_updater.py): the data.cms.gov fetcher, auto-update
routine, and prompt-injection context. HTTP is mocked; no live network.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from proactive.knowledge_updater import (
    KnowledgeUpdater,
    SOURCES,
    _parse_date,
)


@pytest.fixture
def updater(tmp_path):
    ku = KnowledgeUpdater(db_path=str(tmp_path / "ku.db"))
    yield ku
    ku.close()


def _recent(days_ago=1):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _cms_catalog(datasets):
    return {"dataset": datasets}


# ---------------------------------------------------------------------------
# CMS source registration
# ---------------------------------------------------------------------------

def test_cms_data_gov_source_registered():
    assert "cms_data_gov" in SOURCES
    assert SOURCES["cms_data_gov"]["api_url"] == "https://data.cms.gov/data.json"
    assert SOURCES["cms_data_gov"]["category"] == "healthcare_regulatory"


# ---------------------------------------------------------------------------
# _parse_date helper
# ---------------------------------------------------------------------------

def test_parse_date_variants():
    assert _parse_date("2026-05-01") is not None
    assert _parse_date("2026-05-01T12:30:00Z") is not None
    assert _parse_date("2026-05-01T12:30:00+00:00") is not None
    assert _parse_date("") is None
    assert _parse_date(None) is None
    assert _parse_date("not a date") is None
    # Always returns tz-aware
    assert _parse_date("2026-05-01").tzinfo is not None


# ---------------------------------------------------------------------------
# CMS fetcher
# ---------------------------------------------------------------------------

def _mock_httpx_returning(json_payload):
    """Patch httpx.Client so .get().json() returns json_payload."""
    response = MagicMock()
    response.json = MagicMock(return_value=json_payload)
    response.raise_for_status = MagicMock()
    client = MagicMock()
    client.get = MagicMock(return_value=response)
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=client)
    ctx.__exit__ = MagicMock(return_value=False)
    return patch("proactive.knowledge_updater.httpx.Client", return_value=ctx)


def test_fetch_cms_data_gov_keeps_recent_and_drops_old(updater):
    catalog = _cms_catalog([
        {"identifier": "ds-new", "title": "2026 Physician Fee Schedule",
         "description": "Updated rates", "modified": _recent(2),
         "landingPage": "https://data.cms.gov/ds-new"},
        {"identifier": "ds-old", "title": "Ancient dataset",
         "description": "stale", "modified": "2019-01-01"},
    ])
    with _mock_httpx_returning(catalog):
        items = updater._fetch_cms_data_gov(SOURCES["cms_data_gov"])
    keys = {i["source_key"] for i in items}
    assert "ds-new" in keys
    assert "ds-old" not in keys
    new_item = next(i for i in items if i["source_key"] == "ds-new")
    assert new_item["url"] == "https://data.cms.gov/ds-new"
    assert new_item["metadata"]["publisher"] == "CMS"


def test_fetch_cms_data_gov_handles_network_error(updater):
    with patch("proactive.knowledge_updater.httpx.Client", side_effect=Exception("boom")):
        items = updater._fetch_cms_data_gov(SOURCES["cms_data_gov"])
    assert items == []


def test_fetch_cms_data_gov_caps_results(updater):
    datasets = [
        {"identifier": f"ds-{n}", "title": f"Dataset {n}",
         "description": "x", "modified": _recent(1)}
        for n in range(40)
    ]
    with _mock_httpx_returning(_cms_catalog(datasets)):
        items = updater._fetch_cms_data_gov(SOURCES["cms_data_gov"])
    assert len(items) <= 25


# ---------------------------------------------------------------------------
# check / dedup / apply / changelog via the CMS source
# ---------------------------------------------------------------------------

def test_check_updates_persists_and_dedupes(updater):
    catalog = _cms_catalog([
        {"identifier": "ds-1", "title": "PFS 2026", "description": "d", "modified": _recent(1)},
    ])
    with _mock_httpx_returning(catalog):
        first = updater.check_updates(sources=["cms_data_gov"])
    assert len(first["cms_data_gov"]) == 1

    # Second check with same data → deduped, no new rows.
    with _mock_httpx_returning(catalog):
        second = updater.check_updates(sources=["cms_data_gov"])
    assert "cms_data_gov" not in second or second.get("cms_data_gov") == []

    stats = updater.get_stats()
    assert stats["by_source"].get("cms_data_gov") == 1


def test_run_auto_update_applies_regulatory(updater):
    catalog = _cms_catalog([
        {"identifier": "ds-1", "title": "PFS 2026", "description": "d", "modified": _recent(1)},
        {"identifier": "ds-2", "title": "HCPCS update", "description": "d", "modified": _recent(1)},
    ])
    with _mock_httpx_returning(catalog):
        found = updater.check_updates(sources=["cms_data_gov"])
    assert len(found["cms_data_gov"]) == 2

    applied = updater.apply_updates(category="healthcare_regulatory")
    assert len(applied) == 2
    # Re-applying yields nothing (already applied).
    assert updater.apply_updates(category="healthcare_regulatory") == []


def test_get_industry_context_formats_recent_updates(updater):
    catalog = _cms_catalog([
        {"identifier": "ds-1", "title": "2026 Physician Fee Schedule",
         "description": "d", "modified": _recent(1)},
    ])
    with _mock_httpx_returning(catalog):
        updater.check_updates(sources=["cms_data_gov"])

    context = updater.get_industry_context(category="healthcare_regulatory", days=30)
    assert "2026 Physician Fee Schedule" in context
    assert "cms_data_gov" in context


def test_get_industry_context_empty_when_nothing_recent(updater):
    assert updater.get_industry_context(category="healthcare_regulatory") == ""
