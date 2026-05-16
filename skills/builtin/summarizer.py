"""
Aethera AI - Summarizer Skill

Summarize documents, URLs, meetings, and any text content.
Uses LLM for high-quality abstractive summarization with fallback to extractive.
"""

import os
from typing import Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@skill(name="summarizer", category="general")
class SummarizerSkill(AetheraSkill):
    """
    Summarize any content: documents, URLs, meeting transcripts, articles.
    Uses LLM for abstractive summarization when available.
    """

    @property
    def name(self) -> str:
        return "summarizer"

    @property
    def description(self) -> str:
        return "Summarize documents, URLs, meetings, or any text content"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text content to summarize"
                },
                "url": {
                    "type": "string",
                    "description": "URL to fetch and summarize"
                },
                "length": {
                    "type": "string",
                    "enum": ["brief", "medium", "detailed"],
                    "description": "Desired summary length",
                    "default": "medium"
                },
                "format": {
                    "type": "string",
                    "enum": ["paragraph", "bullets", "executive"],
                    "description": "Summary format",
                    "default": "paragraph"
                },
                "focus": {
                    "type": "string",
                    "description": "Specific aspect to focus the summary on"
                }
            }
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"content": "Long text here...", "length": "brief"}},
            {"input": {"url": "https://example.com/article", "format": "bullets"}},
            {"input": {"content": "Meeting transcript...", "format": "executive", "focus": "action items"}},
        ]

    @property
    def cache_ttl(self) -> int:
        return 300  # 5 minutes

    async def execute(self, **kwargs) -> SkillResult:
        content = kwargs.get("content", "")
        url = kwargs.get("url", "")
        length = kwargs.get("length", "medium")
        format_type = kwargs.get("format", "paragraph")
        focus = kwargs.get("focus", "")

        if not content and not url:
            return SkillResult(success=False, error="Either content or url is required")

        try:
            # If URL provided, fetch content first
            if url and not content:
                content = await self._fetch_url(url)

            # Try LLM summarization first, fallback to extractive
            summary = await self._llm_summarize(content, length, format_type, focus)
            if summary is None:
                summary = self._extractive_summary(content, length, format_type)

            return SkillResult(
                success=True,
                data={
                    "summary": summary,
                    "original_length": len(content),
                    "summary_length": len(summary),
                    "method": "llm" if summary else "extractive"
                }
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    async def _fetch_url(self, url: str) -> str:
        """Fetch content from URL."""
        if not HAS_HTTPX:
            return f"[Cannot fetch URL: httpx not installed] {url}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            # Simple text extraction — strip HTML tags
            text = response.text
            if "<html" in text.lower():
                import re
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            return text[:50000]

    async def _llm_summarize(self, content: str, length: str, format_type: str, focus: str) -> Optional[str]:
        """Attempt LLM-backed summarization via LiteLLM proxy."""
        litellm_url = os.environ.get("LITELLM_URL", "http://litellm:4000")
        litellm_key = os.environ.get("LITELLM_MASTER_KEY", "")

        if not HAS_HTTPX:
            return None

        # Truncate content to fit context window
        max_input = 12000 if length == "brief" else 20000 if length == "medium" else 30000
        truncated = content[:max_input]

        # Build prompt
        length_instructions = {
            "brief": "Provide a concise 2-3 sentence summary.",
            "medium": "Provide a comprehensive summary in 1-2 paragraphs.",
            "detailed": "Provide a detailed summary covering all key points in 3-5 paragraphs."
        }
        format_instructions = {
            "paragraph": "Write in paragraph form.",
            "bullets": "Use bullet points for each key point.",
            "executive": "Write an executive summary with a bold heading, key findings, and recommendations."
        }

        prompt_parts = [
            length_instructions.get(length, length_instructions["medium"]),
            format_instructions.get(format_type, format_instructions["paragraph"]),
        ]
        if focus:
            prompt_parts.append(f"Focus specifically on: {focus}")

        system_prompt = "You are a precise summarizer. " + " ".join(prompt_parts)
        user_prompt = f"Summarize the following:\n\n{truncated}"

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if litellm_key:
                    headers["Authorization"] = f"Bearer {litellm_key}"

                resp = await client.post(
                    f"{litellm_url}/chat/completions",
                    json={
                        "model": os.environ.get("SUMMARIZER_MODEL", "aethera-local-fast"),
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1024 if length == "brief" else 2048
                    },
                    headers=headers,
                    timeout=60
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                return None
        except Exception:
            return None

    def _extractive_summary(self, content: str, length: str, format_type: str) -> str:
        """Fallback extractive summarization when LLM is unavailable."""
        if not content:
            return "No content to summarize."

        # Split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content.replace("\n", " "))
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]

        if not sentences:
            # If no sentence breaks found, split by length
            chunk = content[:500]
            sentences = [chunk]

        # Determine number of sentences based on length
        length_map = {"brief": 3, "medium": 7, "detailed": 15}
        num_sentences = length_map.get(length, 7)

        # Score sentences by position and keyword density
        scored = []
        for i, s in enumerate(sentences):
            score = 0
            # Position bonus: first and last sentences are important
            if i < 3:
                score += 3
            if i == len(sentences) - 1:
                score += 1
            # Length preference: medium-length sentences
            if 40 < len(s) < 200:
                score += 2
            # Contains key phrases
            key_phrases = ["conclusion", "result", "found", "significant", "important",
                          "key", "main", "overall", "summary", "finding", "recommendation",
                          "however", "therefore", "notably", "specifically"]
            for phrase in key_phrases:
                if phrase in s.lower():
                    score += 1
            scored.append((score, i, s))

        # Select top sentences, then sort by original order
        scored.sort(key=lambda x: (-x[0], x[1]))
        selected = sorted(scored[:num_sentences], key=lambda x: x[1])
        summary_sentences = [s[2] for s in selected]

        if format_type == "bullets":
            return "\n".join(f"  • {s}" for s in summary_sentences)
        elif format_type == "executive":
            return f"**Executive Summary**\n\n" + "\n\n".join(summary_sentences)
        else:
            return " ".join(summary_sentences)