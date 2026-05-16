"""
Aethera AI — Stage 5: Fact Extractor

Extracts verified facts from document text using heuristic patterns
and optional LLM structured extraction. Stores facts in FactStore
with source attribution and confidence scores.
"""
import re
import logging
from typing import List

from .stages import PipelineStage
from .context import PipelineContext, ExtractedFact

logger = logging.getLogger("aethera.pipeline.facts")

# Heuristic fact indicator patterns
FACT_INDICATORS = [
    re.compile(r"(?i)(?:is|are|was|were|has|have|had|requires|indicates|means|equals|consists of|defined as|refers to)\s", re.IGNORECASE),
    re.compile(r"\b(?:diagnosed|prescribed|approved|denied|covered|excluded|reimbursed|billed)\b", re.IGNORECASE),
    re.compile(r"\$[\d,]+(?:\.\d{2})?"),  # Dollar amounts
    re.compile(r"\b(?:effective|valid from|expires|deadline|due date)\b.*\d", re.IGNORECASE),
]

# Minimum sentence length for a fact candidate
MIN_FACT_LENGTH = 20
MAX_FACT_LENGTH = 500


class FactExtractor(PipelineStage):
    """Stage 5: Extract and store facts from document content."""

    name = "facts"

    @property
    def depends_on(self) -> list:
        return ["extractor"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        text = context.raw_text
        if not text:
            return context

        # Heuristic extraction
        heuristic_facts = self._extract_heuristic_facts(text, context)

        # LLM extraction (if sensitivity-safe)
        llm_facts = []
        if context.sensitivity in ("public", "internal"):
            llm_facts = await self._extract_llm_facts(text, context)

        # Merge facts
        all_facts = self._merge_facts(heuristic_facts, llm_facts)

        # Filter by confidence
        all_facts = [f for f in all_facts if f.confidence >= 0.4]

        # Store in FactStore
        fact_ids = await self._store_facts(all_facts, context)

        context.extracted_facts = all_facts
        context.fact_ids = fact_ids

        logger.info(f"Extracted {len(all_facts)} facts ({len(heuristic_facts)} heuristic, {len(llm_facts)} LLM)")
        return context

    def _extract_heuristic_facts(self, text: str, context: PipelineContext) -> List[ExtractedFact]:
        """Extract facts using heuristic pattern matching."""
        facts = []
        seen = set()

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < MIN_FACT_LENGTH or len(sentence) > MAX_FACT_LENGTH:
                continue

            # Check if sentence contains factual indicators
            is_factual = False
            for pattern in FACT_INDICATORS:
                if pattern.search(sentence):
                    is_factual = True
                    break

            if not is_factual:
                continue

            # Deduplicate
            key = sentence.lower()[:80]
            if key in seen:
                continue
            seen.add(key)

            # Determine category
            category = context.domain
            if context.domain == "general":
                category = self._infer_category(sentence)

            facts.append(ExtractedFact(
                fact_text=sentence,
                category=category,
                confidence=0.6,  # Heuristic confidence
                tags=self._extract_tags(sentence),
                source=context.filename or context.file_path or context.url,
                source_type="document",
            ))

        return facts[:100]  # Cap at 100 facts

    def _infer_category(self, sentence: str) -> str:
        """Infer fact category from sentence content."""
        s = sentence.lower()
        if any(w in s for w in ("icd", "cpt", "hcpcs", "diagnosis", "procedure code")):
            return "coding"
        if any(w in s for w in ("claim", "denial", "appeal", "reimbursement")):
            return "claims"
        if any(w in s for w in ("drug", "medication", "prescription", "formulary")):
            return "pharmacy"
        if any(w in s for w in ("covered", "benefit", "eligibility", "payer")):
            return "coverage"
        if any(w in s for w in ("revenue", "expense", "payment", "billing")):
            return "finance"
        return "general"

    def _extract_tags(self, sentence: str) -> List[str]:
        """Extract potential tag keywords from a sentence."""
        tags = []
        # Extract capitalized terms (potential proper nouns)
        for match in re.finditer(r'\b[A-Z][a-zA-Z]{2,}\b', sentence):
            word = match.group()
            if word not in ("The", "This", "That", "These", "Those", "When", "Where",
                          "Which", "What", "How", "Why", "And", "But", "For", "Not",
                          "With", "From", "Into", "Each", "All", "Any", "Has", "Have"):
                tags.append(word)
        return tags[:5]

    async def _extract_llm_facts(self, text: str, context: PipelineContext) -> List[ExtractedFact]:
        """Extract facts using LLM structured output."""
        facts = []
        excerpt = text[:4000]

        prompt = (
            "Extract factual statements from this text. Return a JSON array where each item has: "
            '"fact_text" (the factual statement), "category" (one of: coding, claims, pharmacy, '
            'coverage, finance, regulation, general), "confidence" (0.0-1.0), '
            '"tags" (array of relevant keywords). Only extract clear, verifiable facts.\n\n'
            f"Text:\n{excerpt}\n\nFacts:"
        )

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "qwen3.5:4b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                if response.status_code == 200:
                    content = response.json().get("message", {}).get("content", "")
                    facts = self._parse_llm_facts(content, context)
        except Exception as e:
            logger.debug(f"LLM fact extraction unavailable: {e}")

        return facts

    def _parse_llm_facts(self, content: str, context: PipelineContext) -> List[ExtractedFact]:
        """Parse LLM response into ExtractedFact objects."""
        import json
        facts = []

        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                arr = json.loads(content[start:end])
                for item in arr[:50]:
                    if isinstance(item, dict) and "fact_text" in item:
                        facts.append(ExtractedFact(
                            fact_text=item["fact_text"][:MAX_FACT_LENGTH],
                            category=item.get("category", context.domain),
                            confidence=min(1.0, max(0.0, float(item.get("confidence", 0.5)))),
                            tags=item.get("tags", []),
                            source=context.filename or context.file_path or context.url,
                            source_type="document",
                        ))
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"LLM fact parse failed: {e}")

        return facts

    def _merge_facts(self, heuristic: List[ExtractedFact],
                     llm: List[ExtractedFact]) -> List[ExtractedFact]:
        """Merge heuristic and LLM facts, deduplicating by text similarity."""
        seen = set()
        merged = []

        for fact in heuristic + llm:
            key = fact.fact_text.lower()[:60]
            if key not in seen:
                seen.add(key)
                merged.append(fact)

        return merged

    async def _store_facts(self, facts: List[ExtractedFact],
                           context: PipelineContext) -> List[str]:
        """Store extracted facts in the FactStore."""
        if not facts:
            return []

        try:
            from memory.fact_store import get_fact_store
            store = get_fact_store()
            if not store._conn:
                store.initialize()

            fact_dicts = [
                {
                    "fact_text": f.fact_text,
                    "source": f.source,
                    "source_type": f.source_type,
                    "confidence": f.confidence,
                    "category": f.category,
                    "tags": f.tags,
                }
                for f in facts
            ]
            return store.store_facts_batch(fact_dicts)

        except Exception as e:
            logger.error(f"FactStore write failed: {e}")
            return []