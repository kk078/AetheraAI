"""
Aethera AI - Knowledge Updater

Automatically fetches and applies updates from:
- CMS transmittals and manual updates
- Federal Register CMS-related documents
- FDA safety alerts and recalls
- OIG work plan updates
- NVD CVEs (National Vulnerability Database)
- CISA cybersecurity advisories

Each source is checked on its own schedule:
- CMS Transmittals: Every 12 hours
- Federal Register: Every 8 hours
- FDA Safety Alerts: Every 6 hours
- OIG Work Plan: Every 24 hours
- NVD CVEs: Every 4 hours
- CISA Alerts: Every 4 hours

Supports: check updates, apply updates, get changelog.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("KNOWLEDGE_UPDATER_DB_PATH", "/data/proactive_knowledge_updates.db")

# Source URLs
SOURCES = {
    "cms_transmittals": {
        "url": "https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals",
        "api_url": "https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/AcuteInpatientPPS/Downloads/CMS-Transmittals-List.json",
        "interval_hours": 12,
        "category": "healthcare_regulatory",
    },
    "federal_register": {
        "url": "https://www.federalregister.gov/api/v1/documents.json",
        "api_url": "https://www.federalregister.gov/api/v1/documents.json",
        "params": {
            "conditions[agencies]": "centers-for-medicare-medicaid-services",
            "order": "newest",
            "per_page": 20,
        },
        "interval_hours": 8,
        "category": "healthcare_regulatory",
    },
    "fda_safety": {
        "url": "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
        "api_url": "https://api.fda.gov/safety/recalls.json",
        "params": {"limit": 20},
        "interval_hours": 6,
        "category": "healthcare_regulatory",
    },
    "oig_work_plan": {
        "url": "https://oig.hhs.gov/reports-and-publications/workplan/",
        "api_url": "https://oig.hhs.gov/reports-and-publications/workplan/wp-items-featured.json",
        "interval_hours": 24,
        "category": "healthcare_regulatory",
    },
    "nvd_cves": {
        "url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
        "api_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
        "params": {"resultsPerPage": 20},
        "interval_hours": 4,
        "category": "security",
    },
    "cisa_alerts": {
        "url": "https://www.cisa.gov/news-events/cybersecurity-advisories",
        "api_url": "https://www.cisa.gov/sites/default/files/feeds/ICS_Advisories.xml",
        "interval_hours": 4,
        "category": "security",
    },
}


class KnowledgeUpdate:
    """Represents a single knowledge update entry."""

    __slots__ = (
        "id", "source", "source_key", "title", "summary",
        "url", "category", "published_date", "fetched_at",
        "applied", "applied_at", "metadata",
    )

    def __init__(
        self,
        id: str,
        source: str,
        source_key: str,
        title: str,
        summary: str = "",
        url: str = "",
        category: str = "general",
        published_date: Optional[str] = None,
        fetched_at: Optional[str] = None,
        applied: bool = False,
        applied_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.source = source
        self.source_key = source_key
        self.title = title
        self.summary = summary
        self.url = url
        self.category = category
        self.published_date = published_date
        self.fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
        self.applied = applied
        self.applied_at = applied_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_key": self.source_key,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "category": self.category,
            "published_date": self.published_date,
            "fetched_at": self.fetched_at,
            "applied": self.applied,
            "applied_at": self.applied_at,
            "metadata": self.metadata,
        }


class KnowledgeUpdater:
    """
    Auto-fetches CMS, FDA, NVD, and regulatory updates.
    Stores updates in SQLite with deduplication.
    Supports checking, applying, and querying the update changelog.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        http_timeout: int = 30,
        user_agent: str = "AetheraAI-KnowledgeUpdater/1.0",
    ):
        self._db_path = db_path
        self._http_timeout = http_timeout
        self._user_agent = user_agent
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the knowledge_updates table."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_updates (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT DEFAULT '',
                url TEXT DEFAULT '',
                category TEXT NOT NULL DEFAULT 'general',
                published_date TEXT,
                fetched_at TEXT NOT NULL,
                applied INTEGER DEFAULT 0,
                applied_at TEXT,
                metadata JSON DEFAULT '{}'
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_updates_source_key
                ON knowledge_updates(source, source_key);

            CREATE INDEX IF NOT EXISTS idx_updates_category ON knowledge_updates(category);
            CREATE INDEX IF NOT EXISTS idx_updates_fetched ON knowledge_updates(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_updates_applied ON knowledge_updates(applied);
        """)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------------
    # Check Updates
    # ---------------------------------------------------------------------------

    def check_updates(self, sources: Optional[List[str]] = None) -> Dict[str, List[KnowledgeUpdate]]:
        """
        Check all configured sources for new updates.

        Args:
            sources: Optional list of source keys to check (e.g., ["nvd_cves", "fda_safety"]).
                    If None, checks all sources that are due.

        Returns:
            Dict mapping source key to list of new KnowledgeUpdate objects.
        """
        results: Dict[str, List[KnowledgeUpdate]] = {}
        source_keys = sources or list(SOURCES.keys())

        for key in source_keys:
            if key not in SOURCES:
                logger.warning("Unknown source: %s", key)
                continue

            # Check if source is due for a refresh
            if not sources and not self._is_source_due(key):
                logger.debug("Source %s not due yet, skipping", key)
                continue

            try:
                new_updates = self._fetch_source(key)
                if new_updates:
                    results[key] = new_updates
                    logger.info("Source %s: %d new updates", key, len(new_updates))
            except Exception as exc:
                logger.error("Fetch from %s failed: %s", key, exc)

        return results

    def _is_source_due(self, source_key: str) -> bool:
        """Check if a source is due for a refresh based on its interval."""
        source_config = SOURCES.get(source_key, {})
        interval_hours = source_config.get("interval_hours", 24)

        # Find the most recent fetch for this source
        row = self._conn.execute(
            "SELECT MAX(fetched_at) as last_fetch FROM knowledge_updates WHERE source = ?",
            (source_key,),
        ).fetchone()

        if not row or not row["last_fetch"]:
            return True

        try:
            last_fetch = datetime.fromisoformat(row["last_fetch"])
            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_fetch).total_seconds()
            return elapsed >= interval_hours * 3600
        except (ValueError, TypeError):
            return True

    def _fetch_source(self, source_key: str) -> List[KnowledgeUpdate]:
        """Fetch updates from a specific source."""
        config = SOURCES[source_key]
        source_name = config.get("category", "general")
        new_updates: List[KnowledgeUpdate] = []

        fetcher_map = {
            "federal_register": self._fetch_federal_register,
            "fda_safety": self._fetch_fda_safety,
            "nvd_cves": self._fetch_nvd_cves,
            "cisa_alerts": self._fetch_cisa_alerts,
            "cms_transmittals": self._fetch_cms_transmittals,
            "oig_work_plan": self._fetch_oig_work_plan,
        }

        fetcher = fetcher_map.get(source_key)
        if fetcher:
            items = fetcher(config)
        else:
            items = self._fetch_generic(config)

        now_iso = datetime.now(timezone.utc).isoformat()

        for item in items:
            # Deduplicate by source + source_key
            existing = self._conn.execute(
                "SELECT id FROM knowledge_updates WHERE source = ? AND source_key = ?",
                (source_key, item["source_key"]),
            ).fetchone()

            if existing:
                continue

            update = KnowledgeUpdate(
                id=f"ku_{uuid.uuid4().hex[:12]}",
                source=source_key,
                source_key=item["source_key"],
                title=item.get("title", "Untitled"),
                summary=item.get("summary", ""),
                url=item.get("url", ""),
                category=config.get("category", "general"),
                published_date=item.get("published_date"),
                fetched_at=now_iso,
                metadata=item.get("metadata", {}),
            )

            self._conn.execute(
                """INSERT INTO knowledge_updates
                   (id, source, source_key, title, summary, url, category,
                    published_date, fetched_at, applied, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (
                    update.id, update.source, update.source_key,
                    update.title, update.summary, update.url,
                    update.category, update.published_date,
                    update.fetched_at, json.dumps(update.metadata),
                ),
            )
            new_updates.append(update)

        if new_updates:
            self._conn.commit()

        return new_updates

    # ---------------------------------------------------------------------------
    # Source-Specific Fetchers
    # ---------------------------------------------------------------------------

    def _fetch_federal_register(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch CMS-related documents from the Federal Register API."""
        api_url = config.get("api_url", "")
        params = dict(config.get("params", {}))

        # Add date filter for last 7 days
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        params["conditions[publication_date][gte]"] = start_date

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = []
            for doc in data.get("results", []):
                items.append({
                    "source_key": doc.get("document_number", doc.get("id", "")),
                    "title": doc.get("title", "Untitled"),
                    "summary": doc.get("abstract", "")[:500] if doc.get("abstract") else "",
                    "url": doc.get("html_url", ""),
                    "published_date": doc.get("publication_date", ""),
                    "metadata": {
                        "type": doc.get("type", ""),
                        "agencies": [a.get("name", "") for a in doc.get("agencies", [])],
                        "action": doc.get("action", ""),
                    },
                })
            return items
        except Exception as exc:
            logger.error("Federal Register fetch failed: %s", exc)
            return []

    def _fetch_fda_safety(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch FDA safety alerts and recalls."""
        api_url = config.get("api_url", "")
        params = dict(config.get("params", {}))

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = []
            results = data.get("results", []) if isinstance(data, dict) else data
            if isinstance(results, list):
                for recall in results:
                    items.append({
                        "source_key": recall.get("recall_number", recall.get("id", "")),
                        "title": recall.get("product_description", recall.get("title", "FDA Safety Alert")),
                        "summary": recall.get("reason_for_recall", "")[:500],
                        "url": recall.get("url", "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"),
                        "published_date": recall.get("report_date", recall.get("date_initiated", "")),
                        "metadata": {
                            "classification": recall.get("classification", ""),
                            "product_type": recall.get("product_type", ""),
                            "firm": recall.get("recalling_firm", ""),
                        },
                    })
            return items
        except Exception as exc:
            logger.error("FDA safety fetch failed: %s", exc)
            return []

    def _fetch_nvd_cves(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch recent CVEs from NVD."""
        api_url = config.get("api_url", "")
        params = dict(config.get("params", {}))

        # Filter for recent CVEs
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000")
        params["pubStartDate"] = start_date

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = []
            vulnerabilities = data.get("vulnerabilities", [])
            for vuln in vulnerabilities:
                cve = vuln.get("cve", {})
                cve_id = cve.get("id", "")

                # Extract CVSS score
                metrics = cve.get("metrics", {})
                cvss_score = 0.0
                for version_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                    if version_key in metrics and metrics[version_key]:
                        cvss_score = metrics[version_key][0].get("cvssData", {}).get("baseScore", 0.0)
                        break

                # Extract description
                descriptions = cve.get("descriptions", [])
                desc_text = ""
                for desc in descriptions:
                    if desc.get("lang") == "en":
                        desc_text = desc.get("value", "")[:500]
                        break

                items.append({
                    "source_key": cve_id,
                    "title": f"{cve_id} (CVSS {cvss_score})",
                    "summary": desc_text,
                    "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "published_date": cve.get("published", ""),
                    "metadata": {
                        "cvss_score": cvss_score,
                        "cve_id": cve_id,
                    },
                })
            return items
        except Exception as exc:
            logger.error("NVD CVE fetch failed: %s", exc)
            return []

    def _fetch_cisa_alerts(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch CISA ICS cybersecurity advisories from RSS/XML feed."""
        api_url = config.get("api_url", "")

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url)
                resp.raise_for_status()

            root = ElementTree.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            items = []
            for entry in root.findall(".//atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                summary_el = entry.find("atom:summary", ns)
                published_el = entry.find("atom:published", ns)
                id_el = entry.find("atom:id", ns)

                title = title_el.text if title_el is not None and title_el.text else "CISA Advisory"
                link = link_el.get("href", "") if link_el is not None else ""
                summary = summary_el.text[:500] if summary_el is not None and summary_el.text else ""
                published = published_el.text if published_el is not None and published_el.text else ""
                source_key = id_el.text if id_el is not None and id_el.text else link

                items.append({
                    "source_key": source_key,
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "published_date": published,
                    "metadata": {},
                })
            return items
        except Exception as exc:
            logger.error("CISA alerts fetch failed: %s", exc)
            return []

    def _fetch_cms_transmittals(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch CMS transmittals. Falls back to the CMS website scraping."""
        # CMS does not provide a clean JSON API for transmittals.
        # Use the Federal Register CMS filter as the primary source.
        try:
            fr_config = SOURCES.get("federal_register", {})
            items = self._fetch_federal_register(fr_config)
            # Tag them as CMS transmittals specifically
            for item in items:
                metadata = item.get("metadata", {})
                if "transmittal" in item.get("title", "").lower():
                    item["source_key"] = f"transmittal_{item['source_key']}"
            return items
        except Exception as exc:
            logger.error("CMS transmittals fetch failed: %s", exc)
            return []

    def _fetch_oig_work_plan(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch OIG work plan updates."""
        api_url = config.get("api_url", "")

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url)
                # OIG may return 404 for JSON endpoint; fall back gracefully
                if resp.status_code == 404:
                    logger.debug("OIG JSON endpoint not available, skipping")
                    return []
                resp.raise_for_status()
                data = resp.json()

            items = []
            if isinstance(data, list):
                for entry in data:
                    items.append({
                        "source_key": str(entry.get("id", "")),
                        "title": entry.get("title", "OIG Work Plan Item"),
                        "summary": entry.get("summary", entry.get("description", ""))[:500],
                        "url": entry.get("url", "https://oig.hhs.gov/reports-and-publications/workplan/"),
                        "published_date": entry.get("published_date", entry.get("date", "")),
                        "metadata": {},
                    })
            return items
        except Exception as exc:
            logger.error("OIG work plan fetch failed: %s", exc)
            return []

    def _fetch_generic(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic fetcher for sources without a specialized parser."""
        api_url = config.get("api_url", "")
        params = dict(config.get("params", {}))

        try:
            with httpx.Client(timeout=self._http_timeout, headers={"User-Agent": self._user_agent}) as client:
                resp = client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = []
            if isinstance(data, dict):
                results = data.get("results", data.get("items", data.get("data", [])))
            elif isinstance(data, list):
                results = data
            else:
                return []

            for entry in results[:20]:
                if isinstance(entry, dict):
                    items.append({
                        "source_key": str(entry.get("id", entry.get("document_number", ""))),
                        "title": entry.get("title", "Untitled Update"),
                        "summary": entry.get("summary", entry.get("abstract", ""))[:500],
                        "url": entry.get("url", entry.get("html_url", "")),
                        "published_date": entry.get("published_date", entry.get("date", "")),
                        "metadata": {},
                    })
            return items
        except Exception as exc:
            logger.error("Generic fetch from %s failed: %s", api_url, exc)
            return []

    # ---------------------------------------------------------------------------
    # Apply Updates
    # ---------------------------------------------------------------------------

    def apply_updates(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[KnowledgeUpdate]:
        """
        Mark pending updates as applied.

        Args:
            source: Only apply updates from this source.
            category: Only apply updates in this category.
            limit: Maximum updates to apply.

        Returns:
            List of applied KnowledgeUpdate objects.
        """
        query = "SELECT * FROM knowledge_updates WHERE applied = 0"
        params: List[Any] = []

        if source:
            query += " AND source = ?"
            params.append(source)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY fetched_at ASC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        applied: List[KnowledgeUpdate] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in rows:
            update = self._row_to_update(row)
            self._conn.execute(
                "UPDATE knowledge_updates SET applied = 1, applied_at = ? WHERE id = ?",
                (now_iso, update.id),
            )
            update.applied = True
            update.applied_at = now_iso
            applied.append(update)

        if applied:
            self._conn.commit()
            logger.info("Applied %d knowledge updates", len(applied))

        return applied

    # ---------------------------------------------------------------------------
    # Get Changelog
    # ---------------------------------------------------------------------------

    def get_changelog(
        self,
        days: int = 7,
        source: Optional[str] = None,
        category: Optional[str] = None,
        applied_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get the changelog of recent knowledge updates.

        Args:
            days: How many days back to look.
            source: Filter by source key.
            category: Filter by category.
            applied_only: Only include applied updates.
            limit: Maximum entries to return.

        Returns:
            List of update dicts.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = "SELECT * FROM knowledge_updates WHERE fetched_at >= ?"
        params: List[Any] = [cutoff]

        if source:
            query += " AND source = ?"
            params.append(source)
        if category:
            query += " AND category = ?"
            params.append(category)
        if applied_only:
            query += " AND applied = 1"

        query += " ORDER BY fetched_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_update(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge updater statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM knowledge_updates").fetchone()[0]
        pending = self._conn.execute(
            "SELECT COUNT(*) FROM knowledge_updates WHERE applied = 0"
        ).fetchone()[0]
        applied = self._conn.execute(
            "SELECT COUNT(*) FROM knowledge_updates WHERE applied = 1"
        ).fetchone()[0]

        by_source = {}
        for key in SOURCES:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM knowledge_updates WHERE source = ?",
                (key,),
            ).fetchone()[0]
            if count > 0:
                by_source[key] = count

        by_category = {}
        for cat in ["healthcare_regulatory", "security", "general"]:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM knowledge_updates WHERE category = ?",
                (cat,),
            ).fetchone()[0]
            if count > 0:
                by_category[cat] = count

        return {
            "total": total,
            "pending": pending,
            "applied": applied,
            "by_source": by_source,
            "by_category": by_category,
            "sources_configured": len(SOURCES),
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_update(row: sqlite3.Row) -> KnowledgeUpdate:
        """Convert a database row to a KnowledgeUpdate."""
        d = dict(row)
        metadata_raw = d.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = metadata_raw or {}

        return KnowledgeUpdate(
            id=d["id"],
            source=d["source"],
            source_key=d["source_key"],
            title=d["title"],
            summary=d.get("summary", ""),
            url=d.get("url", ""),
            category=d.get("category", "general"),
            published_date=d.get("published_date"),
            fetched_at=d["fetched_at"],
            applied=bool(d.get("applied", 0)),
            applied_at=d.get("applied_at"),
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_updater: Optional[KnowledgeUpdater] = None


def get_knowledge_updater(db_path: str = DEFAULT_DB_PATH) -> KnowledgeUpdater:
    """Get or create the singleton KnowledgeUpdater instance."""
    global _updater
    if _updater is None:
        _updater = KnowledgeUpdater(db_path=db_path)
    return _updater