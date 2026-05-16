"""
OpenFDA Connector for Aethera
Fetches drug, device, food safety, and adverse event data from the FDA.
API: https://api.fda.gov/
Optional API key increases rate limits (4/sec -> 240/sec).
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult

_OPENFDA_ENDPOINTS = {
    "drug_label": "drug/label.json",
    "drug_event": "drug/event.json",
    "drug_enforcement": "drug/enforcement.json",
    "drug_ndc": "drug/ndc.json",
    "drug_drugsfda": "drug/drugsfda.json",
    "device_event": "device/event.json",
    "device_enforcement": "device/enforcement.json",
    "device_classification": "device/classification.json",
    "device_510k": "device/510k.json",
    "device_pma": "device/pma.json",
    "device_recall": "device/recall.json",
    "device_udid": "device/udid.json",
    "food_event": "food/event.json",
    "food_enforcement": "food/enforcement.json",
    "other_substance": "other/substance.json",
    "other_universal": "other/universal.json",
}


class OpenFDAConnector(AetheraConnector):
    """OpenFDA API connector for drug, device, and food safety data."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.fda.gov/")
        self.api_key = config.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="openfda",
            version="1.0.0",
            description="OpenFDA - Drug, device, and food safety data",
            base_url=self.base_url,
            auth_type="api_key" if self.api_key else "none",
            rate_limit=240 if self.api_key else 4,
            timeout=30,
        )

    async def initialize(self) -> bool:
        headers: Dict[str, str] = {"Accept": "application/json"}
        params: Dict[str, str] = {}
        if self.api_key:
            params["api_key"] = self.api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers=headers,
            params=params,
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

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
        """Search across OpenFDA endpoints.

        Keyword Args:
            category: Endpoint category key (e.g. 'drug_label', 'device_event').
                      Defaults to 'drug_label'.
            limit: Max results (1-1000, default 10).
            skip: Number of results to skip for pagination.
        """
        category = params.pop("category", "drug_label")
        endpoint_path = _OPENFDA_ENDPOINTS.get(category)
        if not endpoint_path:
            return ConnectorResult(
                success=False,
                error=f"Unknown category '{category}'. Valid: {', '.join(_OPENFDA_ENDPOINTS)}",
            )

        qp: Dict[str, Any] = {"limit": min(int(params.pop("limit", 10)), 1000)}
        if query:
            qp["search"] = query
        if params.get("skip"):
            qp["skip"] = params["skip"]

        try:
            response = await self._rate_limited_request("GET", endpoint_path, params=qp)
            data = response.json()
            results = data.get("results", [])
            meta = data.get("meta", {})

            return ConnectorResult(
                success=True,
                data=results,
                metadata={
                    "source": "OpenFDA",
                    "category": category,
                    "total_results": meta.get("results", {}).get("total", 0),
                    "returned": len(results),
                    "skip": meta.get("results", {}).get("skip", 0),
                },
            )
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            return ConnectorResult(success=False, error=f"FDA API error ({exc.response.status_code}): {body}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific record by its OpenFDA ID.

        Args:
            item_id: The record identifier used by OpenFDA.
        Keyword Args:
            category: Endpoint category (default 'drug_label').
        """
        category = params.pop("category", "drug_label")
        endpoint_path = _OPENFDA_ENDPOINTS.get(category)
        if not endpoint_path:
            return ConnectorResult(success=False, error=f"Unknown category '{category}'")

        try:
            response = await self._rate_limited_request(
                "GET", endpoint_path, params={"search": f"id:{item_id}", "limit": 1}
            )
            data = response.json()
            results = data.get("results", [])
            if not results:
                return ConnectorResult(success=False, error="Record not found")
            return ConnectorResult(
                success=True,
                data=results[0],
                metadata={"source": "OpenFDA", "category": category},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"FDA API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint in _OPENFDA_ENDPOINTS:
            params["category"] = endpoint
            query = params.pop("search", params.pop("query", ""))
            return await self.search(query=query, **params)
        if endpoint == "search":
            query = params.pop("query", params.pop("search", ""))
            return await self.search(query=query, **params)
        if endpoint == "get":
            item_id = params.pop("id", "")
            return await self.get(item_id, **params)
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
                    "description": "Search OpenFDA drug/device/food data",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "category", "type": "string", "description": f"One of: {', '.join(list(_OPENFDA_ENDPOINTS)[:8])}..."},
                        {"name": "limit", "type": "integer", "description": "Max results (1-1000)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a specific record by ID",
                    "parameters": [
                        {"name": "item_id", "type": "string", "required": True, "description": "OpenFDA record ID"},
                        {"name": "category", "type": "string", "description": "Endpoint category"},
                    ],
                },
            ],
        }


def register_connector():
    """Register the OpenFDA connector."""
    import os
    return OpenFDAConnector, {
        "base_url": "https://api.fda.gov/",
        "api_key": os.getenv("FDA_API_KEY", ""),
    }