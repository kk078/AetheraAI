"""
LOINC Lab Code Connector for Aethera
Fetches laboratory observation codes from the LOINC FHIR API.
API: https://fhir.loinc.org/
Free LOINC license required for some operations.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class LOINCConnector(AetheraConnector):
    """LOINC FHIR API connector for laboratory observation code lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://fhir.loinc.org/")
        self.api_key = config.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="loinc",
            version="1.0.0",
            description="LOINC - Laboratory observation code lookup",
            base_url=self.base_url,
            auth_type="api_key" if self.api_key else "none",
            rate_limit=30,
            timeout=30,
        )

    async def initialize(self) -> bool:
        headers: Dict[str, str] = {"Accept": "application/fhir+json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers=headers,
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
        """Search LOINC codes by name or description.

        Keyword Args:
            system: Code system filter (e.g. 'http://loinc.org').
            limit: Max results (default 20).
            component: Component filter.
            property: LOINC property filter.
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        qp: Dict[str, Any] = {
            "name:contains": query,
            "_count": min(int(params.get("limit", 20)), 100),
        }
        if params.get("system"):
            qp["system"] = params["system"]
        if params.get("component"):
            qp["component"] = params["component"]
        if params.get("property"):
            qp["property"] = params["property"]

        try:
            response = await self._rate_limited_request(
                "GET", "CodeSystem/$lookup", params=qp
            )
            data = response.json()
            if data.get("resourceType") == "Bundle":
                entries = data.get("entry", [])
                results = [self._normalize_code_system(e.get("resource", {})) for e in entries]
            elif data.get("resourceType") == "Parameters":
                results = [self._normalize_parameters(data)]
            else:
                results = [self._normalize_code_system(data)]

            return ConnectorResult(
                success=True,
                data=results,
                metadata={
                    "source": "LOINC",
                    "total": data.get("total", len(results)),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"LOINC API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific LOINC code.

        Args:
            item_id: LOINC code (e.g. '2339-0' for Glucose).
        """
        if not item_id:
            return ConnectorResult(success=False, error="LOINC code required")

        try:
            response = await self._rate_limited_request(
                "GET",
                "CodeSystem/$lookup",
                params={"code": item_id, "system": "http://loinc.org"},
            )
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_parameters(data),
                metadata={"source": "LOINC", "code": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="LOINC code not found")
            return ConnectorResult(success=False, error=f"LOINC API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("code", params.pop("id", "")), **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_code_system(resource: Dict) -> Dict:
        code = resource.get("code", "")
        display = resource.get("display", "")
        if isinstance(display, dict):
            display = display.get("value", str(display))
        return {
            "code": code,
            "display": display,
            "system": resource.get("system", "http://loinc.org"),
            "version": resource.get("version", ""),
            "property": resource.get("property", []),
        }

    @staticmethod
    def _normalize_parameters(params_resource: Dict) -> Dict:
        """Normalize FHIR Parameters resource from $lookup."""
        result: Dict[str, Any] = {}
        for param in params_resource.get("parameter", []):
            name = param.get("name", "")
            value = param.get("valueString", param.get("valueCode", param.get("valueInteger", "")))
            if name == "display":
                result["display"] = value
            elif name == "code":
                result["code"] = value
            elif name == "system":
                result["system"] = value
            elif name == "version":
                result["version"] = value
            elif name == "property":
                sub = param.get("part", [])
                prop: Dict[str, Any] = {}
                for part in sub:
                    prop[part.get("name", "")] = part.get("valueString", part.get("valueCode", ""))
                if prop:
                    result.setdefault("properties", []).append(prop)
        return result

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
                    "description": "Search LOINC codes by name",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search term"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Look up a specific LOINC code",
                    "parameters": [
                        {"name": "code", "type": "string", "required": True, "description": "LOINC code (e.g. 2339-0)"},
                    ],
                },
            ],
        }


def register_connector():
    import os
    return LOINCConnector, {
        "base_url": "https://fhir.loinc.org/",
        "api_key": os.getenv("LOINC_API_KEY", ""),
    }