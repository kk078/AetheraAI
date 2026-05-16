"""
ArXiv Paper Search Connector for Aethera
Fetches academic preprints from ArXiv via its search/export API.
API: http://export.arxiv.org/api/
No authentication required. Rate limit: be respectful (1 req/3sec recommended).
"""
import asyncio
import re
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArXivConnector(AetheraConnector):
    """ArXiv API connector for academic preprint search and retrieval."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://export.arxiv.org/api/")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="arxiv",
            version="1.0.0",
            description="ArXiv - Academic preprint search and retrieval",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=20,  # Conservative: ~1 req/3sec
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/atom+xml, application/json", "User-Agent": "AetheraAI/1.0"},
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
        """Search ArXiv papers.

        Keyword Args:
            search_field: 'all', 'ti' (title), 'au' (author), 'abs' (abstract),
                          'cat' (category), 'jr' (journal ref) (default 'all').
            sort_by: 'relevance', 'lastUpdatedDate', 'submittedDate' (default 'relevance').
            sort_order: 'ascending', 'descending' (default 'descending').
            start: Result offset (0-based).
            limit: Max results (1-100, default 10).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        search_field = params.get("search_field", "all")
        sort_by = params.get("sort_by", "relevance")
        sort_order = params.get("sort_order", "descending")
        start = int(params.get("start", 0))
        limit = min(int(params.get("limit", 10)), 100)

        search_query = f"{search_field}:{query}" if search_field != "all" else query

        sort_map = {
            "relevance": "relevance",
            "lastUpdatedDate": "lastUpdatedDate",
            "submittedDate": "submittedDate",
        }

        qp: Dict[str, Any] = {
            "search_query": search_query,
            "start": start,
            "max_results": limit,
            "sortBy": sort_map.get(sort_by, "relevance"),
            "sortOrder": sort_order,
        }

        try:
            response = await self._rate_limited_request("GET", "query", params=qp)
            entries = self._parse_atom_feed(response.text)
            return ConnectorResult(
                success=True,
                data=entries,
                metadata={
                    "source": "ArXiv",
                    "query": search_query,
                    "start": start,
                    "returned": len(entries),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"ArXiv API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific ArXiv paper by its ID.

        Args:
            item_id: ArXiv ID (e.g. '2301.01234' or 'cs/0701001').
        """
        if not item_id:
            return ConnectorResult(success=False, error="ArXiv ID required")

        # Normalize: strip any URL prefix
        arxiv_id = item_id
        if "arxiv.org" in item_id:
            match = re.search(r"(\d{4}\.\d{4,5}|[a-z-]+/\d{7})", item_id)
            if match:
                arxiv_id = match.group(1)

        try:
            response = await self._rate_limited_request(
                "GET", "query", params={"id_list": arxiv_id, "max_results": 1}
            )
            entries = self._parse_atom_feed(response.text)
            if not entries:
                return ConnectorResult(success=False, error=f"ArXiv paper '{item_id}' not found")
            return ConnectorResult(
                success=True,
                data=entries[0],
                metadata={"source": "ArXiv", "id": arxiv_id},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("id", params.pop("arxiv_id", "")), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_atom_feed(xml_text: str) -> List[Dict]:
        """Parse ArXiv Atom feed XML into structured data."""
        results: List[Dict] = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return results

        for entry in root.findall(f"{_ATOM_NS}entry"):
            arxiv_id = ArXivConnector._get_text(entry, f"{_ATOM_NS}id", "")
            # Extract just the ArXiv ID from the full URL
            if arxiv_id and "arxiv.org/abs/" in arxiv_id:
                arxiv_id = arxiv_id.split("arxiv.org/abs/")[-1]

            title = ArXivConnector._get_text(entry, f"{_ATOM_NS}title", "").strip()
            title = re.sub(r"\s+", " ", title)

            summary = ArXivConnector._get_text(entry, f"{_ATOM_NS}summary", "").strip()
            summary = re.sub(r"\s+", " ", summary)

            authors = [
                ArXivConnector._get_text(a, f"{_ATOM_NS}name", "")
                for a in entry.findall(f"{_ATOM_NS}author")
            ]

            categories = [
                c.get("term", "")
                for c in entry.findall(f"{_ATOM_NS}category")
            ]

            published = ArXivConnector._get_text(entry, f"{_ATOM_NS}published", "")
            updated = ArXivConnector._get_text(entry, f"{_ATOM_NS}updated", "")

            doi = ""
            for link in entry.findall(f"{_ARXIV_NS}doi"):
                doi = link.text or ""
                break

            pdf_url = ""
            for link in entry.findall(f"{_ATOM_NS}link"):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break

            comment = ArXivConnector._get_text(entry, f"{_ARXIV_NS}comment", "")
            journal_ref = ArXivConnector._get_text(entry, f"{_ARXIV_NS}journal_ref", "")

            results.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": summary,
                "authors": authors,
                "categories": categories,
                "published": published,
                "updated": updated,
                "doi": doi,
                "pdf_url": pdf_url,
                "comment": comment,
                "journal_ref": journal_ref,
            })

        return results

    @staticmethod
    def _get_text(element: ElementTree.Element, path: str, default: str = "") -> str:
        child = element.find(path)
        if child is not None and child.text:
            return child.text
        return default

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
                    "description": "Search ArXiv papers",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "search_field", "type": "string", "description": "all, ti, au, abs, cat"},
                        {"name": "sort_by", "type": "string", "description": "relevance, lastUpdatedDate, submittedDate"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a specific ArXiv paper by ID",
                    "parameters": [
                        {"name": "id", "type": "string", "required": True, "description": "ArXiv ID (e.g. 2301.01234)"},
                    ],
                },
            ],
        }


def register_connector():
    return ArXivConnector, {"base_url": "http://export.arxiv.org/api/"}