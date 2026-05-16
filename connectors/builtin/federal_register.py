"""
Federal Register Connector for Aethera
Fetches CMS/HHS rules and regulations from the Federal Register API.
API: https://www.federalregister.gov/api/v1/
No authentication required. Rate limit: generous for public use.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class FederalRegisterConnector(AetheraConnector):
    """Federal Register API connector for CMS/HHS rules and regulations."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://www.federalregister.gov/api/v1/")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="federal_register",
            version="1.0.0",
            description="Federal Register - CMS/HHS rules, regulations, and notices",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json", "User-Agent": "AetheraAI/1.0"},
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
        """Search Federal Register documents.

        Keyword Args:
            agencies: Comma-separated agency slugs (default 'centers-for-medicare-medicaid-services,health-and-human-services-department').
            type: Document type: 'RULE', 'PROPOSED_RULE', 'NOTICE', 'PRESDOCU' (presidential).
            conditions: Search conditions string (Lucene syntax).
            publication_date: Date range 'YYYY-MM-DD..YYYY-MM-DD'.
            effective_date: Effective date range.
            limit: Max results (1-100, default 20).
            order: Sort order 'newest', 'oldest', 'relevance' (default 'relevance').
            page: Page number (1-based).
        """
        qp: Dict[str, Any] = {
            "per_page": min(int(params.get("limit", 20)), 100),
            "order": params.get("order", "relevance"),
            "page": params.get("page", 1),
        }

        if query:
            qp["conditions[term]"] = query

        # Default to CMS and HHS agencies
        agencies = params.get(
            "agencies",
            "centers-for-medicare-medicaid-services,health-and-human-services-department",
        )
        if agencies:
            for i, agency in enumerate(agencies.split(",")):
                qp[f"conditions[agencies][][{i}]"] = agency.strip()

        if params.get("type"):
            for i, doc_type in enumerate(params["type"].split(",")):
                qp[f"conditions[type][][{i}]"] = doc_type.strip()

        if params.get("publication_date"):
            qp["conditions[publication_date]"] = params["publication_date"]

        if params.get("effective_date"):
            qp["conditions[effective_date]"] = params["effective_date"]

        try:
            response = await self._rate_limited_request("GET", "documents.json", params=qp)
            data = response.json()
            documents = data.get("results", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_document(d) for d in documents],
                metadata={
                    "source": "Federal Register",
                    "total": data.get("count", 0),
                    "page": data.get("current_page", 1),
                    "total_pages": data.get("total_pages", 1),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Federal Register API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific Federal Register document by document number.

        Args:
            item_id: Document number (e.g. '2024-12345').
        """
        if not item_id:
            return ConnectorResult(success=False, error="Document number required")

        try:
            response = await self._rate_limited_request("GET", f"documents/{item_id}.json")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_document(data),
                metadata={"source": "Federal Register", "document_number": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Document not found")
            return ConnectorResult(success=False, error=f"Federal Register API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def agencies(self) -> ConnectorResult:
        """List available agencies."""
        try:
            response = await self._rate_limited_request("GET", "agencies.json")
            data = response.json()
            results = data.get("results", data if isinstance(data, list) else [])
            return ConnectorResult(
                success=True,
                data=[
                    {"slug": a.get("slug", ""), "name": a.get("name", ""), "short_name": a.get("short_name", "")}
                    for a in results
                ],
                metadata={"source": "Federal Register"},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("document_number", params.pop("id", "")), **params)
        if endpoint == "agencies":
            return await self.agencies()
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_document(doc: Dict) -> Dict:
        return {
            "document_number": doc.get("document_number", ""),
            "title": doc.get("title", ""),
            "type": doc.get("type", ""),
            "abstract": doc.get("abstract", ""),
            "agencies": [a.get("name", a) if isinstance(a, dict) else a for a in doc.get("agencies", [])],
            "publication_date": doc.get("publication_date", ""),
            "effective_date": doc.get("effective_date", ""),
            "comments_close_date": doc.get("comments_close_on", doc.get("comments_close_date", "")),
            "citation": doc.get("citation", ""),
            "html_url": doc.get("html_url", ""),
            "pdf_url": doc.get("pdf_url", ""),
            "full_text_url": doc.get("full_text_url", ""),
            "start_page": doc.get("start_page", ""),
            "end_page": doc.get("end_page", ""),
            "docket_id": doc.get("docket_id", ""),
            "regulation_id_numbers": doc.get("regulation_id_numbers", []),
            "significant": doc.get("significant", False),
            "ror": doc.get("ror", ""),
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
                    "description": "Search Federal Register documents",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search terms"},
                        {"name": "agencies", "type": "string", "description": "Agency slugs (comma-separated)"},
                        {"name": "type", "type": "string", "description": "RULE, PROPOSED_RULE, NOTICE"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a specific Federal Register document",
                    "parameters": [
                        {"name": "document_number", "type": "string", "required": True, "description": "Document number"},
                    ],
                },
                {
                    "name": "agencies",
                    "description": "List available Federal Register agencies",
                    "parameters": [],
                },
            ],
        }


def register_connector():
    return FederalRegisterConnector, {"base_url": "https://www.federalregister.gov/api/v1/"}