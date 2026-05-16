"""
Wikipedia API Connector for Aethera
Fetches Wikipedia article content, summaries, and search results.
API: https://en.wikipedia.org/w/api.php
No authentication required. Rate limit: generous for read-only access.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class WikipediaConnector(AetheraConnector):
    """Wikipedia MediaWiki API connector for article lookup and search."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://en.wikipedia.org/w/api.php")
        self.language = config.get("language", "en")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="wikipedia",
            version="1.0.0",
            description="Wikipedia - Encyclopedia article search and retrieval",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=200,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
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

    def _api_url(self) -> str:
        if self.language != "en":
            return f"https://{self.language}.wikipedia.org/w/api.php"
        return self.base_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search Wikipedia articles.

        Keyword Args:
            limit: Max results (1-50, default 10).
            suggestion: Include search suggestions (default True).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        limit = min(int(params.get("limit", 10)), 50)

        qp: Dict[str, Any] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        if params.get("suggestion", True):
            qp["srinfo"] = "suggestion"

        try:
            response = await self._rate_limited_request("GET", self._api_url(), params=qp)
            data = response.json()
            search_results = data.get("query", {}).get("search", [])

            return ConnectorResult(
                success=True,
                data=[self._normalize_search_result(r) for r in search_results],
                metadata={
                    "source": "Wikipedia",
                    "total_hits": data.get("query", {}).get("searchinfo", {}).get("totalhits", 0),
                    "suggestion": data.get("query", {}).get("searchinfo", {}).get("suggestion", ""),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Wikipedia API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a Wikipedia article by title.

        Args:
            item_id: Article title (e.g. 'Python (programming language)').
        Keyword Args:
            extract: Return plain text extract (default True).
            intro_only: Only the intro/lead section (default True).
            html: Return HTML instead of text (default False).
        """
        if not item_id:
            return ConnectorResult(success=False, error="Article title required")

        extract = params.get("extract", True)
        intro_only = params.get("intro_only", True)
        html = params.get("html", False)

        qp: Dict[str, Any] = {
            "action": "query",
            "titles": item_id,
            "format": "json",
            "redirects": 1,
        }

        if html:
            qp["prop"] = "revisions"
            qp["rvprop"] = "content"
            qp["rvparse"] = 1
        elif extract:
            qp["prop"] = "extracts"
            qp["exintro"] = 1 if intro_only else 0
            qp["explaintext"] = 1
        else:
            qp["prop"] = "revisions"
            qp["rvprop"] = "content"

        try:
            response = await self._rate_limited_request("GET", self._api_url(), params=qp)
            data = response.json()
            pages = data.get("query", {}).get("pages", {})

            # Handle redirects
            redirects = data.get("query", {}).get("redirects", [])
            redirect_to = redirects[0].get("to", item_id) if redirects else item_id

            for page_id, page in pages.items():
                if page_id == "-1" or "missing" in page:
                    return ConnectorResult(success=False, error=f"Article '{item_id}' not found")

                return ConnectorResult(
                    success=True,
                    data={
                        "title": page.get("title", item_id),
                        "page_id": page.get("pageid", int(page_id)),
                        "extract": page.get("extract", ""),
                        "content": page.get("revisions", [{}])[0].get("*", "") if not extract else "",
                        "redirect_to": redirect_to if redirect_to != item_id else None,
                        "full_url": page.get("fullurl", ""),
                    },
                    metadata={"source": "Wikipedia", "title": item_id},
                )

            return ConnectorResult(success=False, error=f"Article '{item_id}' not found")
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Wikipedia API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def summary(self, title: str) -> ConnectorResult:
        """Get a short summary of a Wikipedia article using the REST API.

        Args:
            title: Article title.
        """
        if not title:
            return ConnectorResult(success=False, error="Article title required")

        rest_url = f"https://{self.language}.wikipedia.org/api/rest_v1/page/summary/{title}"
        try:
            response = await self._rate_limited_request("GET", rest_url)
            data = response.json()
            return ConnectorResult(
                success=True,
                data={
                    "title": data.get("title", ""),
                    "extract": data.get("extract", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source", ""),
                    "description": data.get("description", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                },
                metadata={"source": "Wikipedia REST", "title": title},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Article not found")
            return ConnectorResult(success=False, error=f"Wikipedia REST API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("title", params.pop("id", "")), **params)
        if endpoint == "summary":
            return await self.summary(params.pop("title", ""))
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_search_result(result: Dict) -> Dict:
        return {
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "page_id": result.get("pageid", 0),
            "word_count": result.get("wordcount", 0),
            "timestamp": result.get("timestamp", ""),
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
                    "description": "Search Wikipedia articles",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-50)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a full article by title",
                    "parameters": [
                        {"name": "title", "type": "string", "required": True, "description": "Article title"},
                    ],
                },
                {
                    "name": "summary",
                    "description": "Get a short article summary",
                    "parameters": [
                        {"name": "title", "type": "string", "required": True, "description": "Article title"},
                    ],
                },
            ],
        }


def register_connector():
    return WikipediaConnector, {"base_url": "https://en.wikipedia.org/w/api.php", "language": "en"}