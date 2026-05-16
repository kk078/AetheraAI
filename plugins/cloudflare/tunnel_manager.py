"""
Cloudflare Tunnel Manager for Aethera

Provides tunnel create, delete, status, and configuration operations
via the Cloudflare API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class TunnelManager:
    """Manage Cloudflare Tunnels (formerly Argo Tunnels)."""

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

    # -- public operations --------------------------------------------------

    async def list_tunnels(self, include_deleted: bool = False) -> List[Dict]:
        """List all tunnels for the account.

        Args:
            include_deleted: Whether to include deleted tunnels.

        Returns:
            List of dicts with keys: id, name, status, connections.
        """
        params: Dict[str, str] = {}
        if include_deleted:
            params["is_deleted"] = "true"

        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/tunnels"
        async with session.get(url, params=params) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        tunnels = result.get("result", [])
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "status": "active" if t.get("connections") else "inactive",
                "connections": len(t.get("connections", [])),
            }
            for t in tunnels
        ]

    async def get_tunnel(self, tunnel_id: str) -> Dict:
        """Get details for a specific tunnel.

        Returns:
            Dict with keys: id, name, status, connections, created_at.
        """
        result = await self._request("GET", f"accounts/{self.account_id}/tunnels/{tunnel_id}")
        return {
            "id": result["id"],
            "name": result["name"],
            "status": "active" if result.get("connections") else "inactive",
            "connections": len(result.get("connections", [])),
            "created_at": result.get("created_at", ""),
        }

    async def create_tunnel(self, name: str, config_src: str = "cloudflare") -> Dict:
        """Create a new Cloudflare Tunnel.

        Args:
            name:       Tunnel name.
            config_src: Configuration source ("cloudflare" or "local").

        Returns:
            Dict with keys: id, name, token, install_command.
        """
        tunnel = await self._request(
            "POST",
            f"accounts/{self.account_id}/tunnels",
            {"name": name, "config_src": config_src},
        )

        # Generate tunnel token
        token_result = await self._request(
            "POST",
            f"accounts/{self.account_id}/tunnels/{tunnel['id']}/tokens",
        )
        token = token_result.get("token", "")

        return {
            "id": tunnel["id"],
            "name": tunnel["name"],
            "token": token,
            "install_command": f"cloudflared service install {token}",
        }

    async def delete_tunnel(self, tunnel_id: str) -> bool:
        """Delete a tunnel.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"accounts/{self.account_id}/tunnels/{tunnel_id}")
        return True

    async def get_tunnel_config(self, tunnel_id: str) -> Dict:
        """Get the configuration for a tunnel.

        Returns:
            Dict with tunnel configuration including ingress rules.
        """
        return await self._request(
            "GET",
            f"accounts/{self.account_id}/tunnels/{tunnel_id}/configurations",
        )

    async def update_tunnel_config(self, tunnel_id: str, config: Dict[str, Any]) -> Dict:
        """Update the configuration for a tunnel.

        Args:
            tunnel_id: Tunnel identifier.
            config:    Configuration dict including 'ingress' rules.

        Returns:
            Updated configuration result.
        """
        return await self._request(
            "PUT",
            f"accounts/{self.account_id}/tunnels/{tunnel_id}/configurations",
            config,
        )

    async def get_tunnel_connections(self, tunnel_id: str) -> List[Dict]:
        """List active connections for a tunnel.

        Returns:
            List of connection dicts with id, edge_ip, origin_ip, etc.
        """
        result = await self._request(
            "GET",
            f"accounts/{self.account_id}/tunnels/{tunnel_id}/connections",
        )
        return result if isinstance(result, list) else result.get("connections", [])

    async def cleanup_tunnel(self, tunnel_id: str) -> Dict:
        """Clean up a tunnel's connections.

        Returns:
            Dict with cleanup status.
        """
        return await self._request(
            "DELETE",
            f"accounts/{self.account_id}/tunnels/{tunnel_id}/connections",
        )