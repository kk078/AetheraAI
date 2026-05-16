"""
NUCC Provider Taxonomy Connector for Aethera
Fetches provider taxonomy codes from the NUCC classification.
Data source: https://www.nucc.org/ (static taxonomy data file).
No authentication required.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class NUCCTaxonomyConnector(AetheraConnector):
    """NUCC provider taxonomy code connector."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get(
            "base_url",
            "https://www.nucc.org/static/",
        )
        self.data_url = config.get(
            "data_url",
            "https://www.nucc.org/static/CodeSystem/Taxonomy22/nucc-taxonomy-2024.csv",
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._taxonomy_cache: List[Dict] = []
        self._cache_loaded: bool = False

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="nucc_taxonomy",
            version="1.0.0",
            description="NUCC Provider Taxonomy - Healthcare provider classification codes",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=30,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            timeout=self.get_config().timeout,
            headers={"Accept": "text/csv, application/json", "User-Agent": "AetheraAI/1.0"},
            follow_redirects=True,
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._taxonomy_cache.clear()
        self._cache_loaded = False

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        config = self.get_config()
        if config.rate_limit:
            min_interval = 60.0 / config.rate_limit
            async with self._rate_limit_lock:
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = asyncio.get_event_loop().time()

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await _do_request()

    async def _ensure_cache(self) -> None:
        """Load taxonomy data into memory cache if not already loaded."""
        if self._cache_loaded:
            return

        try:
            response = await self._rate_limited_request("GET", self.data_url)
            text = response.text
            self._taxonomy_cache = self._parse_csv(text)
            self._cache_loaded = True
        except Exception:
            # If CSV download fails, leave cache empty
            self._cache_loaded = True

    @staticmethod
    def _parse_csv(text: str) -> List[Dict]:
        """Parse the NUCC taxonomy CSV."""
        results: List[Dict] = []
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return results

        # Detect delimiter and header
        header_line = lines[0]
        delimiter = "\t" if "\t" in header_line else ","
        headers = [h.strip().strip('"') for h in header_line.split(delimiter)]

        for line in lines[1:]:
            if not line.strip():
                continue
            fields = [f.strip().strip('"') for f in line.split(delimiter)]
            if len(fields) >= len(headers):
                row = dict(zip(headers, fields))
                results.append({
                    "code": row.get("Code", row.get("code", "")),
                    "display": row.get("Display", row.get("display", row.get("Classification", ""))),
                    "definition": row.get("Definition", row.get("definition", "")),
                    "type": row.get("Type", row.get("type", "")),
                    "grouping": row.get("Grouping", row.get("grouping", "")),
                    "specialization": row.get("Specialization", row.get("specialization", "")),
                })
        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search NUCC taxonomy codes by name or description.

        Keyword Args:
            grouping: Filter by grouping (e.g. 'Allopathic & Osteopathic Physicians').
            type: Filter by type (e.g. 'Behavioral Health & Social Service Providers').
            limit: Max results (default 20).
        """
        await self._ensure_cache()

        if not self._taxonomy_cache:
            return ConnectorResult(success=False, error="Taxonomy data unavailable")

        query_lower = query.lower() if query else ""
        grouping_filter = (params.get("grouping") or "").lower()
        type_filter = (params.get("type") or "").lower()
        limit = int(params.get("limit", 20))

        matches: List[Dict] = []
        for entry in self._taxonomy_cache:
            if grouping_filter and grouping_filter not in entry.get("grouping", "").lower():
                continue
            if type_filter and type_filter not in entry.get("type", "").lower():
                continue
            if query_lower:
                searchable = f"{entry.get('code', '')} {entry.get('display', '')} {entry.get('definition', '')}".lower()
                if query_lower not in searchable:
                    continue
            matches.append(entry)
            if len(matches) >= limit:
                break

        return ConnectorResult(
            success=True,
            data=matches,
            metadata={
                "source": "NUCC Taxonomy",
                "total_available": len(self._taxonomy_cache),
                "returned": len(matches),
            },
        )

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Look up a specific taxonomy code.

        Args:
            item_id: NUCC taxonomy code (e.g. '207Q00000X').
        """
        await self._ensure_cache()

        if not self._taxonomy_cache:
            return ConnectorResult(success=False, error="Taxonomy data unavailable")

        for entry in self._taxonomy_cache:
            if entry.get("code", "").lower() == item_id.lower():
                return ConnectorResult(
                    success=True,
                    data=entry,
                    metadata={"source": "NUCC Taxonomy", "code": item_id},
                )

        return ConnectorResult(success=False, error=f"Taxonomy code '{item_id}' not found")

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("code", params.pop("id", "")), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "endpoints": [
                {
                    "name": "search",
                    "description": "Search NUCC provider taxonomy codes",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search by name or description"},
                        {"name": "grouping", "type": "string", "description": "Filter by grouping"},
                        {"name": "type", "type": "string", "description": "Filter by provider type"},
                        {"name": "limit", "type": "integer", "description": "Max results"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Look up a specific taxonomy code",
                    "parameters": [
                        {"name": "code", "type": "string", "required": True, "description": "NUCC taxonomy code"},
                    ],
                },
            ],
        }


def register_connector():
    return NUCCTaxonomyConnector, {
        "base_url": "https://www.nucc.org/static/",
        "data_url": "https://www.nucc.org/static/CodeSystem/Taxonomy22/nucc-taxonomy-2024.csv",
    }