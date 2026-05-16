"""
RxNorm Drug Terminology Connector for Aethera
Fetches drug data from the NLM RxNorm API.
API: https://rxnav.nlm.nih.gov/REST/
No authentication required. Rate limit: ~60 req/min.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class RxNormConnector(AetheraConnector):
    """RxNorm API connector for normalized drug terminology."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://rxnav.nlm.nih.gov/REST/")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="rxnorm",
            version="1.0.0",
            description="RxNorm - Normalized drug terminology from NLM",
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
        """Search for drugs by name.

        Keyword Args:
            limit: Max suggestions (default 20).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        limit = min(int(params.get("limit", 20)), 50)

        try:
            response = await self._rate_limited_request(
                "GET", "spellsuggestions.json", params={"name": query}
            )
            data = response.json()
            suggestions = (
                data.get("suggestionGroup", [{}])[0]
                .get("suggestionList", {})
                .get("suggestion", [])
            )
            return ConnectorResult(
                success=True,
                data=[
                    {"name": s.get("name", ""), "rxcui": s.get("rxcui", "")}
                    for s in suggestions[:limit]
                ],
                metadata={"source": "RxNorm", "query": query},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"RxNorm API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Get drug properties by RxCUI.

        Args:
            item_id: RxCUI identifier.
        """
        if not item_id:
            return ConnectorResult(success=False, error="RxCUI required")

        try:
            response = await self._rate_limited_request(
                "GET", f"rxcui/{item_id}/properties.json"
            )
            data = response.json()
            props = data.get("properties", {})

            return ConnectorResult(
                success=True,
                data={
                    "rxcui": props.get("rxcui", ""),
                    "name": props.get("name", ""),
                    "tty": props.get("tty", ""),
                    "vocab": props.get("vocab", "RXNORM"),
                    "suppress": props.get("suppress", "N"),
                },
                metadata={"source": "RxNorm"},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"RxNorm API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def related(self, rxcui: str, tty: str = "GBPC") -> ConnectorResult:
        """Get related drugs (generic/brand equivalents) by RxCUI.

        Args:
            rxcui: RxCUI identifier.
            tty: Term type filter (default 'GBPC' for generic/brand pack).
        """
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        try:
            response = await self._rate_limited_request(
                "GET", f"rxcui/{rxcui}/related.json", params={"tty": tty}
            )
            data = response.json()
            concepts = data.get("relatedGroup", {}).get("conceptGroup", [])

            related: List[Dict] = []
            for group in concepts:
                for concept in group.get("conceptProperties", []):
                    related.append({
                        "rxcui": concept.get("rxcui", ""),
                        "name": concept.get("name", ""),
                        "tty": concept.get("tty", ""),
                    })
            return ConnectorResult(
                success=True,
                data={"rxcui": rxcui, "related": related},
                metadata={"source": "RxNorm", "count": len(related)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def ndcs(self, rxcui: str) -> ConnectorResult:
        """Get NDC codes for a drug by RxCUI."""
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        try:
            response = await self._rate_limited_request(
                "GET", f"rxcui/{rxcui}/ndcs.json"
            )
            data = response.json()
            ndc_groups = data.get("idGroup", {}).get("ndcGroup", [])
            ndcs: List[str] = []
            for group in ndc_groups:
                for ndc in group.get("ndcList", []):
                    ndcs.append(ndc.get("ndc", ""))
            return ConnectorResult(
                success=True,
                data={"rxcui": rxcui, "ndcs": ndcs},
                metadata={"source": "RxNorm", "count": len(ndcs)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def interaction(self, rxcui1: str, rxcui2: str) -> ConnectorResult:
        """Check drug-drug interactions between two RxCUIs."""
        if not rxcui1 or not rxcui2:
            return ConnectorResult(success=False, error="Both RxCUIs required")

        try:
            response = await self._rate_limited_request(
                "GET",
                "interaction.json",
                params={"rxcui1": rxcui1, "rxcui2": rxcui2},
            )
            data = response.json()
            interactions = data.get("interactionType", [])
            results = [
                {
                    "type": i.get("description", ""),
                    "severity": i.get("severity", "unknown"),
                    "description": i.get("description", ""),
                }
                for i in interactions
            ]
            return ConnectorResult(
                success=True,
                data={"rxcui1": rxcui1, "rxcui2": rxcui2, "interactions": results},
                metadata={"source": "RxNorm", "count": len(results)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", params.pop("drug_name", "")), **params)
        if endpoint in ("rxcui", "properties"):
            rxcui = params.pop("rxcui", params.pop("id", ""))
            return await self.get(rxcui, **params)
        if endpoint == "related":
            return await self.related(params.pop("rxcui", ""), params.pop("tty", "GBPC"))
        if endpoint == "ndc":
            return await self.ndcs(params.pop("rxcui", ""))
        if endpoint == "interaction":
            return await self.interaction(params.pop("rxcui1", ""), params.pop("rxcui2", ""))
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
                    "description": "Search drugs by name",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Drug name search"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get drug properties by RxCUI",
                    "parameters": [
                        {"name": "rxcui", "type": "string", "required": True, "description": "RxCUI"},
                    ],
                },
                {
                    "name": "related",
                    "description": "Get related drugs (generic/brand)",
                    "parameters": [
                        {"name": "rxcui", "type": "string", "required": True, "description": "RxCUI"},
                    ],
                },
                {
                    "name": "interaction",
                    "description": "Check drug-drug interactions",
                    "parameters": [
                        {"name": "rxcui1", "type": "string", "required": True},
                        {"name": "rxcui2", "type": "string", "required": True},
                    ],
                },
            ],
        }


def register_connector():
    return RxNormConnector, {"base_url": "https://rxnav.nlm.nih.gov/REST/"}