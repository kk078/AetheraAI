"""
CMS Coverage Database Connector for Aethera
Fetches LCD/NCD coverage determinations from the Medicare Coverage Database.
https://www.cms.gov/medicare-coverage-database
Uses the public search endpoint; no authentication required.
"""
import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class CMSCoverageConnector(AetheraConnector):
    """CMS Medicare Coverage Database connector for LCD/NCD lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get(
            "base_url",
            "https://www.cms.gov/medicare-coverage-database",
        )
        self.search_url = "https://www.cms.gov/medicare-coverage-database/search"
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="cms_coverage",
            version="1.0.0",
            description="CMS Medicare Coverage Database - LCD/NCD coverage determinations",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=30,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json", "User-Agent": "AetheraAI/1.0"},
            follow_redirects=True,
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

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search Medicare coverage documents (LCDs, NCDs).

        Keyword Args:
            doc_type: 'lcd', 'ncd', or 'all' (default 'all').
            status: 'final', 'proposed', 'retired', or 'all' (default 'active').
            state: Two-letter state for LCDs.
            hcpcs: HCPCS/CPT code to search.
            limit: Max results (default 25).
        """
        doc_type = params.get("doc_type", "all")
        status = params.get("status", "active")
        limit = min(int(params.get("limit", 25)), 100)

        query_params: Dict[str, Any] = {
            "keyword": query,
            "docType": doc_type,
            "status": status,
            "limit": limit,
        }
        if params.get("state"):
            query_params["state"] = params["state"]
        if params.get("hcpcs"):
            query_params["hcpcsCode"] = params["hcpcs"]

        try:
            response = await self._rate_limited_request(
                "GET",
                f"{self.base_url}/api/search",
                params=query_params,
            )
            data = response.json()
            results = data.get("results", data.get("documents", []))
            if isinstance(results, list):
                normalized = [self._normalize_document(d) for d in results]
            else:
                normalized = [self._normalize_document(results)] if results else []

            return ConnectorResult(
                success=True,
                data=normalized,
                metadata={
                    "source": "CMS Coverage Database",
                    "doc_type": doc_type,
                    "total": data.get("total", len(normalized)),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"CMS Coverage API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific coverage document by its ID.

        Args:
            item_id: Coverage document ID (e.g. NCD ID or LCD ID).
        """
        try:
            response = await self._rate_limited_request(
                "GET",
                f"{self.base_url}/api/document/{item_id}",
            )
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_document(data),
                metadata={"source": "CMS Coverage Database", "document_id": item_id},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Document not found: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            query = params.pop("query", "")
            return await self.search(query=query, **params)
        if endpoint == "get":
            doc_id = params.pop("document_id", params.pop("id", ""))
            return await self.get(doc_id, **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_document(doc: Dict) -> Dict:
        return {
            "id": doc.get("id", doc.get("documentId", "")),
            "title": doc.get("title", doc.get("name", "")),
            "type": doc.get("type", doc.get("documentType", "")),
            "status": doc.get("status", ""),
            "effective_date": doc.get("effectiveDate", doc.get("effective", "")),
            "retirement_date": doc.get("retirementDate", ""),
            "summary": doc.get("summary", doc.get("description", "")),
            "state": doc.get("state", ""),
            "contractor": doc.get("contractorName", doc.get("contractor", "")),
            "hcpcs_codes": doc.get("hcpcsCodes", []),
            "icd_codes": doc.get("icdCodes", []),
            "url": doc.get("url", ""),
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
                    "description": "Search LCD/NCD coverage documents",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search keyword"},
                        {"name": "doc_type", "type": "string", "description": "lcd, ncd, or all"},
                        {"name": "state", "type": "string", "description": "Two-letter state"},
                        {"name": "hcpcs", "type": "string", "description": "HCPCS/CPT code"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a specific coverage document by ID",
                    "parameters": [
                        {"name": "document_id", "type": "string", "required": True, "description": "Document ID"},
                    ],
                },
            ],
        }


def register_connector():
    return CMSCoverageConnector, {"base_url": "https://www.cms.gov/medicare-coverage-database"}