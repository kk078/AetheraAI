"""
Cloudflare Pages Manager for Aethera

Provides Pages project deployment operations via the Cloudflare API v4.
"""
from typing import Any, Dict, List, Optional

import aiohttp


class PagesManager:
    """Manage Cloudflare Pages projects and deployments."""

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

    async def list_projects(self) -> List[Dict]:
        """List all Pages projects.

        Returns:
            List of dicts with keys: id, name, subdomain, domains, created_on.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/pages/projects"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": p["id"],
                "name": p["name"],
                "subdomain": p.get("subdomain", ""),
                "domains": p.get("domains", []),
                "created_on": p.get("created_on", ""),
            }
            for p in result.get("result", [])
        ]

    async def get_project(self, project_name: str) -> Dict:
        """Get details for a Pages project.

        Returns:
            Dict with project details.
        """
        result = await self._request(
            "GET",
            f"accounts/{self.account_id}/pages/projects/{project_name}",
        )
        return {
            "id": result["id"],
            "name": result["name"],
            "subdomain": result.get("subdomain", ""),
            "domains": result.get("domains", []),
            "created_on": result.get("created_on", ""),
            "production_branch": result.get("production_branch", "main"),
            "build_config": result.get("build_config", {}),
        }

    async def create_project(
        self,
        name: str,
        production_branch: str = "main",
        build_config: Optional[Dict] = None,
        source: Optional[Dict] = None,
    ) -> Dict:
        """Create a new Pages project.

        Args:
            name:              Project name (must be unique per account).
            production_branch: Default branch for production deploys.
            build_config:      Build configuration dict (build_command, destination_dir, etc.).
            source:            Source integration dict (type, repo, owner, etc.).

        Returns:
            Dict with keys: id, name, subdomain.
        """
        data: Dict[str, Any] = {
            "name": name,
            "production_branch": production_branch,
        }
        if build_config:
            data["build_config"] = build_config
        if source:
            data["source"] = source

        result = await self._request(
            "POST",
            f"accounts/{self.account_id}/pages/projects",
            data,
        )
        return {
            "id": result["id"],
            "name": result["name"],
            "subdomain": result.get("subdomain", ""),
        }

    async def delete_project(self, project_name: str) -> bool:
        """Delete a Pages project.

        Returns:
            True on success.
        """
        await self._request(
            "DELETE",
            f"accounts/{self.account_id}/pages/projects/{project_name}",
        )
        return True

    async def list_deployments(self, project_name: str) -> List[Dict]:
        """List deployments for a Pages project.

        Returns:
            List of deployment dicts.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/pages/projects/{project_name}/deployments"
        async with session.get(url) as resp:
            result = await resp.json()
            if not result.get("success", False):
                errors = result.get("errors", [{"message": "Unknown error"}])
                raise Exception(f"Cloudflare API error: {errors[0]['message']}")

        return [
            {
                "id": d["id"],
                "environment": d.get("environment", ""),
                "status": d.get("latest_stage", {}).get("name", ""),
                "url": d.get("url", ""),
                "created_on": d.get("created_on", ""),
                "source": d.get("source", {}),
            }
            for d in result.get("result", [])
        ]

    async def get_deployment(self, project_name: str, deployment_id: str) -> Dict:
        """Get details for a specific deployment.

        Returns:
            Dict with deployment details.
        """
        result = await self._request(
            "GET",
            f"accounts/{self.account_id}/pages/projects/{project_name}/deployments/{deployment_id}",
        )
        return {
            "id": result["id"],
            "environment": result.get("environment", ""),
            "status": result.get("latest_stage", {}).get("name", ""),
            "url": result.get("url", ""),
            "created_on": result.get("created_on", ""),
            "stages": result.get("stages", []),
            "build_log": result.get("build_log", ""),
        }

    async def create_deployment(
        self,
        project_name: str,
        branch: str = "main",
        commit_hash: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> Dict:
        """Create a new deployment (trigger a deploy hook or direct upload).

        For Git-integrated projects, this triggers a redeployment.
        For direct-upload projects, use `upload_directory` instead.

        Args:
            project_name:  Target Pages project.
            branch:        Branch to deploy.
            commit_hash:   Optional commit hash.
            commit_message: Optional commit message.

        Returns:
            Dict with deployment details.
        """
        data: Dict[str, Any] = {"branch": branch}
        if commit_hash:
            data["commit_hash"] = commit_hash
        if commit_message:
            data["commit_message"] = commit_message

        result = await self._request(
            "POST",
            f"accounts/{self.account_id}/pages/projects/{project_name}/deployments",
            data,
        )
        return {
            "id": result["id"],
            "url": result.get("url", ""),
            "environment": result.get("environment", ""),
        }

    async def upload_directory(
        self,
        project_name: str,
        directory_path: str,
        branch: str = "main",
    ) -> Dict:
        """Upload a directory for a direct-upload Pages deployment.

        This uses the Cloudflare Direct Upload API. The caller must provide
        a valid local directory path; the manager reads and uploads it.

        Args:
            project_name:  Target Pages project.
            directory_path: Local path to the directory to upload.
            branch:        Branch name for the deployment.

        Returns:
            Dict with upload/deployment details.
        """
        import os
        import zipfile
        import tempfile

        # Zip the directory
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, directory_path)
                        zf.write(file_path, arcname)

            session = await self._ensure_session()
            url = (
                f"{self.BASE_URL}/accounts/{self.account_id}"
                f"/pages/projects/{project_name}/deployments"
            )
            data = aiohttp.FormData()
            with open(tmp_path, "rb") as f:
                data.add_field("directory", f, filename="directory.zip")
            data.add_field("branch", branch)

            # Override content-type for multipart
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with session.post(url, data=data, headers=headers) as resp:
                result = await resp.json()
                if not result.get("success", False):
                    errors = result.get("errors", [{"message": "Unknown error"}])
                    raise Exception(f"Upload failed: {errors[0]['message']}")
                return result.get("result", {})
        finally:
            import os as _os
            _os.unlink(tmp_path)

    async def rollback_deployment(self, project_name: str, deployment_id: str) -> Dict:
        """Rollback to a previous deployment (promote it to production).

        Args:
            project_name:  Target Pages project.
            deployment_id: Deployment ID to promote.

        Returns:
            Dict with rollback status.
        """
        result = await self._request(
            "POST",
            f"accounts/{self.account_id}/pages/projects/{project_name}"
            f"/deployments/{deployment_id}/rollback",
        )
        return {"status": "rolled_back", "deployment_id": deployment_id}