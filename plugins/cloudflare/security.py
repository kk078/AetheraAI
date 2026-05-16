"""
Cloudflare Security Manager for Aethera

Provides WAF, DDoS protection, SSL/TLS, and firewall rule management
via the Cloudflare API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class SecurityManager:
    """Manage Cloudflare security features: WAF, DDoS, SSL, firewall rules."""

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_key: str, zone_id: str, account_id: str = ""):
        """
        Args:
            api_key:    Cloudflare API bearer token.
            zone_id:    Zone identifier.
            account_id: Cloudflare account identifier.
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

    # -- WAF / Firewall Rules -----------------------------------------------

    async def list_firewall_rules(self) -> List[Dict]:
        """List all firewall rules for the zone.

        Returns:
            List of firewall rule dicts.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/firewall/rules"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": r["id"],
                "action": r.get("action", ""),
                "description": r.get("description", ""),
                "paused": r.get("paused", False),
                "priority": r.get("priority", 0),
                "filter_id": r.get("filter", {}).get("id", ""),
            }
            for r in result.get("result", [])
        ]

    async def create_firewall_rule(
        self,
        filter_expression: str,
        action: str,
        description: str = "",
        priority: int = 0,
        paused: bool = False,
    ) -> Dict:
        """Create a firewall rule with a filter expression.

        Args:
            filter_expression: Firewall filter expression (e.g. "ip.src in {1.2.3.4}").
            action:           Action to take: block, challenge, js_challenge, allow, log.
            description:      Human-readable description.
            priority:         Rule priority (lower = higher priority).
            paused:           Whether the rule starts paused.

        Returns:
            Dict with rule details.
        """
        # First create the filter
        filter_result = await self._request(
            "POST",
            f"zones/{self.zone_id}/filters",
            {
                "expression": filter_expression,
                "description": description,
                "paused": paused,
            },
        )

        # Then create the firewall rule referencing the filter
        rule = await self._request(
            "POST",
            f"zones/{self.zone_id}/firewall/rules",
            {
                "filter": {"id": filter_result["id"]},
                "action": action,
                "description": description,
                "priority": priority,
                "paused": paused,
            },
        )
        return {
            "id": rule["id"],
            "action": rule.get("action", action),
            "description": rule.get("description", description),
            "filter_id": filter_result["id"],
        }

    async def update_firewall_rule(
        self,
        rule_id: str,
        action: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        paused: Optional[bool] = None,
    ) -> Dict:
        """Update an existing firewall rule.

        Returns:
            Updated rule details.
        """
        data: Dict[str, Any] = {}
        if action is not None:
            data["action"] = action
        if description is not None:
            data["description"] = description
        if priority is not None:
            data["priority"] = priority
        if paused is not None:
            data["paused"] = paused

        result = await self._request(
            "PATCH",
            f"zones/{self.zone_id}/firewall/rules/{rule_id}",
            data,
        )
        return {"id": result["id"], "action": result.get("action", ""), "description": result.get("description", "")}

    async def delete_firewall_rule(self, rule_id: str) -> bool:
        """Delete a firewall rule.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"zones/{self.zone_id}/firewall/rules/{rule_id}")
        return True

    # -- WAF Managed Rules --------------------------------------------------

    async def list_waf_packages(self) -> List[Dict]:
        """List WAF managed rule packages.

        Returns:
            List of WAF package dicts.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/firewall/waf/packages")
        packages = result if isinstance(result, list) else result.get("packages", result.get("result", []))
        return [
            {
                "id": p["id"],
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "detection_mode": p.get("detection_mode", ""),
            }
            for p in (packages if isinstance(packages, list) else [])
        ]

    async def get_waf_package(self, package_id: str) -> Dict:
        """Get WAF managed rule package details.

        Returns:
            Dict with WAF package details.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/firewall/waf/packages/{package_id}")
        return {
            "id": result["id"],
            "name": result.get("name", ""),
            "description": result.get("description", ""),
            "detection_mode": result.get("detection_mode", ""),
        }

    async def set_waf_package_mode(self, package_id: str, mode: str) -> Dict:
        """Set WAF package mode (on, off, sim).

        Args:
            package_id: WAF package ID.
            mode:       "on", "off", or "sim" (simulate).

        Returns:
            Updated package details.
        """
        result = await self._request(
            "PATCH",
            f"zones/{self.zone_id}/firewall/waf/packages/{package_id}",
            {"mode": mode},
        )
        return {"id": result["id"], "mode": result.get("mode", mode)}

    # -- DDoS Protection ----------------------------------------------------

    async def get_ddos_protection(self) -> Dict:
        """Get DDoS protection settings for the zone.

        Returns:
            Dict with DDoS configuration.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/ddos-protection")
        return {
            "enabled": result.get("enabled", True),
            "mode": result.get("mode", "standard"),
            "profile": result.get("profile", {}),
        }

    async def set_ddos_protection(self, mode: str = "standard") -> Dict:
        """Set DDoS protection mode.

        Args:
            mode: "standard", "mitigation", or "off".

        Returns:
            Updated DDoS settings.
        """
        result = await self._request(
            "PATCH",
            f"zones/{self.zone_id}/ddos-protection",
            {"mode": mode},
        )
        return {"mode": result.get("mode", mode)}

    # -- SSL/TLS ------------------------------------------------------------

    async def get_ssl_settings(self) -> Dict:
        """Get SSL/TLS settings for the zone.

        Returns:
            Dict with SSL configuration.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/ssl/verification")
        return {
            "ssl_mode": result.get("ssl_mode", ""),
            "certificate_status": result.get("certificate_status", ""),
            "method": result.get("method", ""),
            "hostname": result.get("hostname", ""),
        }

    async def set_ssl_mode(self, mode: str) -> Dict:
        """Set SSL/TLS mode for the zone.

        Args:
            mode: "off", "flexible", "full", "strict", or "strict_only".

        Returns:
            Updated SSL settings.
        """
        result = await self._request(
            "PATCH",
            f"zones/{self.zone_id}/settings/ssl",
            {"value": mode},
        )
        return {"ssl_mode": result.get("value", mode)}

    async def get_ssl_certificate_packs(self) -> List[Dict]:
        """List SSL certificate packs for the zone.

        Returns:
            List of certificate pack dicts.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/ssl/certificate_packs"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                return []
            return result.get("result", [])

    async def enable_always_use_https(self, enabled: bool = True) -> Dict:
        """Enable or disable the "Always Use HTTPS" setting.

        Returns:
            Updated setting value.
        """
        result = await self._request(
            "PATCH",
            f"zones/{self.zone_id}/settings/always_use_https",
            {"value": "on" if enabled else "off"},
        )
        return {"always_use_https": result.get("value", "")}

    # -- Rate Limiting -------------------------------------------------------

    async def list_rate_limits(self) -> List[Dict]:
        """List rate limiting rules.

        Returns:
            List of rate limit dicts.
        """
        result = await self._request("GET", f"zones/{self.zone_id}/rate_limits")
        rules = result if isinstance(result, list) else result.get("result", [])
        return [
            {
                "id": r["id"],
                "description": r.get("description", ""),
                "threshold": r.get("threshold", 0),
                "period": r.get("period", 0),
                "action": r.get("action", {}).get("mode", ""),
            }
            for r in rules
        ]

    async def create_rate_limit(
        self,
        threshold: int,
        period: int,
        description: str = "",
        action: str = "block",
        url_pattern: str = "*",
    ) -> Dict:
        """Create a rate limiting rule.

        Args:
            threshold:    Number of requests allowed per period.
            period:       Time window in seconds.
            description:  Human-readable description.
            action:       Action: block, challenge, js_challenge, log.
            url_pattern:  URL pattern to match.

        Returns:
            Dict with rate limit details.
        """
        data = {
            "threshold": threshold,
            "period": period,
            "description": description,
            "match": {"request": {"url_pattern": url_pattern}},
            "action": {"mode": action},
        }
        result = await self._request("POST", f"zones/{self.zone_id}/rate_limits", data)
        return {
            "id": result["id"],
            "threshold": result.get("threshold", threshold),
            "period": result.get("period", period),
        }

    async def delete_rate_limit(self, rule_id: str) -> bool:
        """Delete a rate limiting rule.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"zones/{self.zone_id}/rate_limits/{rule_id}")
        return True