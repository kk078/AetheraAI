"""
SNOMED CT Browser Connector for Aethera
Fetches clinical terminology from the SNOMED CT browser API (Snowstorm).
API: https://browser.ihtsdotools.org/snowstorm/snomed-ct/
No authentication required for public branch. UMLS license needed for full access.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class SNOMEDConnector(AetheraConnector):
    """SNOMED CT browser connector for clinical terminology lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get(
            "base_url",
            "https://browser.ihtsdotools.org/snowstorm/snomed-ct/",
        )
        self.branch = config.get("branch", "MAIN/2024-06-01")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="snomed",
            version="1.0.0",
            description="SNOMED CT - Clinical terminology browser (Snowstorm API)",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=30,
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
        """Search SNOMED CT concepts.

        Keyword Args:
            limit: Max results (1-100, default 20).
            active_only: Only active concepts (default True).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        qp: Dict[str, Any] = {
            "term": query,
            "activeFilter": params.get("active_only", True),
            "limit": min(int(params.get("limit", 20)), 100),
        }

        try:
            response = await self._rate_limited_request(
                "GET", f"browser/{self.branch}/concepts", params=qp
            )
            data = response.json()
            items = data.get("items", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_concept(c) for c in items],
                metadata={
                    "source": "SNOMED CT",
                    "total": data.get("total", len(items)),
                    "branch": self.branch,
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"SNOMED API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a SNOMED CT concept by its concept ID.

        Args:
            item_id: SNOMED concept ID (e.g. '73211009' for Diabetes mellitus).
        """
        if not item_id:
            return ConnectorResult(success=False, error="Concept ID required")

        try:
            response = await self._rate_limited_request(
                "GET", f"browser/{self.branch}/concepts/{item_id}"
            )
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_concept(data),
                metadata={"source": "SNOMED CT", "branch": self.branch},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Concept not found")
            return ConnectorResult(success=False, error=f"SNOMED API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def children(self, concept_id: str, **params) -> ConnectorResult:
        """Get direct children of a concept.

        Args:
            concept_id: SNOMED concept ID.
        Keyword Args:
            limit: Max results (default 50).
        """
        if not concept_id:
            return ConnectorResult(success=False, error="Concept ID required")

        qp: Dict[str, Any] = {"limit": min(int(params.get("limit", 50)), 100)}

        try:
            response = await self._rate_limited_request(
                "GET",
                f"browser/{self.branch}/concepts/{concept_id}/children",
                params=qp,
            )
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_concept(c) for c in items],
                metadata={"source": "SNOMED CT", "parent": concept_id, "branch": self.branch},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def descendants(self, concept_id: str, **params) -> ConnectorResult:
        """Get all descendants of a concept.

        Args:
            concept_id: SNOMED concept ID.
        Keyword Args:
            limit: Max results (default 100).
        """
        if not concept_id:
            return ConnectorResult(success=False, error="Concept ID required")

        qp: Dict[str, Any] = {"limit": min(int(params.get("limit", 100)), 500)}

        try:
            response = await self._rate_limited_request(
                "GET",
                f"browser/{self.branch}/concepts/{concept_id}/descendants",
                params=qp,
            )
            data = response.json()
            items = data.get("items", data if isinstance(data, list) else [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_concept(c) for c in items],
                metadata={"source": "SNOMED CT", "parent": concept_id, "branch": self.branch},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("concept_id", params.pop("id", "")), **params)
        if endpoint == "children":
            return await self.children(params.pop("concept_id", ""), **params)
        if endpoint == "descendants":
            return await self.descendants(params.pop("concept_id", ""), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_concept(concept: Dict) -> Dict:
        pt = concept.get("pt", concept.get("preferredTerm", ""))
        if isinstance(pt, dict):
            pt = pt.get("term", pt.get("name", ""))
        return {
            "concept_id": concept.get("conceptId", concept.get("id", "")),
            "name": pt or concept.get("fsn", {}).get("term", ""),
            "fully_specified_name": concept.get("fsn", {}).get("term", concept.get("fsn", "")),
            "active": concept.get("active", concept.get("isActive", True)),
            "definition_status": concept.get("definitionStatus", ""),
            "module": concept.get("moduleId", ""),
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
                    "description": "Search SNOMED CT concepts",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search term"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a concept by ID",
                    "parameters": [
                        {"name": "concept_id", "type": "string", "required": True, "description": "SNOMED concept ID"},
                    ],
                },
                {
                    "name": "children",
                    "description": "Get direct children of a concept",
                    "parameters": [
                        {"name": "concept_id", "type": "string", "required": True},
                    ],
                },
                {
                    "name": "descendants",
                    "description": "Get all descendants of a concept",
                    "parameters": [
                        {"name": "concept_id", "type": "string", "required": True},
                    ],
                },
            ],
        }


def register_connector():
    return SNOMEDConnector, {
        "base_url": "https://browser.ihtsdotools.org/snowstorm/snomed-ct/",
        "branch": "MAIN/2024-06-01",
    }