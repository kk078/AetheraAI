"""
GitHub REST API v3 Connector for Aethera
Fetches repositories, issues, pull requests, and other GitHub resources.
API: https://api.github.com/
Optional token increases rate limits (60/hr -> 5000/hr).
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class GitHubConnector(AetheraConnector):
    """GitHub REST API v3 connector for repository and issue data."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.github.com/")
        self.token = config.get("token", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="github",
            version="1.0.0",
            description="GitHub REST API v3 - Repositories, issues, and pull requests",
            base_url=self.base_url,
            auth_type="bearer" if self.token else "none",
            rate_limit=5000 if self.token else 60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AetheraAI/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

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
            # Per-hour limit, convert to per-second
            min_interval = 3600.0 / config.rate_limit
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
        """Search GitHub repositories, issues, or users.

        Keyword Args:
            target: What to search: 'repositories', 'issues', 'users' (default 'repositories').
            sort: Sort field: 'stars', 'forks', 'updated' (repos); 'comments', 'created', 'updated' (issues).
            order: 'asc' or 'desc' (default 'desc').
            limit: Max results (1-100, default 30).
            page: Page number (1-based).
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        target = params.get("target", "repositories")
        limit = min(int(params.get("limit", 30)), 100)

        qp: Dict[str, Any] = {
            "q": query,
            "per_page": limit,
            "page": params.get("page", 1),
        }
        if params.get("sort"):
            qp["sort"] = params["sort"]
        if params.get("order"):
            qp["order"] = params["order"]

        try:
            response = await self._rate_limited_request("GET", f"search/{target}", params=qp)
            data = response.json()
            items = data.get("items", [])

            if target == "repositories":
                normalized = [self._normalize_repo(r) for r in items]
            elif target == "issues":
                normalized = [self._normalize_issue(r) for r in items]
            elif target == "users":
                normalized = [self._normalize_user(r) for r in items]
            else:
                normalized = items

            return ConnectorResult(
                success=True,
                data=normalized,
                metadata={
                    "source": "GitHub",
                    "target": target,
                    "total": data.get("total_count", 0),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"GitHub API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Retrieve a specific repository.

        Args:
            item_id: Repository full name (owner/repo, e.g. 'octocat/Hello-World').
        """
        if not item_id:
            return ConnectorResult(success=False, error="Repository full name required (owner/repo)")

        try:
            response = await self._rate_limited_request("GET", f"repos/{item_id}")
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_repo(data),
                metadata={"source": "GitHub", "repo": item_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return ConnectorResult(success=False, error="Repository not found")
            return ConnectorResult(success=False, error=f"GitHub API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def issues(self, repo: str, **params) -> ConnectorResult:
        """List issues for a repository.

        Args:
            repo: Repository full name (owner/repo).
        Keyword Args:
            state: 'open', 'closed', 'all' (default 'open').
            labels: Comma-separated label names.
            limit: Max results (1-100, default 30).
        """
        if not repo:
            return ConnectorResult(success=False, error="Repository full name required")

        qp: Dict[str, Any] = {
            "state": params.get("state", "open"),
            "per_page": min(int(params.get("limit", 30)), 100),
        }
        if params.get("labels"):
            qp["labels"] = params["labels"]

        try:
            response = await self._rate_limited_request("GET", f"repos/{repo}/issues", params=qp)
            data = response.json()
            return ConnectorResult(
                success=True,
                data=[self._normalize_issue(i) for i in data],
                metadata={"source": "GitHub", "repo": repo, "count": len(data)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def pull_requests(self, repo: str, **params) -> ConnectorResult:
        """List pull requests for a repository.

        Args:
            repo: Repository full name (owner/repo).
        Keyword Args:
            state: 'open', 'closed', 'all' (default 'open').
            limit: Max results (1-100, default 30).
        """
        if not repo:
            return ConnectorResult(success=False, error="Repository full name required")

        qp: Dict[str, Any] = {
            "state": params.get("state", "open"),
            "per_page": min(int(params.get("limit", 30)), 100),
        }

        try:
            response = await self._rate_limited_request("GET", f"repos/{repo}/pulls", params=qp)
            data = response.json()
            return ConnectorResult(
                success=True,
                data=[self._normalize_issue(pr) for pr in data],
                metadata={"source": "GitHub", "repo": repo, "count": len(data)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def rate_limit_status(self) -> ConnectorResult:
        """Check current rate limit status."""
        try:
            response = await self._rate_limited_request("GET", "rate_limit")
            data = response.json()
            resources = data.get("resources", {})
            core = resources.get("core", resources.get("search", {}))
            return ConnectorResult(
                success=True,
                data={
                    "limit": core.get("limit", 0),
                    "remaining": core.get("remaining", 0),
                    "reset": core.get("reset", 0),
                },
                metadata={"source": "GitHub"},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "get":
            return await self.get(params.pop("repo", params.pop("id", "")), **params)
        if endpoint == "issues":
            return await self.issues(params.pop("repo", ""), **params)
        if endpoint == "pull_requests":
            return await self.pull_requests(params.pop("repo", ""), **params)
        if endpoint == "rate_limit":
            return await self.rate_limit_status()
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_repo(repo: Dict) -> Dict:
        return {
            "id": repo.get("id", ""),
            "full_name": repo.get("full_name", ""),
            "description": repo.get("description", ""),
            "url": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "language": repo.get("language", ""),
            "created": repo.get("created_at", ""),
            "updated": repo.get("updated_at", ""),
            "license": repo.get("license", {}).get("name", "") if isinstance(repo.get("license"), dict) else "",
            "topics": repo.get("topics", []),
            "archived": repo.get("archived", False),
        }

    @staticmethod
    def _normalize_issue(issue: Dict) -> Dict:
        return {
            "id": issue.get("id", ""),
            "number": issue.get("number", 0),
            "title": issue.get("title", ""),
            "state": issue.get("state", ""),
            "url": issue.get("html_url", ""),
            "user": issue.get("user", {}).get("login", "") if isinstance(issue.get("user"), dict) else "",
            "labels": [l.get("name", l) if isinstance(l, dict) else l for l in issue.get("labels", [])],
            "created": issue.get("created_at", ""),
            "updated": issue.get("updated_at", ""),
            "comments": issue.get("comments", 0),
            "body": (issue.get("body") or "")[:500] if issue.get("body") else "",
        }

    @staticmethod
    def _normalize_user(user: Dict) -> Dict:
        return {
            "id": user.get("id", ""),
            "login": user.get("login", ""),
            "name": user.get("name", ""),
            "url": user.get("html_url", ""),
            "type": user.get("type", ""),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "bio": (user.get("bio") or "")[:300] if user.get("bio") else "",
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
                    "description": "Search GitHub repositories, issues, or users",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "target", "type": "string", "description": "repositories, issues, or users"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get repository details",
                    "parameters": [
                        {"name": "repo", "type": "string", "required": True, "description": "owner/repo"},
                    ],
                },
                {
                    "name": "issues",
                    "description": "List repository issues",
                    "parameters": [
                        {"name": "repo", "type": "string", "required": True, "description": "owner/repo"},
                        {"name": "state", "type": "string", "description": "open, closed, all"},
                    ],
                },
                {
                    "name": "pull_requests",
                    "description": "List repository pull requests",
                    "parameters": [
                        {"name": "repo", "type": "string", "required": True, "description": "owner/repo"},
                    ],
                },
            ],
        }


def register_connector():
    import os
    return GitHubConnector, {
        "base_url": "https://api.github.com/",
        "token": os.getenv("GITHUB_TOKEN", os.getenv("GITHUB_API_TOKEN", "")),
    }