"""
Cloudflare REST API v4 Connector for Aethera
Manages Cloudflare zones, DNS records, and account settings.
API: https://api.cloudflare.com/client/v4/
Requires API token or Global API Key.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class CloudflareConnector(AetheraConnector):
    """Cloudflare API v4 connector for zone and DNS management."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.cloudflare.com/client/v4/")
        self.api_token = config.get("api_token", "")
        self.api_key = config.get("api_key", "")
        self.email = config.get("email", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="cloudflare",
            version="1.0.0",
            description="Cloudflare API v4 - DNS, zones, and account management",
            base_url=self.base_url,
            auth_type="bearer",
            rate_limit=1200,  # Cloudflare allows 1200 req/5min
            timeout=30,
        )

    async def initialize(self) -> bool:
        if not self.api_token and not (self.api_key and self.email):
            raise ValueError("Cloudflare API token or (API key + email) required")

        headers: Dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}

        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        else:
            headers["X-Auth-Email"] = self.email
            headers["X-Auth-Key"] = self.api_key

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
            # 1200 req per 5 min = 4/sec
            min_interval = 300.0 / config.rate_limit
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
        """Search/list Cloudflare zones.

        Keyword Args:
            name: Zone name filter.
            status: Zone status filter (active, pending, initializing).
            limit: Max results (1-50, default 20).
            page: Page number.
        """
        qp: Dict[str, Any] = {
            "per_page": min(int(params.get("limit", 20)), 50),
            "page": params.get("page", 1),
        }
        if query:
            qp["name"] = query
        if params.get("status"):
            qp["status"] = params["status"]

        try:
            response = await self._rate_limited_request("GET", "zones", params=qp)
            data = response.json()
            result_info = data.get("result_info", {})
            results = data.get("result", [])

            return ConnectorResult(
                success=True,
                data=[self._normalize_zone(z) for z in results],
                metadata={
                    "source": "Cloudflare",
                    "total": result_info.get("total_count", len(results)),
                    "page": result_info.get("page", 1),
                    "total_pages": result_info.get("total_pages", 1),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Cloudflare API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Get details for a specific zone.

        Args:
            item_id: Zone identifier (zone ID or zone name).
        """
        if not item_id:
            return ConnectorResult(success=False, error="Zone ID required")

        try:
            response = await self._rate_limited_request("GET", f"zones/{item_id}")
            data = response.json()
            result = data.get("result", data)
            return ConnectorResult(
                success=True,
                data=self._normalize_zone(result),
                metadata={"source": "Cloudflare", "zone_id": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Zone not found")
            return ConnectorResult(success=False, error=f"Cloudflare API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def dns_records(self, zone_id: str, **params) -> ConnectorResult:
        """List DNS records for a zone.

        Args:
            zone_id: Cloudflare zone ID.
        Keyword Args:
            type: Record type filter (A, AAAA, CNAME, MX, TXT, etc.).
            name: Record name filter.
            limit: Max results (1-100, default 20).
        """
        if not zone_id:
            return ConnectorResult(success=False, error="Zone ID required")

        qp: Dict[str, Any] = {"per_page": min(int(params.get("limit", 20)), 100)}
        if params.get("type"):
            qp["type"] = params["type"]
        if params.get("name"):
            qp["name"] = params["name"]

        try:
            response = await self._rate_limited_request(
                "GET", f"zones/{zone_id}/dns_records", params=qp
            )
            data = response.json()
            records = data.get("result", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_dns_record(r) for r in records],
                metadata={"source": "Cloudflare", "zone_id": zone_id, "count": len(records)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def verify_token(self) -> ConnectorResult:
        """Verify the current API token is valid."""
        try:
            response = await self._rate_limited_request("GET", "user/tokens/verify")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=data.get("result", data),
                metadata={"source": "Cloudflare"},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", params.pop("name", "")), **params)
        if endpoint == "get":
            return await self.get(params.pop("zone_id", params.pop("id", "")), **params)
        if endpoint == "dns_records":
            return await self.dns_records(params.pop("zone_id", ""), **params)
        if endpoint == "verify":
            return await self.verify_token()
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_zone(zone: Dict) -> Dict:
        return {
            "id": zone.get("id", ""),
            "name": zone.get("name", ""),
            "status": zone.get("status", ""),
            "type": zone.get("type", ""),
            "nameservers": zone.get("name_servers", []),
            "original_nameservers": zone.get("original_name_servers", []),
            "created": zone.get("created_on", zone.get("created", "")),
            "modified": zone.get("modified_on", zone.get("modified", "")),
            "plan": zone.get("plan", {}).get("name", "") if isinstance(zone.get("plan"), dict) else "",
        }

    @staticmethod
    def _normalize_dns_record(record: Dict) -> Dict:
        return {
            "id": record.get("id", ""),
            "type": record.get("type", ""),
            "name": record.get("name", ""),
            "content": record.get("content", ""),
            "ttl": record.get("ttl", 0),
            "priority": record.get("priority"),
            "proxied": record.get("proxied", False),
            "comment": record.get("comment", ""),
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
                    "description": "List/search Cloudflare zones",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Zone name filter"},
                        {"name": "status", "type": "string", "description": "active, pending, initializing"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-50)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get zone details",
                    "parameters": [
                        {"name": "zone_id", "type": "string", "required": True, "description": "Zone ID"},
                    ],
                },
                {
                    "name": "dns_records",
                    "description": "List DNS records for a zone",
                    "parameters": [
                        {"name": "zone_id", "type": "string", "required": True},
                        {"name": "type", "type": "string", "description": "A, AAAA, CNAME, MX, TXT"},
                    ],
                },
            ],
        }


def register_connector():
    import os
    return CloudflareConnector, {
        "base_url": "https://api.cloudflare.com/client/v4/",
        "api_token": os.getenv("CLOUDFLARE_API_TOKEN", ""),
        "api_key": os.getenv("CLOUDFLARE_API_KEY", ""),
        "email": os.getenv("CLOUDFLARE_EMAIL", ""),
    }