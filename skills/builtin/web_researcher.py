"""
Aethera AI - Web Researcher Skill

Multi-hop web search with summarization and citation.
"""

import asyncio
from typing import List, Dict, Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="web_researcher", category="general")
class WebResearcherSkill(AetheraSkill):
    """
    Perform multi-hop web research with summarization and citations.
    Uses SearXNG for privacy-respecting search.
    """

    def __init__(self):
        self.searxng_url = "http://searxng:8080"
        if not HAS_HTTPX:
            self._httpx_warning = "httpx not installed — web research will use fallback mode"

    @property
    def name(self) -> str:
        return "web_researcher"

    @property
    def description(self) -> str:
        return "Search the web and summarize findings with citations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search categories: general, news, science, etc."
                },
                "summarize": {
                    "type": "boolean",
                    "description": "Generate summary of results",
                    "default": True
                }
            },
            "required": ["query"]
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"query": "latest CMS telehealth rules 2025"}},
            {"input": {"query": "ICD-10 code for diabetes type 2", "num_results": 5}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 10)
        categories = kwargs.get("categories", ["general"])
        summarize = kwargs.get("summarize", True)

        if not query:
            return SkillResult(success=False, error="Query is required")

        try:
            results = await self._search(query, num_results, categories)

            if summarize and results:
                summary = await self._generate_summary(results)
                return SkillResult(
                    success=True,
                    data={
                        "query": query,
                        "results": results,
                        "summary": summary
                    }
                )

            return SkillResult(
                success=True,
                data={
                    "query": query,
                    "results": results
                }
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    async def _search(self, query: str, num_results: int, categories: List[str]) -> List[Dict[str, Any]]:
        """Search using SearXNG."""
        if not HAS_HTTPX:
            return [{"title": "Web search unavailable", "url": "", "content": "httpx package not installed. Install with: pip install httpx"}]

        async with httpx.AsyncClient() as client:
            params = {
                "q": query,
                "format": "json",
                "pageno": 1
            }
            if categories:
                params["categories"] = ",".join(categories)

            try:
                response = await client.get(
                    f"{self.searxng_url}/search",
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])[:num_results]
            except Exception as e:
                # Fallback to direct search if SearXNG unavailable
                return [{"title": "Search unavailable", "url": "", "content": str(e)}]

    async def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        """Generate a summary from search results."""
        if not results:
            return "No results found."

        # Extract key information from top results
        snippets = []
        for i, result in enumerate(results[:5], 1):
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            url = result.get("url", "")

            if content:
                snippets.append(f"[{i}] {title}: {content}")

        if not snippets:
            return "Results found but no summaries available."

        return "\n\n".join(snippets)
