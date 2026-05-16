"""
SearXNG Local Instance Connector for Aethera
Connects to a self-hosted SearXNG meta-search engine instance.
API: Typically http://localhost:8080/ (configurable).
No API key required for local instances.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class SearXNGConnector(AetheraConnector):
    """SearXNG meta-search engine connector for local instance queries."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:8080/")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="searxng",
            version="1.0.0",
            description="SearXNG - Self-hosted meta-search engine",
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
        # Verify the instance is reachable
        try:
            resp = await self._client.get("healthcheck")
            if resp.status_code not in (200, 404):
                # Some instances don't have healthcheck; that's fine
                pass
        except Exception:
            pass
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
        """Search via SearXNG.

        Keyword Args:
            categories: Comma-separated categories (general, images, news, science, it, files, social media).
            engines: Comma-separated engine names (google, bing, duckduckgo, wikipedia, etc.).
            language: Language code (en, de, fr, etc.).
            time_range: 'day', 'week', 'month', 'year'.
            format: Response format (default 'json').
            pageno: Page number (1-based).
            limit: Max results hint (SearXNG controls actual count).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        qp: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": params.get("pageno", 1),
        }
        if params.get("categories"):
            qp["categories"] = params["categories"]
        if params.get("engines"):
            qp["engines"] = params["engines"]
        if params.get("language"):
            qp["language"] = params["language"]
        if params.get("time_range"):
            qp["time_range"] = params["time_range"]

        try:
            response = await self._rate_limited_request("GET", "search", params=qp)
            data = response.json()
            results = data.get("results", [])
            normalized = [self._normalize_result(r) for r in results]

            return ConnectorResult(
                success=True,
                data=normalized,
                metadata={
                    "source": "SearXNG",
                    "query": query,
                    "number_of_results": data.get("number_of_results", len(normalized)),
                    "categories": data.get("categories", []),
                    "engines": list({e.get("engine", "") for r in results for e in r.get("engines", [])}),
                    "suggestions": data.get("suggestions", []),
                    "infoboxes": data.get("infoboxes", []),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"SearXNG API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """SearXNG doesn't support direct item retrieval; redirects to search.

        Args:
            item_id: Treated as a search query.
        """
        return await self.search(query=item_id, **params)

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint in ("search", "get"):
            query = params.pop("query", params.pop("q", ""))
            return await self.search(query=query, **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_result(result: Dict) -> Dict:
        return {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "description": result.get("content", ""),
            "engine": result.get("engine", ""),
            "engines": [e.get("engine", e) if isinstance(e, dict) else e for e in result.get("engines", [])],
            "score": result.get("score", 0.0),
            "category": result.get("category", ""),
            "published_date": result.get("publishedDate", ""),
            "thumbnail": result.get("thumbnail", ""),
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
                    "description": "Search via SearXNG meta-search engine",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "categories", "type": "string", "description": "general, news, science, it, images"},
                        {"name": "engines", "type": "string", "description": "google, bing, duckduckgo, wikipedia"},
                        {"name": "language", "type": "string", "description": "Language code (en, de, fr)"},
                        {"name": "time_range", "type": "string", "description": "day, week, month, year"},
                    ],
                },
            ],
        }


def register_connector():
    return SearXNGConnector, {"base_url": "http://localhost:8080/"}