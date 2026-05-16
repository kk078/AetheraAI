"""
Cloudflare Workers Manager for Aethera

Provides Workers script management operations via the Cloudflare API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class WorkersManager:
    """Manage Cloudflare Workers scripts, bindings, and routes."""

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_key: str, account_id: str):
        """
        Args:
            api_key:    Cloudflare API bearer token.
            account_id: Cloudflare account identifier.
        """
        self.api_key = api_key
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

    # -- low-level request helpers -------------------------------------------

    async def _json_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.request(method, url, json=data) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")
            return result.get("result", {})

    # -- public operations --------------------------------------------------

    async def list_scripts(self) -> List[Dict]:
        """List all Workers scripts.

        Returns:
            List of dicts with keys: name, created_on, modified_on.
        """
        result = await self._json_request(
            "GET",
            f"accounts/{self.account_id}/workers/scripts",
        )
        workers = result.get("workers", []) if isinstance(result, dict) else result
        return [
            {
                "name": w["id"],
                "created_on": w.get("created_on", ""),
                "modified_on": w.get("modified_on", ""),
            }
            for w in workers
        ]

    async def get_script(self, script_name: str) -> str:
        """Download a Workers script source.

        Returns:
            The script content as a string.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/workers/scripts/{script_name}"
        async with session.get(url) as resp:
            return await resp.text()

    async def deploy_script(
        self,
        name: str,
        script: str,
        bindings: Optional[List[Dict]] = None,
        compatibility_date: Optional[str] = None,
        compatibility_flags: Optional[List[str]] = None,
    ) -> Dict:
        """Deploy or update a Workers script.

        Args:
            name:               Worker script name.
            script:             JavaScript module content.
            bindings:           List of binding dicts (type, name, ...).
            compatibility_date: Workers runtime compatibility date.
            compatibility_flags: List of compatibility flag strings.

        Returns:
            Dict with keys: name, status.
        """
        metadata: Dict[str, Any] = {
            "main_module": "main.js",
        }
        if bindings:
            metadata["bindings"] = bindings
        if compatibility_date:
            metadata["compatibility_date"] = compatibility_date
        if compatibility_flags:
            metadata["compatibility_flags"] = compatibility_flags

        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/workers/scripts/{name}"

        form = aiohttp.FormData()
        form.add_field(
            "metadata",
            __import__("json").dumps(metadata),
            filename="metadata.json",
            content_type="application/json",
        )
        form.add_field(
            "main.js",
            script,
            filename="main.js",
            content_type="application/javascript+module",
        )

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with session.put(url, data=form, headers=headers) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Worker deploy failed: {errors[0]['message']}")

        return {"name": name, "status": "deployed"}

    async def delete_script(self, script_name: str) -> bool:
        """Delete a Workers script.

        Returns:
            True on success.
        """
        await self._json_request(
            "DELETE",
            f"accounts/{self.account_id}/workers/scripts/{script_name}",
        )
        return True

    # -- routes -------------------------------------------------------------

    async def list_routes(self, zone_id: str) -> List[Dict]:
        """List Worker routes for a zone.

        Args:
            zone_id: Zone identifier.

        Returns:
            List of route dicts with keys: id, pattern, script.
        """
        result = await self._json_request(
            "GET",
            f"zones/{zone_id}/workers/routes",
        )
        routes = result if isinstance(result, list) else result.get("routes", result.get("result", []))
        return [
            {
                "id": r["id"],
                "pattern": r["pattern"],
                "script": r.get("script", ""),
            }
            for r in routes
        ]

    async def create_route(self, zone_id: str, pattern: str, script_name: str) -> Dict:
        """Create a Worker route.

        Args:
            zone_id:     Zone identifier.
            pattern:     Route pattern (e.g. "example.com/*").
            script_name: Worker script to invoke.

        Returns:
            Dict with keys: id, pattern, script.
        """
        result = await self._json_request(
            "POST",
            f"zones/{zone_id}/workers/routes",
            {"pattern": pattern, "script": script_name},
        )
        return {"id": result["id"], "pattern": result["pattern"], "script": result.get("script", "")}

    async def delete_route(self, zone_id: str, route_id: str) -> bool:
        """Delete a Worker route.

        Returns:
            True on success.
        """
        await self._json_request("DELETE", f"zones/{zone_id}/workers/routes/{route_id}")
        return True

    # -- cron triggers ------------------------------------------------------

    async def list_cron_triggers(self, script_name: str) -> List[Dict]:
        """List cron triggers for a Workers script.

        Returns:
            List of cron trigger dicts.
        """
        result = await self._json_request(
            "GET",
            f"accounts/{self.account_id}/workers/scripts/{script_name}/schedules",
        )
        schedules = result.get("schedules", result) if isinstance(result, dict) else result
        return schedules if isinstance(schedules, list) else []

    async def update_cron_triggers(self, script_name: str, crons: List[str]) -> List[Dict]:
        """Update cron triggers for a Workers script (replaces all existing triggers).

        Args:
            script_name: Worker script name.
            crons:       List of cron expressions (e.g. ["*/5 * * * *"]).

        Returns:
            Updated list of cron trigger dicts.
        """
        result = await self._json_request(
            "PUT",
            f"accounts/{self.account_id}/workers/scripts/{script_name}/schedules",
            {"cron": crons},
        )
        schedules = result.get("schedules", result) if isinstance(result, dict) else result
        return schedules if isinstance(schedules, list) else []

    # -- usage / analytics ---------------------------------------------------

    async def get_script_usage(self, script_name: str, since: Optional[str] = None) -> Dict:
        """Get aggregate usage statistics for a Workers script.

        Args:
            script_name: Worker script name.
            since:       ISO timestamp for start of window (default: 24h ago).

        Returns:
            Dict with usage metrics (requests, duration, errors).
        """
        params = {}
        if since:
            params["since"] = since

        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/workers/scripts/{script_name}/analytics/aggregate"
        async with session.get(url, params=params) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")
            return result.get("result", {})