"""
Aethera AI — Stage 3: Entity Extractor

Identifies people, organizations, codes, dates, amounts, and other
entities from extracted text using regex patterns and optional LLM extraction.
"""
import re
import logging
from typing import List

from .stages import PipelineStage
from .context import PipelineContext, ExtractedEntity

logger = logging.getLogger("aethera.pipeline.entities")

# Regex patterns for structured entity extraction
ENTITY_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "npi": re.compile(r"\b\d{10}\b"),
    "icd10": re.compile(r"\b[A-Z]\d{2}(\.[A-Z0-9]{1,4})?\b"),
    "cpt": re.compile(r"\b\d{5}[A-Z]?\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "date": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b", re.IGNORECASE),
    "dollar_amount": re.compile(r"\$[\d,]+(?:\.\d{2})?\b"),
    "mrn": re.compile(r"\bMRN[:\s]?\d+\b", re.IGNORECASE),
    "dea": re.compile(r"\b[A-Z]\d{7}\b"),
}

# Map pattern keys to KnowledgeGraph entity types
PATTERN_TO_ENTITY_TYPE = {
    "npi": "person",
    "mrn": "person",
    "icd10": "condition",
    "cpt": "procedure",
    "dea": "person",
}


class EntityExtractor(PipelineStage):
    """Stage 3: Extract entities from text content."""

    name = "entities"

    @property
    def depends_on(self) -> list:
        return ["extractor"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        text = context.raw_text
        if not text:
            return context

        # Regex-based extraction
        regex_entities = self._extract_regex_entities(text)

        # LLM-based extraction (if available and sensitivity-safe)
        llm_entities = []
        if context.sensitivity in ("public", "internal"):
            llm_entities = await self._extract_llm_entities(text, context)

        # Merge and deduplicate
        all_entities = self._merge_entities(regex_entities, llm_entities)
        context.entities = all_entities

        logger.info(f"Extracted {len(all_entities)} entities ({len(regex_entities)} regex, {len(llm_entities)} LLM)")
        return context

    def _extract_regex_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []

        for pattern_name, pattern in ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches[:20]:  # Limit per pattern
                match_str = match if isinstance(match, str) else match[0]
                entity_type = PATTERN_TO_ENTITY_TYPE.get(pattern_name, "organization")
                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    name=f"{pattern_name.upper()}: {match_str}",
                    attributes={"pattern": pattern_name, "value": match_str},
                    confidence=0.8,
                    source_snippet=match_str,
                ))

        return entities

    async def _extract_llm_entities(self, text: str, context: PipelineContext) -> List[ExtractedEntity]:
        """Extract named entities using LLM structured output."""
        entities = []

        # Use a reasonable excerpt for LLM
        excerpt = text[:4000] if len(text) > 4000 else text

        prompt = (
            "Extract named entities from this text. Return a JSON array where each item has: "
            '"entity_type" (one of: person, organization, condition, drug, procedure, payer, '
            'facility, device, test, regulation), "name", "confidence" (0.0-1.0). '
            "Only include entities you are confident about.\n\n"
            f"Text:\n{excerpt}\n\nEntities:"
        )

        try:
            import httpx
            ollama_url = "http://localhost:11434"
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": "qwen3.5:4b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                if response.status_code == 200:
                    content = response.json().get("message", {}).get("content", "")
                    entities = self._parse_llm_entities(content)
        except Exception as e:
            logger.debug(f"LLM entity extraction unavailable: {e}")

        return entities

    def _parse_llm_entities(self, content: str) -> List[ExtractedEntity]:
        """Parse LLM response into ExtractedEntity objects."""
        import json
        entities = []

        # Try to find JSON array in response
        try:
            # Look for JSON array brackets
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                arr = json.loads(content[start:end])
                for item in arr[:30]:
                    if isinstance(item, dict) and "name" in item:
                        entity_type = item.get("entity_type", "organization")
                        if entity_type not in {"person", "organization", "condition", "drug",
                                              "procedure", "payer", "facility", "device",
                                              "test", "regulation"}:
                            entity_type = "organization"
                        entities.append(ExtractedEntity(
                            entity_type=entity_type,
                            name=item["name"][:200],
                            attributes=item.get("attributes", {}),
                            confidence=min(1.0, max(0.0, float(item.get("confidence", 0.5)))),
                        ))
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"LLM entity parse failed: {e}")

        return entities

    def _merge_entities(self, regex_entities: List[ExtractedEntity],
                        llm_entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Merge and deduplicate entity lists."""
        seen_names = set()
        merged = []

        for entity in regex_entities + llm_entities:
            key = (entity.entity_type, entity.name.lower())
            if key not in seen_names:
                seen_names.add(key)
                merged.append(entity)

        return merged