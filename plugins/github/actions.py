"""
GitHub Actions Manager for Aethera

Provides CI/CD workflow status and management operations
via the GitHub REST API v3.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class ActionsManager:
    """Manage GitHub Actions workflows and runs."""

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

    # -- Workflow Management ------------------------------------------------

    async def list_workflows(self, repo: str) -> List[Dict]:
        """List all GitHub Actions workflows for a repository.

        Args:
            repo: Repository in "owner/name" format.

        Returns:
            List of dicts with keys: id, name, state, path, created_at.
        """
        result = await self._request("GET", f"repos/{repo}/actions/workflows")
        workflows = result.get("workflows", [])
        return [
            {
                "id": w["id"],
                "name": w.get("name", ""),
                "state": w.get("state", ""),
                "path": w.get("path", ""),
                "created_at": w.get("created_at", ""),
            }
            for w in workflows
        ]

    async def get_workflow(self, repo: str, workflow_id: str) -> Dict:
        """Get a specific workflow.

        Args:
            repo:        Repository in "owner/name" format.
            workflow_id: Workflow ID or filename.

        Returns:
            Dict with workflow details.
        """
        result = await self._request("GET", f"repos/{repo}/actions/workflows/{workflow_id}")
        return {
            "id": result["id"],
            "name": result.get("name", ""),
            "state": result.get("state", ""),
            "path": result.get("path", ""),
            "created_at": result.get("created_at", ""),
            "updated_at": result.get("updated_at", ""),
        }

    async def enable_workflow(self, repo: str, workflow_id: str) -> bool:
        """Enable a workflow.

        Returns:
            True on success.
        """
        await self._request("PUT", f"repos/{repo}/actions/workflows/{workflow_id}/enable")
        return True

    async def disable_workflow(self, repo: str, workflow_id: str) -> bool:
        """Disable a workflow.

        Returns:
            True on success.
        """
        await self._request("PUT", f"repos/{repo}/actions/workflows/{workflow_id}/disable")
        return True

    # -- Workflow Runs -------------------------------------------------------

    async def list_workflow_runs(
        self,
        repo: str,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        branch: Optional[str] = None,
        per_page: int = 30,
    ) -> List[Dict]:
        """List workflow runs, optionally filtered by workflow, status, or branch.

        Args:
            repo:        Repository in "owner/name" format.
            workflow_id: Optional workflow ID or filename to filter.
            status:      Optional status filter: queued, in_progress, completed.
            branch:      Optional branch filter.
            per_page:    Number of results.

        Returns:
            List of dicts with keys: id, name, status, conclusion, head_branch, created_at.
        """
        if workflow_id:
            endpoint = f"repos/{repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"repos/{repo}/actions/runs"

        params = f"per_page={per_page}"
        if status:
            params += f"&status={status}"
        if branch:
            params += f"&branch={branch}"

        result = await self._request("GET", f"{endpoint}?{params}")
        runs = result.get("workflow_runs", [])
        return [
            {
                "id": r["id"],
                "name": r.get("name", ""),
                "status": r.get("status", ""),
                "conclusion": r.get("conclusion", ""),
                "head_branch": r.get("head_branch", ""),
                "created_at": r.get("created_at", ""),
                "updated_at": r.get("updated_at", ""),
            }
            for r in runs
        ]

    async def get_workflow_run(self, repo: str, run_id: int) -> Dict:
        """Get details of a specific workflow run.

        Returns:
            Dict with run details.
        """
        result = await self._request("GET", f"repos/{repo}/actions/runs/{run_id}")
        return {
            "id": result["id"],
            "name": result.get("name", ""),
            "status": result.get("status", ""),
            "conclusion": result.get("conclusion", ""),
            "head_branch": result.get("head_branch", ""),
            "head_sha": result.get("head_sha", ""),
            "created_at": result.get("created_at", ""),
            "updated_at": result.get("updated_at", ""),
            "url": result.get("html_url", ""),
        }

    async def re_run_workflow(self, repo: str, run_id: int) -> bool:
        """Re-run a workflow.

        Returns:
            True on success.
        """
        await self._request("POST", f"repos/{repo}/actions/runs/{run_id}/rerun")
        return True

    async def cancel_workflow_run(self, repo: str, run_id: int) -> bool:
        """Cancel a workflow run.

        Returns:
            True on success.
        """
        await self._request("POST", f"repos/{repo}/actions/runs/{run_id}/cancel")
        return True

    async def delete_workflow_run(self, repo: str, run_id: int) -> bool:
        """Delete a workflow run.

        Returns:
            True on success.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/repos/{repo}/actions/runs/{run_id}"
        async with session.delete(url) as resp:
            return resp.status == 204

    # -- Workflow Dispatch ---------------------------------------------------

    async def trigger_workflow(
        self,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Trigger a workflow dispatch event.

        Args:
            repo:        Repository in "owner/name" format.
            workflow_id: Workflow ID or filename.
            ref:         Branch or tag ref to run on.
            inputs:      Optional workflow input parameters.

        Returns:
            True on success.
        """
        data: Dict[str, Any] = {"ref": ref}
        if inputs:
            data["inputs"] = inputs

        await self._request(
            "POST",
            f"repos/{repo}/actions/workflows/{workflow_id}/dispatches",
            data,
        )
        return True

    # -- Jobs ---------------------------------------------------------------

    async def list_jobs(self, repo: str, run_id: int) -> List[Dict]:
        """List jobs for a workflow run.

        Returns:
            List of job dicts.
        """
        result = await self._request("GET", f"repos/{repo}/actions/runs/{run_id}/jobs")
        jobs = result.get("jobs", [])
        return [
            {
                "id": j["id"],
                "name": j.get("name", ""),
                "status": j.get("status", ""),
                "conclusion": j.get("conclusion", ""),
                "started_at": j.get("started_at", ""),
                "completed_at": j.get("completed_at", ""),
            }
            for j in jobs
        ]

    async def get_job_logs(self, repo: str, job_id: int) -> str:
        """Get logs for a specific job.

        Returns:
            Log content as text.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/repos/{repo}/actions/jobs/{job_id}/logs"
        async with session.get(url) as resp:
            if resp.status == 302:
                # Follow redirect to log location
                location = resp.headers.get("Location", "")
                if location:
                    async with session.get(location) as log_resp:
                        return await log_resp.text()
            return await resp.text()

    # -- Artifacts -----------------------------------------------------------

    async def list_artifacts(self, repo: str, per_page: int = 30) -> List[Dict]:
        """List artifacts for a repository.

        Returns:
            List of artifact dicts.
        """
        result = await self._request("GET", f"repos/{repo}/actions/artifacts?per_page={per_page}")
        artifacts = result.get("artifacts", [])
        return [
            {
                "id": a["id"],
                "name": a.get("name", ""),
                "size_in_bytes": a.get("size_in_bytes", 0),
                "expired": a.get("expired", False),
                "created_at": a.get("created_at", ""),
            }
            for a in artifacts
        ]

    async def download_artifact(self, repo: str, artifact_id: int) -> bytes:
        """Download an artifact as a zip archive.

        Returns:
            Artifact zip content as bytes.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/repos/{repo}/actions/artifacts/{artifact_id}/zip"
        async with session.get(url) as resp:
            return await resp.read()