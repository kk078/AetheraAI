"""
Cloudflare DNS Manager for Aethera

Provides CRUD operations for DNS records via the Cloudflare API v4.
Each method corresponds to a single DNS operation and can be used independently.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class DNSManager:
    """Manage Cloudflare DNS records for a zone."""

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_key: str, zone_id: str, account_id: str = ""):
        """
        Args:
            api_key:   Cloudflare API bearer token.
            zone_id:   Zone identifier to operate on.
            account_id: Cloudflare account identifier (kept for API consistency).
        """
        self.api_key = api_key
        self.zone_id = zone_id
        self.account_id = account_id
        self._session: Optional[aiohttp.ClientSession] = None

    # -- session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- low-level request --------------------------------------------------

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.request(method, url, json=data) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")
            return result.get("result", {})

    # -- public CRUD --------------------------------------------------------

    async def list_records(self, record_type: Optional[str] = None, name: Optional[str] = None) -> List[Dict]:
        """List DNS records for the zone, optionally filtered by type and/or name.

        Returns:
            List of dicts with keys: id, name, type, content, proxied, ttl.
        """
        endpoint = f"zones/{self.zone_id}/dns_records"
        params: Dict[str, str] = {}
        if record_type:
            params["type"] = record_type
        if name:
            params["name"] = name

        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.get(url, params=params) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "content": r["content"],
                "proxied": r.get("proxied", False),
                "ttl": r.get("ttl", 3600),
            }
            for r in result.get("result", [])
        ]

    async def get_record(self, record_id: str) -> Dict:
        """Fetch a single DNS record by ID.

        Returns:
            Dict with keys: id, name, type, content, proxied, ttl.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/dns_records/{record_id}")
        return {
            "id": result["id"],
            "name": result["name"],
            "type": result["type"],
            "content": result["content"],
            "proxied": result.get("proxied", False),
            "ttl": result.get("ttl", 3600),
        }

    async def create_record(
        self,
        name: str,
        record_type: str,
        content: str,
        ttl: int = 3600,
        proxied: bool = True,
        priority: Optional[int] = None,
    ) -> Dict:
        """Create a new DNS record.

        Args:
            name:        Record name (e.g. "www.example.com").
            record_type: DNS type (A, AAAA, CNAME, MX, TXT, etc.).
            content:     Record value.
            ttl:         Time-to-live in seconds (1 = auto).
            proxied:     Whether Cloudflare proxies the record.
            priority:    MX priority (only for MX records).

        Returns:
            Dict with keys: id, name, type.
        """
        data: Dict[str, Any] = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied,
        }
        if priority is not None:
            data["priority"] = priority

        result = await self._request("POST", f"zones/{self.zone_id}/dns_records", data)
        return {"id": result["id"], "name": result["name"], "type": result["type"]}

    async def update_record(
        self,
        record_id: str,
        name: Optional[str] = None,
        record_type: Optional[str] = None,
        content: Optional[str] = None,
        ttl: Optional[int] = None,
        proxied: Optional[bool] = None,
        priority: Optional[int] = None,
    ) -> Dict:
        """Update an existing DNS record. Only supplied fields are changed.

        Returns:
            Dict with keys: id, name.
        """
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if record_type is not None:
            data["type"] = record_type
        if content is not None:
            data["content"] = content
        if ttl is not None:
            data["ttl"] = ttl
        if proxied is not None:
            data["proxied"] = proxied
        if priority is not None:
            data["priority"] = priority

        result = await self._request("PUT", f"zones/{self.zone_id}/dns_records/{record_id}", data)
        return {"id": result["id"], "name": result["name"]}

    async def delete_record(self, record_id: str) -> bool:
        """Delete a DNS record by ID.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"zones/{self.zone_id}/dns_records/{record_id}")
        return True

    async def export_zone(self) -> str:
        """Export the zone's DNS records in BIND format.

        Returns:
            BIND-format zone file string.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/dns_records/export"
        async with session.get(url) as resp:
            return await resp.text()

    async def import_zone(self, zone_file: str, proxied: bool = False) -> Dict:
        """Import a BIND-format zone file.

        Args:
            zone_file: BIND-format zone file content.
            proxied:    Whether to proxy imported records.

        Returns:
            Dict with import status details.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/dns_records/import"
        data = aiohttp.FormData()
        data.add_field("file", zone_file, filename="zone.txt", content_type="text/plain")
        data.add_field("proxied", str(proxied).lower())
        async with session.post(url, data=data) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Zone import error: {errors[0]['message']}")
            return result.get("result", {})

    async def scan_dns(self) -> Dict:
        """Scan DNS records for the zone and return discovered records.

        Returns:
            Dict with scan status and discovered records.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/dns_records/scan")
        return result