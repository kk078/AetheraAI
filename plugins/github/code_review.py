"""
GitHub Code Review Manager for Aethera

Provides automated code review suggestions by analyzing PR diffs,
commit history, and code patterns via the GitHub REST API v3.
"""
import base64
import re
from typing import Any, Dict, List, Optional

import aiohttp


class CodeReviewManager:
    """Automated code review for GitHub pull requests."""

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
            return await resp.json()

    async def _get_text(self, url: str) -> str:
        """Fetch raw text content from a URL using the session headers."""
        session = await self._ensure_session()
        async with session.get(url) as resp:
            return await resp.text()

    # -- PR Diff Retrieval --------------------------------------------------

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the diff for a pull request.

        Returns:
            The PR diff as raw text.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/repos/{repo}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        async with session.get(url, headers=headers) as resp:
            return await resp.text()

    async def get_pr_files(self, repo: str, pr_number: int) -> List[Dict]:
        """Get the list of files changed in a PR.

        Returns:
            List of file dicts with keys: filename, status, additions, deletions, changes.
        """
        result = await self._request("GET", f"repos/{repo}/pulls/{pr_number}/files")
        return [
            {
                "filename": f["filename"],
                "status": f.get("status", ""),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "changes": f.get("changes", 0),
                "patch": f.get("patch", ""),
            }
            for f in result
        ]

    # -- Automated Review ----------------------------------------------------

    async def review_pr(self, repo: str, pr_number: int) -> Dict:
        """Perform an automated code review on a pull request.

        Analyzes the PR diff for common issues and returns suggestions.
        This does NOT post the review to GitHub; use `submit_review` for that.

        Returns:
            Dict with keys: suggestions, summary, stats.
        """
        files = await self.get_pr_files(repo, pr_number)
        suggestions: List[Dict[str, Any]] = []

        total_additions = 0
        total_deletions = 0

        for file_info in files:
            filename = file_info["filename"]
            patch = file_info.get("patch", "")
            additions = file_info.get("additions", 0)
            deletions = file_info.get("deletions", 0)
            total_additions += additions
            total_deletions += deletions

            # Analyze the patch for common issues
            file_suggestions = self._analyze_patch(filename, patch)
            suggestions.extend(file_suggestions)

        summary = self._generate_summary(files, total_additions, total_deletions, suggestions)

        return {
            "suggestions": suggestions,
            "summary": summary,
            "stats": {
                "files_changed": len(files),
                "total_additions": total_additions,
                "total_deletions": total_deletions,
                "suggestion_count": len(suggestions),
            },
        }

    def _analyze_patch(self, filename: str, patch: str) -> List[Dict[str, Any]]:
        """Analyze a file patch for common code review issues.

        Returns:
            List of suggestion dicts.
        """
        suggestions: List[Dict[str, Any]] = []
        lines = patch.split("\n") if patch else []

        for i, line in enumerate(lines):
            # Only check added lines (those starting with +)
            if not line.startswith("+") or line.startswith("+++"):
                continue

            # Check for potential secrets/credentials
            secret_patterns = [
                (r"(?i)(password|passwd|secret|token|api_key|apikey)\s*[=:]\s*['\"][^'\"]+['\"]", "potential_secret"),
                (r"(?i)(private_key|private-key)\s*[=:]\s*['\"]", "potential_secret"),
                (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "potential_secret"),
            ]
            for pattern, issue_type in secret_patterns:
                if re.search(pattern, line):
                    suggestions.append({
                        "file": filename,
                        "line_number": i + 1,
                        "severity": "critical",
                        "type": issue_type,
                        "message": "Potential secret or credential detected. Do not commit secrets to the repository.",
                    })

            # Check for debug/logging statements
            debug_patterns = [
                (r"console\.log\(", "debug_statement"),
                (r"print\s*\(", "debug_statement"),
                (r"debugger\s*;", "debug_statement"),
                (r"fmt\.Println\(", "debug_statement"),
            ]
            for pattern, issue_type in debug_patterns:
                if re.search(pattern, line):
                    suggestions.append({
                        "file": filename,
                        "line_number": i + 1,
                        "severity": "warning",
                        "type": issue_type,
                        "message": "Debug/logging statement found. Consider removing before merging.",
                    })

            # Check for TODO/FIXME/HACK comments
            todo_patterns = [
                (r"(?i)(TODO|FIXME|HACK|XXX|BUG)\b", "todo_comment"),
            ]
            for pattern, issue_type in todo_patterns:
                if re.search(pattern, line):
                    suggestions.append({
                        "file": filename,
                        "line_number": i + 1,
                        "severity": "info",
                        "type": issue_type,
                        "message": f"Found {issue_type.replace('_', ' ').upper()} comment. Consider addressing before merge.",
                    })

            # Check for large functions (heuristic: many consecutive + lines)
            # This is checked at file level below

        # Check for very large files
        if len(lines) > 500:
            suggestions.append({
                "file": filename,
                "line_number": 0,
                "severity": "warning",
                "type": "large_file",
                "message": f"Large file change ({len(lines)} lines). Consider breaking into smaller PRs.",
            })

        # Check for binary or generated files by extension
        generated_extensions = (".min.js", ".min.css", ".bundle.js", ".map", ".lock")
        if any(filename.endswith(ext) for ext in generated_extensions):
            suggestions.append({
                "file": filename,
                "line_number": 0,
                "severity": "warning",
                "type": "generated_file",
                "message": "Generated or minified file detected. These should typically not be committed directly.",
            })

        return suggestions

    def _generate_summary(
        self,
        files: List[Dict],
        additions: int,
        deletions: int,
        suggestions: List[Dict],
    ) -> str:
        """Generate a human-readable review summary."""
        critical = sum(1 for s in suggestions if s["severity"] == "critical")
        warnings = sum(1 for s in suggestions if s["severity"] == "warning")
        info = sum(1 for s in suggestions if s["severity"] == "info")

        parts = [
            f"Files changed: {len(files)}, +{additions}/-{deletions} lines.",
        ]
        if critical:
            parts.append(f"CRITICAL: {critical} issue(s) found (secrets/credentials).")
        if warnings:
            parts.append(f"Warnings: {warnings} suggestion(s) (debug code, large files, etc.).")
        if info:
            parts.append(f"Info: {info} note(s) (TODOs, FIXMEs, etc.).")
        if not suggestions:
            parts.append("No issues found. Code looks good!")

        return " ".join(parts)

    # -- Submit Review to GitHub ---------------------------------------------

    async def submit_review(
        self,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        suggestions: Optional[List[Dict]] = None,
    ) -> Dict:
        """Submit a code review to a GitHub pull request.

        Args:
            repo:        Repository in "owner/name" format.
            pr_number:   PR number.
            body:        Review body text.
            event:       Review event: APPROVE, REQUEST_CHANGES, COMMENT.
            suggestions: Optional list of inline comment dicts with
                         keys: path, line, message.

        Returns:
            Dict with keys: id, state.
        """
        # Determine review event based on suggestions
        if suggestions and event == "COMMENT":
            critical_count = sum(1 for s in suggestions if s.get("severity") == "critical")
            if critical_count > 0:
                event = "REQUEST_CHANGES"

        # Build inline comments from suggestions
        comments = []
        if suggestions:
            for s in suggestions:
                if s.get("file") and s.get("line_number", 0) > 0:
                    comments.append({
                        "path": s["file"],
                        "line": s["line_number"],
                        "side": "RIGHT",
                        "body": f"[{s.get('severity', 'info').upper()}] {s.get('message', '')}",
                    })

        data: Dict[str, Any] = {"body": body, "event": event}
        if comments:
            data["comments"] = comments

        result = await self._request(
            "POST",
            f"repos/{repo}/pulls/{pr_number}/reviews",
            data,
        )
        return {"id": result["id"], "state": result.get("state", "")}

    # -- Review Summary by PR ------------------------------------------------

    async def get_pr_review_status(self, repo: str, pr_number: int) -> Dict:
        """Get the current review status of a PR.

        Returns:
            Dict with review status details.
        """
        reviews = await self._request("GET", f"repos/{repo}/pulls/{pr_number}/reviews")
        approved = []
        changes_requested = []
        commented = []

        for r in reviews:
            user = r.get("user", {}).get("login", "")
            state = r.get("state", "")
            if state == "APPROVED":
                approved.append(user)
            elif state == "CHANGES_REQUESTED":
                changes_requested.append(user)
            elif state == "COMMENTED":
                commented.append(user)

        return {
            "approved": approved,
            "changes_requested": changes_requested,
            "commented": commented,
            "total_reviews": len(reviews),
        }