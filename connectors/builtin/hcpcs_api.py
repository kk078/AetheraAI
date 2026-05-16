"""
HCPCS Code Lookup Connector for Aethera
Fetches Healthcare Common Procedure Coding System codes from CMS.
Uses CMS HCPCS release data. No authentication required.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class HCPCSConnector(AetheraConnector):
    """HCPCS code lookup connector for Medicare procedure codes."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get(
            "base_url",
            "https://data.cms.gov/provider-data/api/1/datastore/query/",
        )
        self.hcpcs_dataset_id = config.get("dataset_id", "h8vv-9qkk")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._code_cache: Dict[str, Dict] = {}

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="hcpcs",
            version="1.0.0",
            description="HCPCS - Healthcare Common Procedure Coding System code lookup",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json"},
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._code_cache.clear()

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search HCPCS codes by description or code.

        Keyword Args:
            year: HCPCS release year (default '2024').
            limit: Max results (1-500, default 50).
            offset: Result offset.
        """
        limit = min(int(params.get("limit", 50)), 500)
        offset = int(params.get("offset", 0))

        qp: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if query:
            qp["search"] = query

        url = f"{self.hcpcs_dataset_id}/0"

        try:
            response = await self._rate_limited_request("GET", url, params=qp)
            data = response.json()
            results = data if isinstance(data, list) else data.get("results", data.get("data", []))
            normalized = [self._normalize_code(r) for r in results]
            return ConnectorResult(
                success=True,
                data=normalized,
                metadata={
                    "source": "HCPCS",
                    "total": len(normalized),
                    "offset": offset,
                    "limit": limit,
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HCPCS API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Look up a specific HCPCS code.

        Args:
            item_id: HCPCS code (e.g. '99213', 'J1745').
        """
        if not item_id:
            return ConnectorResult(success=False, error="HCPCS code required")

        # Check cache first
        if item_id in self._code_cache:
            return ConnectorResult(
                success=True,
                data=self._code_cache[item_id],
                metadata={"source": "HCPCS", "cached": True},
            )

        # Search by exact code
        try:
            url = f"{self.hcpcs_dataset_id}/0"
            response = await self._rate_limited_request(
                "GET", url, params={"search": item_id, "limit": 10}
            )
            data = response.json()
            results = data if isinstance(data, list) else data.get("results", data.get("data", []))

            for r in results:
                normalized = self._normalize_code(r)
                if normalized.get("code", "").upper() == item_id.upper():
                    self._code_cache[item_id] = normalized
                    return ConnectorResult(
                        success=True,
                        data=normalized,
                        metadata={"source": "HCPCS", "code": item_id},
                    )

            return ConnectorResult(success=False, error=f"HCPCS code '{item_id}' not found")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("code", params.pop("id", "")), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_code(record: Dict) -> Dict:
        return {
            "code": record.get("hcpcs_code", record.get("HCPCS_Code", record.get("code", ""))),
            "description": record.get("long_description", record.get("Long_Description", record.get("description", ""))),
            "short_description": record.get("short_description", record.get("Short_Description", "")),
            "category": record.get("hcpcs_category", record.get("category", "")),
            "effective_date": record.get("effective_date", record.get("Effective_Date", "")),
            "action_code": record.get("action_code", record.get("Action_Code", "")),
            "coverage": record.get("coverage", record.get("Coverage", "")),
        }

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
                    "description": "Search HCPCS codes by description or code",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search term"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-500)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Look up a specific HCPCS code",
                    "parameters": [
                        {"name": "code", "type": "string", "required": True, "description": "HCPCS code (e.g. 99213)"},
                    ],
                },
            ],
        }


def register_connector():
    return HCPCSConnector, {
        "base_url": "https://data.cms.gov/provider-data/api/1/datastore/query/",
        "dataset_id": "h8vv-9qkk",
    }