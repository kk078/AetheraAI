"""
GitHub Issue/PR Manager for Aethera

Provides issue and pull request management operations
via the GitHub REST API v3.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class IssueManager:
    """Manage GitHub issues and pull requests."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        """
        Args:
            token: GitHub personal access token or OAuth token.
        """
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None

    # -- session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"token {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- helpers ------------------------------------------------------------

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        async with session.request(method, url, json=data) as resp:
            if resp.status >= 400:
                error = await resp.json()
                raise Exception(f"GitHub API error: {error.get('message', 'Unknown error')}")
            if resp.status == 204:
                return {"status": "success", "code": 204}
            return await resp.json()

    # -- Issue CRUD ---------------------------------------------------------

    async def list_issues(
        self,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        per_page: int = 50,
    ) -> List[Dict]:
        """List issues for a repository.

        Args:
            repo:     Repository in "owner/name" format.
            state:    Issue state filter: open, closed, all.
            labels:   Filter by label names.
            per_page: Number of results.

        Returns:
            List of issue dicts.
        """
        params = f"state={state}&per_page={per_page}"
        if labels:
            params += f"&labels={','.join(labels)}"
        result = await self._request("GET", f"repos/{repo}/issues?{params}")
        return [
            {
                "number": i["number"],
                "title": i["title"],
                "state": i.get("state", "open"),
                "labels": [l["name"] for l in i.get("labels", [])],
                "assignees": [a["login"] for a in i.get("assignees", [])],
                "created_at": i.get("created_at", ""),
            }
            for i in result
            if "pull_request" not in i  # Exclude PRs
        ]

    async def get_issue(self, repo: str, issue_number: int) -> Dict:
        """Get issue details.

        Returns:
            Dict with issue details.
        """
        result = await self._request("GET", f"repos/{repo}/issues/{issue_number}")
        return {
            "number": result["number"],
            "title": result["title"],
            "body": result.get("body", ""),
            "state": result.get("state", "open"),
            "labels": [l["name"] for l in result.get("labels", [])],
            "assignees": [a["login"] for a in result.get("assignees", [])],
        }

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict:
        """Create a new issue.

        Returns:
            Dict with keys: number, url.
        """
        data: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        result = await self._request("POST", f"repos/{repo}/issues", data)
        return {"number": result["number"], "url": result["html_url"]}

    async def update_issue(
        self,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        state: Optional[str] = None,
    ) -> Dict:
        """Update an existing issue.

        Returns:
            Dict with keys: number, url.
        """
        data: Dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if labels is not None:
            data["labels"] = labels
        if assignees is not None:
            data["assignees"] = assignees
        if state is not None:
            data["state"] = state

        result = await self._request("PATCH", f"repos/{repo}/issues/{issue_number}", data)
        return {"number": result["number"], "url": result["html_url"]}

    async def close_issue(self, repo: str, issue_number: int) -> bool:
        """Close an issue.

        Returns:
            True on success.
        """
        await self._request("PATCH", f"repos/{repo}/issues/{issue_number}", {"state": "closed"})
        return True

    # -- Issue Comments -----------------------------------------------------

    async def list_comments(self, repo: str, issue_number: int) -> List[Dict]:
        """List comments on an issue or PR.

        Returns:
            List of comment dicts.
        """
        result = await self._request("GET", f"repos/{repo}/issues/{issue_number}/comments")
        return [
            {
                "id": c["id"],
                "user": c["user"]["login"],
                "body": c.get("body", ""),
                "created_at": c.get("created_at", ""),
            }
            for c in result
        ]

    async def add_comment(self, repo: str, issue_number: int, body: str) -> Dict:
        """Add a comment to an issue or PR.

        Returns:
            Dict with keys: id, url.
        """
        result = await self._request(
            "POST",
            f"repos/{repo}/issues/{issue_number}/comments",
            {"body": body},
        )
        return {"id": result["id"], "url": result.get("html_url", "")}

    # -- Pull Request CRUD --------------------------------------------------

    async def list_prs(
        self,
        repo: str,
        state: str = "open",
        per_page: int = 50,
    ) -> List[Dict]:
        """List pull requests for a repository.

        Returns:
            List of PR dicts.
        """
        result = await self._request("GET", f"repos/{repo}/pulls?state={state}&per_page={per_page}")
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "head": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "user": pr["user"]["login"],
                "state": pr.get("state", "open"),
                "draft": pr.get("draft", False),
            }
            for pr in result
        ]

    async def get_pr(self, repo: str, pr_number: int) -> Dict:
        """Get pull request details.

        Returns:
            Dict with PR details.
        """
        result = await self._request("GET", f"repos/{repo}/pulls/{pr_number}")
        return {
            "number": result["number"],
            "title": result["title"],
            "body": result.get("body", ""),
            "state": result.get("state", "open"),
            "head": result["head"]["ref"],
            "base": result["base"]["ref"],
            "merged": result.get("merged", False),
            "url": result["html_url"],
            "mergeable": result.get("mergeable"),
            "draft": result.get("draft", False),
        }

    async def create_pr(
        self,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> Dict:
        """Create a pull request.

        Args:
            repo:  Repository in "owner/name" format.
            title: PR title.
            head:  Head branch (source).
            base:  Base branch (target).
            body:  PR description.
            draft: Whether to create as draft.

        Returns:
            Dict with keys: number, url.
        """
        data: Dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        result = await self._request("POST", f"repos/{repo}/pulls", data)
        return {"number": result["number"], "url": result["html_url"]}

    async def merge_pr(
        self,
        repo: str,
        pr_number: int,
        commit_message: str = "",
        merge_method: str = "merge",
    ) -> Dict:
        """Merge a pull request.

        Args:
            repo:          Repository in "owner/name" format.
            pr_number:     PR number.
            commit_message: Merge commit message.
            merge_method:   Merge method: merge, squash, rebase.

        Returns:
            Dict with keys: merged, sha.
        """
        data: Dict[str, Any] = {
            "commit_message": commit_message,
            "merge_method": merge_method,
        }
        result = await self._request("PUT", f"repos/{repo}/pulls/{pr_number}/merge", data)
        return {"merged": result.get("merged", False), "sha": result.get("sha", "")}

    async def close_pr(self, repo: str, pr_number: int) -> bool:
        """Close a pull request without merging.

        Returns:
            True on success.
        """
        await self._request("PATCH", f"repos/{repo}/pulls/{pr_number}", {"state": "closed"})
        return True

    # -- PR Reviews ---------------------------------------------------------

    async def list_reviews(self, repo: str, pr_number: int) -> List[Dict]:
        """List reviews on a pull request.

        Returns:
            List of review dicts.
        """
        result = await self._request("GET", f"repos/{repo}/pulls/{pr_number}/reviews")
        return [
            {
                "id": r["id"],
                "user": r["user"]["login"],
                "state": r.get("state", ""),
                "body": r.get("body", ""),
            }
            for r in result
        ]

    async def create_review(
        self,
        repo: str,
        pr_number: int,
        body: str = "",
        event: str = "COMMENT",
        comments: Optional[List[Dict]] = None,
    ) -> Dict:
        """Create a review on a pull request.

        Args:
            repo:     Repository in "owner/name" format.
            pr_number: PR number.
            body:     Review body.
            event:    Review event: APPROVE, REQUEST_CHANGES, COMMENT.
            comments: List of inline comment dicts with path, position, body.

        Returns:
            Dict with keys: id, state.
        """
        data: Dict[str, Any] = {"body": body, "event": event}
        if comments:
            data["comments"] = comments

        result = await self._request(
            "POST",
            f"repos/{repo}/pulls/{pr_number}/reviews",
            data,
        )
        return {"id": result["id"], "state": result.get("state", "")}

    # -- Labels -------------------------------------------------------------

    async def list_labels(self, repo: str) -> List[Dict]:
        """List labels for a repository.

        Returns:
            List of label dicts.
        """
        result = await self._request("GET", f"repos/{repo}/labels")
        return [
            {"name": l["name"], "color": l.get("color", ""), "description": l.get("description", "")}
            for l in result
        ]

    async def add_label(self, repo: str, issue_number: int, labels: List[str]) -> List[Dict]:
        """Add labels to an issue.

        Returns:
            Updated list of label dicts.
        """
        result = await self._request(
            "POST",
            f"repos/{repo}/issues/{issue_number}/labels",
            {"labels": labels},
        )
        return [{"name": l["name"], "color": l.get("color", "")} for l in result]