"""
Cloudflare Zero Trust Access Manager for Aethera

Provides Zero Trust access policy management via the Cloudflare API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class AccessManager:
    """Manage Cloudflare Zero Trust access policies, groups, and applications."""

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

    # -- Access Applications -------------------------------------------------

    async def list_applications(self) -> List[Dict]:
        """List all Access applications.

        Returns:
            List of application dicts.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/access/apps"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": a["id"],
                "name": a.get("name", ""),
                "domain": a.get("domain", ""),
                "created_at": a.get("created_at", ""),
            }
            for a in result.get("result", [])
        ]

    async def get_application(self, app_id: str) -> Dict:
        """Get Access application details.

        Returns:
            Dict with application details.
        """
        result = await self._request("GET", f"accounts/{self.account_id}/access/apps/{app_id}")
        return {
            "id": result["id"],
            "name": result.get("name", ""),
            "domain": result.get("domain", ""),
            "type": result.get("type", ""),
            "aud": result.get("aud", ""),
            "auto_redirect_to_identity": result.get("auto_redirect_to_identity", False),
        }

    async def create_application(
        self,
        name: str,
        domain: str,
        session_duration: str = "24h",
        auto_redirect_to_identity: bool = False,
    ) -> Dict:
        """Create an Access application.

        Args:
            name:                      Application name.
            domain:                    Application domain.
            session_duration:          Session duration (e.g. "24h", "12h").
            auto_redirect_to_identity: Whether to auto-redirect to IdP.

        Returns:
            Dict with application details.
        """
        data = {
            "name": name,
            "domain": domain,
            "session_duration": session_duration,
            "auto_redirect_to_identity": auto_redirect_to_identity,
        }
        result = await self._request("POST", f"accounts/{self.account_id}/access/apps", data)
        return {
            "id": result["id"],
            "name": result.get("name", name),
            "domain": result.get("domain", domain),
            "aud": result.get("aud", ""),
        }

    async def delete_application(self, app_id: str) -> bool:
        """Delete an Access application.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"accounts/{self.account_id}/access/apps/{app_id}")
        return True

    # -- Access Policies ----------------------------------------------------

    async def list_policies(self, app_id: Optional[str] = None) -> List[Dict]:
        """List Access policies, optionally filtered by application.

        Args:
            app_id: Optional application ID to filter by.

        Returns:
            List of policy dicts.
        """
        if app_id:
            endpoint = f"accounts/{self.account_id}/access/apps/{app_id}/policies"
        else:
            endpoint = f"accounts/{self.account_id}/access/policies"

        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": p["id"],
                "name": p.get("name", ""),
                "decision": p.get("decision", ""),
                "enabled": p.get("enabled", True),
                "precedence": p.get("precedence", 0),
            }
            for p in result.get("result", [])
        ]

    async def get_policy(self, policy_id: str) -> Dict:
        """Get Access policy details.

        Returns:
            Dict with policy details.
        """
        result = await self._request("GET", f"accounts/{self.account_id}/access/policies/{policy_id}")
        return {
            "id": result["id"],
            "name": result.get("name", ""),
            "decision": result.get("decision", ""),
            "enabled": result.get("enabled", True),
            "precedence": result.get("precedence", 0),
            "include": result.get("include", []),
            "exclude": result.get("exclude", []),
            "require": result.get("require", []),
        }

    async def create_policy(
        self,
        name: str,
        decision: str,
        app_id: str,
        include: Optional[List[Dict]] = None,
        exclude: Optional[List[Dict]] = None,
        require: Optional[List[Dict]] = None,
        precedence: int = 0,
    ) -> Dict:
        """Create an Access policy.

        Args:
            name:       Policy name.
            decision:   Decision type: allow, deny, non_identity, bypass.
            app_id:     Application ID this policy belongs to.
            include:    List of include rules (e.g. [{"email": {"email": "user@example.com"}}]).
            exclude:    List of exclude rules.
            require:    List of require rules.
            precedence: Policy precedence (higher = evaluated first).

        Returns:
            Dict with policy details.
        """
        data: Dict[str, Any] = {
            "name": name,
            "decision": decision,
            "precedence": precedence,
            "include": include or [],
            "exclude": exclude or [],
            "require": require or [],
        }
        result = await self._request(
            "POST",
            f"accounts/{self.account_id}/access/apps/{app_id}/policies",
            data,
        )
        return {
            "id": result["id"],
            "name": result.get("name", name),
            "decision": result.get("decision", decision),
        }

    async def update_policy(
        self,
        policy_id: str,
        name: Optional[str] = None,
        decision: Optional[str] = None,
        include: Optional[List[Dict]] = None,
        exclude: Optional[List[Dict]] = None,
        require: Optional[List[Dict]] = None,
        enabled: Optional[bool] = None,
    ) -> Dict:
        """Update an Access policy.

        Returns:
            Updated policy details.
        """
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if decision is not None:
            data["decision"] = decision
        if include is not None:
            data["include"] = include
        if exclude is not None:
            data["exclude"] = exclude
        if require is not None:
            data["require"] = require
        if enabled is not None:
            data["enabled"] = enabled

        result = await self._request(
            "PATCH",
            f"accounts/{self.account_id}/access/policies/{policy_id}",
            data,
        )
        return {"id": result["id"], "name": result.get("name", ""), "decision": result.get("decision", "")}

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete an Access policy.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"accounts/{self.account_id}/access/policies/{policy_id}")
        return True

    # -- Access Groups -------------------------------------------------------

    async def list_groups(self) -> List[Dict]:
        """List all Access groups.

        Returns:
            List of group dicts.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/access/groups"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": g["id"],
                "name": g.get("name", ""),
                "created_at": g.get("created_at", ""),
            }
            for g in result.get("result", [])
        ]

    async def create_group(
        self,
        name: str,
        include: List[Dict],
        exclude: Optional[List[Dict]] = None,
        require: Optional[List[Dict]] = None,
    ) -> Dict:
        """Create an Access group.

        Args:
            name:    Group name.
            include: List of include rules.
            exclude: List of exclude rules.
            require: List of require rules.

        Returns:
            Dict with group details.
        """
        data: Dict[str, Any] = {
            "name": name,
            "include": include,
        }
        if exclude:
            data["exclude"] = exclude
        if require:
            data["require"] = require

        result = await self._request("POST", f"accounts/{self.account_id}/access/groups", data)
        return {"id": result["id"], "name": result.get("name", name)}

    async def delete_group(self, group_id: str) -> bool:
        """Delete an Access group.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"accounts/{self.account_id}/access/groups/{group_id}")
        return True