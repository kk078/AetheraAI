"""
GitHub Repository Manager for Aethera

Provides repository management and code search operations
via the GitHub REST API v3.
"""
import base64
from typing import Any, Dict, List, Optional

import aiohttp


class RepoManager:
    """Manage GitHub repositories, branches, files, and code search."""

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

    @staticmethod
    def parse_repo(repo: str) -> tuple:
        """Parse 'owner/name' string into (owner, name) tuple."""
        if "/" in repo:
            owner, name = repo.split("/", 1)
            return owner, name
        return "", ""

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

    # -- Repository CRUD ----------------------------------------------------

    async def list_repos(self, sort: str = "updated", per_page: int = 100) -> List[Dict]:
        """List repositories for the authenticated user.

        Args:
            sort:     Sort field (created, updated, pushed, full_name).
            per_page: Results per page (max 100).

        Returns:
            List of dicts with keys: name, full_name, description, private, updated.
        """
        result = await self._request("GET", f"user/repos?sort={sort}&per_page={per_page}")
        return [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description", ""),
                "private": r.get("private", False),
                "updated": r.get("updated_at", ""),
            }
            for r in result
        ]

    async def get_repo(self, repo: str) -> Dict:
        """Get repository details.

        Args:
            repo: Repository in "owner/name" format.

        Returns:
            Dict with repository details.
        """
        result = await self._request("GET", f"repos/{repo}")
        return {
            "name": result["name"],
            "full_name": result["full_name"],
            "description": result.get("description", ""),
            "private": result.get("private", False),
            "stars": result.get("stargazers_count", 0),
            "forks": result.get("forks_count", 0),
            "default_branch": result.get("default_branch", "main"),
        }

    async def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
    ) -> Dict:
        """Create a new repository for the authenticated user.

        Args:
            name:        Repository name.
            description: Repository description.
            private:     Whether the repo is private.
            auto_init:   Initialize with a README.

        Returns:
            Dict with keys: name, full_name, url.
        """
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        result = await self._request("POST", "user/repos", data)
        return {
            "name": result["name"],
            "full_name": result["full_name"],
            "url": result.get("html_url", ""),
        }

    async def delete_repo(self, repo: str) -> bool:
        """Delete a repository.

        Args:
            repo: Repository in "owner/name" format.

        Returns:
            True on success.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/repos/{repo}"
        async with session.delete(url) as resp:
            return resp.status == 204

    # -- File Operations ----------------------------------------------------

    async def get_file(self, repo: str, path: str, branch: str = "main") -> Dict:
        """Get file content from a repository.

        Args:
            repo:   Repository in "owner/name" format.
            path:   File path within the repository.
            branch: Branch to read from.

        Returns:
            Dict with keys: path, content, sha, size.
        """
        result = await self._request("GET", f"repos/{repo}/contents/{path}?ref={branch}")
        content = base64.b64decode(result["content"]).decode("utf-8")
        return {
            "path": result["path"],
            "content": content,
            "sha": result["sha"],
            "size": result["size"],
        }

    async def create_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str = "",
        branch: str = "main",
    ) -> Dict:
        """Create a new file in the repository.

        Returns:
            Dict with keys: path, sha.
        """
        if not message:
            message = f"Create {path}"
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        result = await self._request("PUT", f"repos/{repo}/contents/{path}", data)
        return {"path": result["content"]["path"], "sha": result["content"]["sha"]}

    async def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str = "",
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> Dict:
        """Update an existing file. If sha is not provided, fetches it first.

        Returns:
            Dict with keys: path, sha.
        """
        if not message:
            message = f"Update {path}"
        if not sha:
            current = await self.get_file(repo, path, branch)
            sha = current["sha"]

        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
            "sha": sha,
        }
        result = await self._request("PUT", f"repos/{repo}/contents/{path}", data)
        return {"path": result["content"]["path"], "sha": result["content"]["sha"]}

    async def delete_file(
        self,
        repo: str,
        path: str,
        message: str = "",
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> bool:
        """Delete a file from the repository.

        Returns:
            True on success.
        """
        if not message:
            message = f"Delete {path}"
        if not sha:
            current = await self.get_file(repo, path, branch)
            sha = current["sha"]

        data = {"message": message, "sha": sha, "branch": branch}
        await self._request("DELETE", f"repos/{repo}/contents/{path}", data)
        return True

    # -- Branch Operations --------------------------------------------------

    async def list_branches(self, repo: str) -> List[Dict]:
        """List branches for a repository.

        Returns:
            List of dicts with keys: name, sha, protected.
        """
        result = await self._request("GET", f"repos/{repo}/branches?per_page=100")
        return [
            {
                "name": b["name"],
                "sha": b["commit"]["sha"],
                "protected": b.get("protected", False),
            }
            for b in result
        ]

    async def create_branch(self, repo: str, branch: str, base: str = "main") -> Dict:
        """Create a new branch from a base branch.

        Returns:
            Dict with keys: ref, sha.
        """
        ref_result = await self._request("GET", f"repos/{repo}/git/refs/heads/{base}")
        sha = ref_result["object"]["sha"]
        result = await self._request(
            "POST",
            f"repos/{repo}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": sha},
        )
        return {"ref": result["ref"], "sha": result["object"]["sha"]}

    async def delete_branch(self, repo: str, branch: str) -> bool:
        """Delete a branch.

        Returns:
            True on success.
        """
        await self._request("DELETE", f"repos/{repo}/git/refs/heads/{branch}")
        return True

    # -- Code Search --------------------------------------------------------

    async def search_code(self, query: str, per_page: int = 30) -> List[Dict]:
        """Search code across GitHub.

        Args:
            query:    Search query (supports GitHub search syntax).
            per_page: Number of results.

        Returns:
            List of dicts with keys: name, path, repo, html_url.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/search/code"
        async with session.get(url, params={"q": query, "per_page": str(per_page)}) as resp:
            result = await resp.json()
        return [
            {
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "repo": item.get("repository", {}).get("full_name", ""),
                "html_url": item.get("html_url", ""),
            }
            for item in result.get("items", [])
        ]

    async def search_repos(self, query: str, sort: str = "stars", per_page: int = 30) -> List[Dict]:
        """Search repositories on GitHub.

        Args:
            query:    Search query.
            sort:     Sort field (stars, forks, updated).
            per_page: Number of results.

        Returns:
            List of dicts with keys: full_name, description, stars, url.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/search/repositories"
        async with session.get(url, params={"q": query, "sort": sort, "per_page": str(per_page)}) as resp:
            result = await resp.json()
        return [
            {
                "full_name": item.get("full_name", ""),
                "description": item.get("description", ""),
                "stars": item.get("stargazers_count", 0),
                "url": item.get("html_url", ""),
            }
            for item in result.get("items", [])
        ]

    # -- Commit Operations --------------------------------------------------

    async def list_commits(self, repo: str, branch: str = "main", path: str = "", per_page: int = 50) -> List[Dict]:
        """List commits for a repository.

        Returns:
            List of dicts with keys: sha, message, author, date.
        """
        endpoint = f"repos/{repo}/commits?sha={branch}&per_page={per_page}"
        if path:
            endpoint += f"&path={path}"
        result = await self._request("GET", endpoint)
        return [
            {
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
            for c in result
        ]

    async def get_commit(self, repo: str, sha: str) -> Dict:
        """Get commit details.

        Returns:
            Dict with commit details.
        """
        result = await self._request("GET", f"repos/{repo}/commits/{sha}")
        return {
            "sha": result["sha"],
            "message": result["commit"]["message"],
            "author": result["commit"]["author"]["name"],
            "date": result["commit"]["author"]["date"],
            "files_changed": len(result.get("files", [])),
        }