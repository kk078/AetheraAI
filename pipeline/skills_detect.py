"""
Aethera AI — Stage 7: Skill Detector

Scans document content for procedural/workflow patterns and matches
them against available skills in the SkillRegistry.
"""
import re
import logging
from typing import List

from .stages import PipelineStage
from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline.skills_detect")

# Patterns that indicate procedural/workflow content
PROCESS_PATTERNS = [
    re.compile(r"(?:step\s+\d+|first|second|third|next|then|finally|lastly)\b", re.IGNORECASE),
    re.compile(r"(?:how\s+to|guide|tutorial|procedure|workflow|process|instructions)\b", re.IGNORECASE),
    re.compile(r"(?:if\s+.+,\s*(?:then|do|perform|execute|run))\b", re.IGNORECASE),
    re.compile(r"(?:navigate\s+to|click\s+on|open\s+the|select\s+the|enter\s+the)\b", re.IGNORECASE),
    re.compile(r"\d+\.\s+\w+", re.IGNORECASE),  # Numbered lists
]


class SkillDetector(PipelineStage):
    """Stage 7: Detect workflow patterns and relevant skills."""

    name = "skills_detect"

    @property
    def depends_on(self) -> list:
        return ["extractor"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        text = context.raw_text
        if not text:
            return context

        # Detect procedural patterns
        detected_processes = self._detect_processes(text)
        context.detected_processes = detected_processes

        # Match against skill registry
        relevant_skills = self._match_skills(text, context)
        context.detected_skills = relevant_skills

        # Record in LearningStore
        try:
            from memory.learning import get_learning_store
            store = get_learning_store()
            if not store._conn:
                store.initialize()

            store.record_interaction(
                interaction_type="skill_detection",
                context={
                    "document_type": context.file_type,
                    "detected_processes": detected_processes[:5],
                    "detected_skills": relevant_skills[:5],
                    "domain": context.domain,
                },
                user_id="default_user",
            )
        except Exception as e:
            logger.debug(f"LearningStore skill recording skipped: {e}")

        logger.info(f"Detected {len(detected_processes)} processes, {len(relevant_skills)} skills")
        return context

    def _detect_processes(self, text: str) -> List[str]:
        """Detect procedural patterns in text."""
        processes = []
        seen = set()

        for pattern in PROCESS_PATTERNS:
            for match in pattern.finditer(text):
                # Extract surrounding context
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 80)
                snippet = text[start:end].strip().replace("\n", " ")

                key = snippet[:40].lower()
                if key not in seen:
                    seen.add(key)
                    processes.append(snippet[:150])

        return processes[:20]

    def _match_skills(self, text: str, context: PipelineContext) -> List[str]:
        """Match document content against available skills."""
        relevant_skills = []
        text_lower = text.lower()

        try:
            from skills.skill_registry import get_registry
            registry = get_registry()
            all_skills = registry.list()  # Returns list of skill names

            for skill_name in all_skills:
                skill = registry.get(skill_name)
                if not skill:
                    continue

                # Check skill name against text
                name_parts = skill_name.replace("_", " ").split()
                if any(part in text_lower for part in name_parts if len(part) > 3):
                    relevant_skills.append(skill_name)
                    continue

                # Check skill description keywords
                desc = (skill.description or "").lower()
                desc_keywords = [w for w in desc.split() if len(w) > 4]
                if sum(1 for kw in desc_keywords[:20] if kw in text_lower) >= 3:
                    relevant_skills.append(skill_name)

        except Exception as e:
            logger.debug(f"Skill matching skipped: {e}")

        return relevant_skills[:10]