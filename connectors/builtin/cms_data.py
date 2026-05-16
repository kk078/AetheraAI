"""
CMS Public Datasets Connector for Aethera
Fetches Medicare provider, payment, and quality data from data.cms.gov.
API: https://data.cms.gov/provider-data/api/1/datastore/query/
No authentication required.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult

# Common CMS dataset identifiers
_CMS_DATASETS = {
    "provider_util_payment": "5d76-i4yi",
    "physician_compare": "4j6v-f8cf",
    "hospital_general": "xubh-q36u",
    "hospital_readmissions": "9n3s-kdb3",
    "hospital_hcahps": "dk4c-n4ze",
    "nursing_home_compare": "4pq5-n9py",
    "home_health_compare": "6jpm-cxw9",
    "hospice_compare": "4cnf-2m5a",
    "durable_medical_equipment": "uq7h-jdh3",
    "medicare_advantage_enrollment": "wk4m-rrsa",
}


class CMSDataConnector(AetheraConnector):
    """CMS public datasets API connector for Medicare data."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get(
            "base_url",
            "https://data.cms.gov/provider-data/api/1/datastore/query/",
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="cms_data",
            version="1.0.0",
            description="CMS Public Datasets - Medicare provider, payment, and quality data",
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
        """Search CMS datasets.

        Keyword Args:
            dataset: Dataset identifier or alias (e.g. 'provider_util_payment').
            filters: JSON-encoded filter expressions for the CMS API.
            limit: Max results (1-1000, default 50).
            offset: Result offset for pagination.
        """
        dataset_id = params.get("dataset", "provider_util_payment")
        # Resolve friendly name to UUID
        resolved_id = _CMS_DATASETS.get(dataset_id, dataset_id)

        limit = min(int(params.get("limit", 50)), 1000)
        offset = int(params.get("offset", 0))

        url = f"{resolved_id}/0"

        qp: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if query:
            qp["search"] = query
        if params.get("filters"):
            qp["filters"] = params["filters"]

        try:
            response = await self._rate_limited_request("GET", url, params=qp)
            data = response.json()
            results = data if isinstance(data, list) else data.get("results", data.get("data", []))
            return ConnectorResult(
                success=True,
                data=results,
                metadata={
                    "source": "CMS Data",
                    "dataset": dataset_id,
                    "offset": offset,
                    "limit": limit,
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"CMS Data API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Get a specific record from a CMS dataset.

        Args:
            item_id: Row ID within the dataset.
        Keyword Args:
            dataset: Dataset identifier or alias.
        """
        dataset_id = params.get("dataset", "provider_util_payment")
        resolved_id = _CMS_DATASETS.get(dataset_id, dataset_id)

        try:
            response = await self._rate_limited_request("GET", f"{resolved_id}/0/{item_id}")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=data,
                metadata={"source": "CMS Data", "dataset": dataset_id, "row": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Record not found")
            return ConnectorResult(success=False, error=f"CMS Data API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def datasets(self) -> ConnectorResult:
        """List available CMS dataset identifiers."""
        return ConnectorResult(
            success=True,
            data=[
                {"alias": k, "id": v} for k, v in _CMS_DATASETS.items()
            ],
            metadata={"source": "CMS Data", "count": len(_CMS_DATASETS)},
        )

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("id", ""), **params)
        if endpoint == "datasets":
            return await self.datasets()
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
                    "description": "Search CMS datasets",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "dataset", "type": "string", "description": f"One of: {', '.join(list(_CMS_DATASETS)[:6])}..."},
                        {"name": "limit", "type": "integer", "description": "Max results (1-1000)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a specific record from a dataset",
                    "parameters": [
                        {"name": "id", "type": "string", "required": True, "description": "Row ID"},
                        {"name": "dataset", "type": "string", "description": "Dataset alias"},
                    ],
                },
                {
                    "name": "datasets",
                    "description": "List available CMS datasets",
                    "parameters": [],
                },
            ],
        }


def register_connector():
    return CMSDataConnector, {
        "base_url": "https://data.cms.gov/provider-data/api/1/datastore/query/"
    }