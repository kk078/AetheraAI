"""
UMLS Metathesaurus Connector for Aethera
Fetches unified medical language system data from the UTS API.
API: https://uts-ws.nlm.nih.gov/rest/
Requires a free UMLS license (API key).
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class UMLSConnector(AetheraConnector):
    """UMLS Metathesaurus connector for cross-vocabulary medical term lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://uts-ws.nlm.nih.gov/rest/")
        self.api_key = config.get("api_key", "")
        self.version = config.get("version", "current")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="umls",
            version="1.0.0",
            description="UMLS Metathesaurus - Unified medical language system cross-vocabulary lookup",
            base_url=self.base_url,
            auth_type="api_key",
            rate_limit=20,
            timeout=30,
        )

    async def initialize(self) -> bool:
        if not self.api_key:
            raise ValueError("UMLS API key required (free UMLS license at https://uts.nlm.nih.gov/)")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json"},
            params={"apiKey": self.api_key},
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
        """Search UMLS concepts across vocabularies.

        Keyword Args:
            sabs: Comma-separated source vocabulary abbreviations (e.g. 'SNOMEDCT_US,ICD10CM').
            search_type: 'words', 'exact', 'leftTruncation', 'rightTruncation', 'approximate' (default 'words').
            limit: Max results (1-100, default 20).
            page: Page number (1-based).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        qp: Dict[str, Any] = {
            "string": query,
            "searchType": params.get("search_type", "words"),
            "pageSize": min(int(params.get("limit", 20)), 100),
            "pageNumber": params.get("page", 1),
        }
        if params.get("sabs"):
            qp["sabs"] = params["sabs"]

        try:
            response = await self._rate_limited_request(
                "GET", f"search/{self.version}", params=qp
            )
            data = response.json()
            result = data.get("result", {})
            results_list = result.get("results", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_search_result(r) for r in results_list],
                metadata={
                    "source": "UMLS",
                    "total": result.get("totalCount", len(results_list)),
                    "page": result.get("pageNumber", 1),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"UMLS API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific UMLS concept by CUI.

        Args:
            item_id: UMLS Concept Unique Identifier (CUI), e.g. 'C0011847'.
        """
        if not item_id:
            return ConnectorResult(success=False, error="CUI required")

        try:
            response = await self._rate_limited_request(
                "GET", f"content/{self.version}/CUI/{item_id}"
            )
            data = response.json()
            result = data.get("result", data)
            return ConnectorResult(
                success=True,
                data=self._normalize_concept(result),
                metadata={"source": "UMLS", "cui": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="CUI not found")
            return ConnectorResult(success=False, error=f"UMLS API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def definitions(self, cui: str) -> ConnectorResult:
        """Get definitions for a CUI."""
        if not cui:
            return ConnectorResult(success=False, error="CUI required")

        try:
            response = await self._rate_limited_request(
                "GET", f"content/{self.version}/CUI/{cui}/definitions"
            )
            data = response.json()
            results = data.get("result", [])
            defs = [
                {
                    "value": d.get("value", ""),
                    "source": d.get("rootSource", d.get("source", "")),
                    "language": d.get("language", "ENG"),
                }
                for d in (results if isinstance(results, list) else [])
            ]
            return ConnectorResult(
                success=True,
                data={"cui": cui, "definitions": defs},
                metadata={"source": "UMLS", "count": len(defs)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def atoms(self, cui: str, **params) -> ConnectorResult:
        """Get atoms (source vocabulary entries) for a CUI.

        Keyword Args:
            sabs: Source vocabulary filter.
            limit: Max results (default 50).
        """
        if not cui:
            return ConnectorResult(success=False, error="CUI required")

        qp: Dict[str, Any] = {"pageSize": min(int(params.get("limit", 50)), 200)}
        if params.get("sabs"):
            qp["sabs"] = params["sabs"]

        try:
            response = await self._rate_limited_request(
                "GET", f"content/{self.version}/CUI/{cui}/atoms", params=qp
            )
            data = response.json()
            result = data.get("result", [])
            atoms = [
                {
                    "aui": a.get("aui", ""),
                    "name": a.get("name", ""),
                    "source": a.get("rootSource", a.get("source", "")),
                    "term_type": a.get("termType", ""),
                    "code": a.get("code", ""),
                }
                for a in (result if isinstance(result, list) else result.get("results", []))
            ]
            return ConnectorResult(
                success=True,
                data={"cui": cui, "atoms": atoms},
                metadata={"source": "UMLS", "count": len(atoms)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def relations(self, cui: str, **params) -> ConnectorResult:
        """Get relationships for a CUI.

        Keyword Args:
            limit: Max results (default 50).
        """
        if not cui:
            return ConnectorResult(success=False, error="CUI required")

        qp: Dict[str, Any] = {"pageSize": min(int(params.get("limit", 50)), 200)}

        try:
            response = await self._rate_limited_request(
                "GET", f"content/{self.version}/CUI/{cui}/relations", params=qp
            )
            data = response.json()
            result = data.get("result", [])
            rels = [
                {
                    "relation": r.get("relationLabel", r.get("additionalRelationLabel", "")),
                    "target_cui": r.get("relatedId", ""),
                    "source": r.get("rootSource", ""),
                }
                for r in (result if isinstance(result, list) else result.get("results", []))
            ]
            return ConnectorResult(
                success=True,
                data={"cui": cui, "relations": rels},
                metadata={"source": "UMLS", "count": len(rels)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("cui", params.pop("id", "")), **params)
        if endpoint == "definitions":
            return await self.definitions(params.pop("cui", ""))
        if endpoint == "atoms":
            return await self.atoms(params.pop("cui", ""), **params)
        if endpoint == "relations":
            return await self.relations(params.pop("cui", ""), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_search_result(result: Dict) -> Dict:
        return {
            "cui": result.get("ui", result.get("cui", "")),
            "name": result.get("name", ""),
            "source_vocabularies": result.get("rootSource", result.get("sabs", "")),
            "semantic_types": result.get("semanticType", result.get("stems", [])),
        }

    @staticmethod
    def _normalize_concept(result: Dict) -> Dict:
        return {
            "cui": result.get("ui", result.get("cui", "")),
            "name": result.get("name", ""),
            "semantic_types": [
                st.get("name", st) if isinstance(st, dict) else st
                for st in result.get("semanticTypes", result.get("semanticType", []))
            ],
            "definitions": result.get("definitions", []),
            "atoms_count": result.get("atomCount", 0),
            "status": result.get("status", "R"),
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
                    "description": "Search UMLS concepts across vocabularies",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search string"},
                        {"name": "sabs", "type": "string", "description": "Source vocabularies (e.g. SNOMEDCT_US,ICD10CM)"},
                        {"name": "search_type", "type": "string", "description": "words, exact, approximate"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get a concept by CUI",
                    "parameters": [
                        {"name": "cui", "type": "string", "required": True, "description": "UMLS CUI (e.g. C0011847)"},
                    ],
                },
                {
                    "name": "atoms",
                    "description": "Get source vocabulary atoms for a CUI",
                    "parameters": [
                        {"name": "cui", "type": "string", "required": True},
                    ],
                },
                {
                    "name": "relations",
                    "description": "Get relationships for a CUI",
                    "parameters": [
                        {"name": "cui", "type": "string", "required": True},
                    ],
                },
            ],
        }


def register_connector():
    import os
    return UMLSConnector, {
        "base_url": "https://uts-ws.nlm.nih.gov/rest/",
        "api_key": os.getenv("UMLS_API_KEY", ""),
    }