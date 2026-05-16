"""
CMS NPI Registry Connector for Aethera
Fetches provider information from the CMS NPI Registry.
API: https://npiregistry.cms.hhs.gov/api/
No authentication required. Rate limit: ~100 req/min.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class CMSNPIConnector(AetheraConnector):
    """CMS NPI Registry connector for National Provider Identifier lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://npiregistry.cms.hhs.gov/api/")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="cms_npi",
            version="1.0.0",
            description="CMS NPI Registry - National Provider Identifier lookup",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=100,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json"},
        )
        return True

    async def cleanup(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute an HTTP request with rate limiting and retry."""
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
    # Public high-level API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search providers by name, organization, location, or taxonomy.

        Keyword Args:
            first_name: Provider first name.
            last_name: Provider last name.
            organization_name: Organization name.
            city: City filter.
            state: Two-letter state code.
            zip: Postal code.
            taxonomy: Taxonomy code filter.
            type: NPI type ('NPI-1' individual, 'NPI-2' organization).
            limit: Max results (1-200, default 200).
        """
        search_params: Dict[str, Any] = {"version": "2.1"}
        if query:
            search_params["first_name"] = query
        for key in ("first_name", "last_name", "organization_name", "city", "state", "taxonomy", "type"):
            if params.get(key):
                search_params[key] = params[key]
        if params.get("zip"):
            search_params["postal_code"] = params["zip"]
        if params.get("limit"):
            search_params["limit"] = min(int(params["limit"]), 200)

        try:
            response = await self._rate_limited_request("GET", "", params=search_params)
            data = response.json()
            results = data.get("results", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_provider(p) for p in results],
                metadata={
                    "source": "CMS NPI Registry",
                    "total": data.get("result_count", 0),
                    "version": "2.1",
                },
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Look up a single provider by NPI number."""
        try:
            response = await self._rate_limited_request(
                "GET", str(item_id), params={"version": "2.1"}
            )
            data = response.json()
            results = data.get("results", [])
            if not results:
                return ConnectorResult(success=False, error="Provider not found")
            return ConnectorResult(
                success=True,
                data=self._normalize_provider(results[0]),
                metadata={"source": "CMS NPI Registry", "version": "2.1"},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"NPI API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Legacy fetch() for backward compat with base class
    # ------------------------------------------------------------------

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Dispatch to search or lookup."""
        params = params or {}
        if endpoint == "lookup":
            npi = params.get("npi", "")
            return await self.get(npi, **params)
        if endpoint == "search":
            query = params.pop("query", "")
            return await self.search(query=query, **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------

    def _normalize_provider(self, provider: Dict) -> Dict:
        return {
            "npi": provider.get("number", ""),
            "type": provider.get("type", ""),
            "name": self._get_provider_name(provider),
            "addresses": self._get_addresses(provider),
            "taxonomies": self._get_taxonomies(provider),
            "phone": provider.get("telephone_number", ""),
            "fax": provider.get("fax_number", ""),
            "email": provider.get("email", ""),
            "certification": provider.get("certification", ""),
            "other_names": provider.get("other_names", []),
        }

    @staticmethod
    def _get_provider_name(provider: Dict) -> str:
        basic = provider.get("basic", {})
        if basic.get("first_name"):
            parts = [basic.get("first_name", ""), basic.get("middle_name", ""), basic.get("last_name", "")]
            return " ".join(p for p in parts if p).strip()
        return provider.get("organization_name", "Unknown")

    @staticmethod
    def _get_addresses(provider: Dict) -> Dict:
        addresses: Dict[str, Any] = {}
        for addr in provider.get("addresses", []):
            purpose = addr.get("address_purpose", "").lower()
            if purpose == "location":
                addresses["location"] = addr
            elif purpose == "mailing":
                addresses["mailing"] = addr
            elif purpose == "primary":
                addresses["primary"] = addr
        return addresses

    @staticmethod
    def _get_taxonomies(provider: Dict) -> List[Dict]:
        return [
            {
                "code": t.get("code", ""),
                "name": t.get("desc", ""),
                "primary": t.get("primary", False),
                "state": t.get("state", ""),
            }
            for t in provider.get("taxonomies", [])
        ]

    # ------------------------------------------------------------------
    # Tool definition
    # ------------------------------------------------------------------

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
                    "description": "Search providers by name, org, location, or taxonomy",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query (name)"},
                        {"name": "state", "type": "string", "description": "Two-letter state code"},
                        {"name": "taxonomy", "type": "string", "description": "Taxonomy code"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-200)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Look up a provider by NPI number",
                    "parameters": [
                        {"name": "npi", "type": "string", "required": True, "description": "10-digit NPI"},
                    ],
                },
            ],
        }


def register_connector():
    """Register the CMS NPI connector."""
    return CMSNPIConnector, {"base_url": "https://npiregistry.cms.hhs.gov/api/"}