"""
Aethera AI — Data Intelligence LLM Helper

Thin async wrapper for calling Ollama (qwen3.5:4b) via the LiteLLM proxy
for data annotation and schema detection.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aethera.data_intelligence.llm")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "qwen3.5:4b"


class DataIntelligenceLLM:
    """Async LLM wrapper for data annotation and schema detection."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        litellm_url: Optional[str] = None,
        litellm_key: Optional[str] = None,
    ):
        self.model = model
        self.litellm_url = litellm_url or LITELLM_URL
        self.litellm_key = litellm_key or LITELLM_KEY

    async def annotate_row(
        self,
        row: Dict[str, Any],
        annotation_types: List[str],
        domain_hint: str = "general",
    ) -> Dict[str, Any]:
        """
        Annotate a single data row using LLM.

        Args:
            row: The data row to annotate
            annotation_types: Types of annotations to generate
                             ('category', 'sentiment', 'entity', 'relationship')
            domain_hint: Domain context (e.g. 'healthcare', 'finance')

        Returns:
            Dict with annotation_type -> annotation_value pairs
        """
        type_descriptions = {
            "category": "Classify this row into a category (e.g., healthcare, finance, technology, legal, general)",
            "sentiment": "Rate the sentiment of this row: positive, negative, or neutral, with a confidence score 0-1",
            "entity": "Extract named entities: people, organizations, locations, dates, amounts, codes",
            "relationship": "Extract subject-predicate-object triples between entities in this row",
        }

        requested = {t: type_descriptions[t] for t in annotation_types if t in type_descriptions}
        if not requested:
            return {}

        prompt = (
            f"You are a data annotation assistant for {domain_hint} data.\n"
            f"For the following data row, provide these annotations as JSON:\n\n"
        )
        for ann_type, desc in requested.items():
            prompt += f"- {ann_type}: {desc}\n"

        prompt += f"\nData row:\n{json.dumps(row, default=str)}\n\n"
        prompt += "Return ONLY valid JSON with the annotation types as keys."

        return await self._call_llm(prompt)

    async def detect_schema(
        self,
        sample_rows: List[Dict[str, Any]],
        headers: List[str],
    ) -> Dict[str, Any]:
        """
        Detect schema information from a sample of rows.

        Returns dict with column type suggestions, primary key candidates,
        and foreign key hints.
        """
        prompt = (
            "Analyze this data sample and infer the schema. Return ONLY valid JSON with:\n"
            "- columns: list of {name, type, nullable, sample_values}\n"
            "- primary_key_candidates: list of column names that could be primary keys\n"
            "- foreign_key_hints: list of {column, references} pairs\n\n"
            f"Headers: {headers}\n"
            f"Sample rows (first 5):\n{json.dumps(sample_rows[:5], default=str)}\n"
        )

        return await self._call_llm(prompt)

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Make an async LLM call and parse JSON response."""
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not available for LLM calls")
            return {}

        headers = {"Content-Type": "application/json"}
        if self.litellm_key:
            headers["Authorization"] = f"Bearer {self.litellm_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a data analysis assistant. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.litellm_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning(f"LLM call failed: HTTP {resp.status_code}")
                    return {}

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # Strip markdown code fences
                content = re.sub(r"^```(?:json)?\s*", "", content.strip())
                content = re.sub(r"\s*```$", "", content.strip())

                return json.loads(content)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"LLM response parse error: {e}")
            return {}
        except Exception as e:
            logger.warning(f"LLM call error: {e}")
            return {}