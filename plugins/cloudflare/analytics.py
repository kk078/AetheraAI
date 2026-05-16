"""
Cloudflare Analytics for Aethera

Provides traffic, security, and performance analytics via the
Cloudflare GraphQL Analytics API and REST API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class CloudflareAnalytics:
    """Fetch Cloudflare analytics: traffic, security, performance."""

    BASE_URL = "https://api.cloudflare.com/client/v4"
    GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"

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

    # -- GraphQL helper -----------------------------------------------------

    async def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query against the Cloudflare Analytics API."""
        session = await self._ensure_session()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        async with session.post(self.GRAPHQL_URL, json=payload) as resp:
            result = await resp.json()
            if "errors" in result:
                messages = [e.get("message", "Unknown error") for e in result["errors"]]
                raise Exception(f"GraphQL error: {'; '.join(messages)}")
            return result.get("data", {})

    # -- traffic analytics --------------------------------------------------

    async def get_traffic_summary(
        self,
        since: str,
        until: str,
        interval: str = "DAY",
    ) -> List[Dict]:
        """Get HTTP request traffic summary by interval.

        Args:
            since:    ISO timestamp start.
            until:    ISO timestamp end.
            interval: Granularity: MINUTE, HOUR, or DAY.

        Returns:
            List of traffic data points.
        """
        query = """
        query ($zoneId: String!, $since: String!, $until: String!, $interval: String!) {
          viewer {
            zones(filter: {zoneTag: $zoneId}) {
              httpRequests1dGroups(
                filter: {date_gt: $since, date_lt: $until}
                limit: 100
                orderBy: [date_ASC]
              ) {
                dimensions { date }
                sum { requests bytes pageViews }
                uniq { uniques }
              }
            }
          }
        }
        """
        variables = {
            "zoneId": self.zone_id,
            "since": since,
            "until": until,
            "interval": interval,
        }
        data = await self._graphql(query, variables)
        zones = data.get("viewer", {}).get("zones", [])
        if not zones:
            return []
        groups = zones[0].get("httpRequests1dGroups", [])
        return [
            {
                "date": g["dimensions"]["date"],
                "requests": g["sum"]["requests"],
                "bytes": g["sum"]["bytes"],
                "page_views": g["sum"]["pageViews"],
                "uniques": g["uniq"]["uniques"],
            }
            for g in groups
        ]

    async def get_top_paths(
        self,
        since: str,
        until: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Get top requested paths by traffic volume.

        Args:
            since: ISO timestamp start.
            until: ISO timestamp end.
            limit: Number of top paths to return.

        Returns:
            List of dicts with path and request count.
        """
        query = """
        query ($zoneId: String!, $since: String!, $until: String!, $limit: Int!) {
          viewer {
            zones(filter: {zoneTag: $zoneId}) {
              httpRequests1dGroups(
                filter: {date_gt: $since, date_lt: $until}
                limit: $limit
                orderBy: [sum_requests_DESC]
              ) {
                dimensions { date }
                sum { requests }
              }
            }
          }
        }
        """
        # Use a specialized top-paths query via the REST API as fallback
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/analytics/dashboard"
        params = {"since": since, "until": until, "continuous": "true"}
        async with session.get(url, params=params) as resp:
            result = await resp.json()
            if not result.get("success", False):
                return []
            data = result.get("result", {})
            top_paths = data.get("top_paths", data.get("traffic", {}).get("top_paths", []))
            return [
                {"path": p.get("path", p.get("url", "")), "requests": p.get("requests", 0)}
                for p in top_paths[:limit]
            ]

    async def get_bandwidth(
        self,
        since: str,
        until: str,
    ) -> Dict:
        """Get bandwidth usage over a time range.

        Returns:
            Dict with total bytes and time-series data.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/analytics/dashboard"
        async with session.get(url, params={"since": since, "until": until}) as resp:
            result = await resp.json()
            if not result.get("success", False):
                return {"total_bytes": 0, "timeseries": []}
            data = result.get("result", {})
            bandwidth = data.get("bandwidth", data.get("traffic", {}).get("bandwidth", {}))
            return {
                "total_bytes": bandwidth.get("all", bandwidth.get("total", 0)),
                "timeseries": bandwidth.get("timeseries", []),
            }

    # -- security analytics -------------------------------------------------

    async def get_security_events(
        self,
        since: str,
        until: str,
    ) -> Dict:
        """Get security event summary (WAF, firewall, rate limiting).

        Returns:
            Dict with event counts by action and country.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/security/events"
        params = {"since": since, "until": until}
        async with session.get(url, params=params) as resp:
            result = await resp.json()
            if not result.get("success", False):
                return {"total": 0, "by_action": {}, "by_country": {}}
            data = result.get("result", {})
            return {
                "total": data.get("total", 0),
                "by_action": data.get("by_action", {}),
                "by_country": data.get("by_country", {}),
            }

    async def get_firewall_analytics(
        self,
        since: str,
        until: str,
    ) -> Dict:
        """Get firewall rule analytics.

        Returns:
            Dict with firewall event statistics.
        """
        query = """
        query ($zoneId: String!, $since: String!, $until: String!) {
          viewer {
            zones(filter: {zoneTag: $zoneId}) {
              firewallEventsAdaptiveGroups(
                filter: {date_gt: $since, date_lt: $until}
                limit: 100
              ) {
                dimensions { action source countryClient }
                sum { requests }
              }
            }
          }
        }
        """
        variables = {
            "zoneId": self.zone_id,
            "since": since,
            "until": until,
        }
        data = await self._graphql(query, variables)
        zones = data.get("viewer", {}).get("zones", [])
        if not zones:
            return {"events": []}
        groups = zones[0].get("firewallEventsAdaptiveGroups", [])
        return {
            "events": [
                {
                    "action": g["dimensions"]["action"],
                    "source": g["dimensions"]["source"],
                    "country": g["dimensions"]["countryClient"],
                    "requests": g["sum"]["requests"],
                }
                for g in groups
            ]
        }

    # -- performance analytics -----------------------------------------------

    async def get_performance_summary(
        self,
        since: str,
        until: str,
    ) -> Dict:
        """Get performance metrics (TTFB, response time, cache hit ratio).

        Returns:
            Dict with performance metrics.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/zones/{self.zone_id}/analytics/dashboard"
        async with session.get(url, params={"since": since, "until": until}) as resp:
            result = await resp.json()
            if not result.get("success", False):
                return {}
            data = result.get("result", {})
            perf = data.get("performance", data.get("traffic", {}).get("performance", {}))
            return {
                "cache_hit_ratio": perf.get("cache_hit_ratio", 0),
                "ttfb_ms": perf.get("ttfb", {}).get("median", 0),
                "response_time_ms": perf.get("response_time", {}).get("median", 0),
            }

    async def get_cache_analytics(
        self,
        since: str,
        until: str,
    ) -> Dict:
        """Get cache performance analytics.

        Returns:
            Dict with cache hit/miss/bypass counts.
        """
        query = """
        query ($zoneId: String!, $since: String!, $until: String!) {
          viewer {
            zones(filter: {zoneTag: $zoneId}) {
              httpRequests1dGroups(
                filter: {date_gt: $since, date_lt: $until}
                limit: 30
                orderBy: [date_ASC]
              ) {
                dimensions { date cacheStatus }
                sum { requests }
              }
            }
          }
        }
        """
        variables = {
            "zoneId": self.zone_id,
            "since": since,
            "until": until,
        }
        data = await self._graphql(query, variables)
        zones = data.get("viewer", {}).get("zones", [])
        if not zones:
            return {"hits": 0, "misses": 0, "bypasses": 0}
        groups = zones[0].get("httpRequests1dGroups", [])
        hits = misses = bypasses = 0
        for g in groups:
            status = g["dimensions"].get("cacheStatus", "")
            reqs = g["sum"]["requests"]
            if status == "hit":
                hits += reqs
            elif status == "miss":
                misses += reqs
            else:
                bypasses += reqs
        return {"hits": hits, "misses": misses, "bypasses": bypasses}