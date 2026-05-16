"""
Aethera AI — Stage 9: Contradiction Checker

Validates newly extracted facts against existing knowledge in the FactStore,
flagging contradictions for human review.
"""
import logging

from .stages import PipelineStage
from .context import PipelineContext, Contradiction

logger = logging.getLogger("aethera.pipeline.contradictions")


class ContradictionChecker(PipelineStage):
    """Stage 9: Check new facts against existing knowledge for contradictions."""

    name = "contradictions"

    @property
    def depends_on(self) -> list:
        return ["facts"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.extracted_facts:
            return context

        contradictions = []

        try:
            from memory.contradiction_detector import get_contradiction_detector
            from memory.fact_store import get_fact_store

            detector = get_contradiction_detector()
            store = get_fact_store()
            if not store._conn:
                store.initialize()

            for fact in context.extracted_facts:
                # Find existing facts in same category
                existing = store.search_facts(
                    query=fact.fact_text[:50],
                    category=fact.category,
                    min_confidence=0.3,
                    limit=5,
                )

                if not existing:
                    continue

                # Check against contradiction detector
                existing_texts = [f["fact_text"] for f in existing if "fact_text" in f]
                for existing_text in existing_texts:
                    try:
                        result = detector.check_new_fact(fact.fact_text, existing_texts)
                        for c in result:
                            contradictions.append(Contradiction(
                                new_fact=fact.fact_text[:200],
                                existing_fact=existing_text[:200],
                                reason=c.reason if hasattr(c, "reason") else str(c),
                                severity="review",
                            ))
                    except Exception:
                        # Fallback: simple keyword contradiction check
                        if self._simple_contradiction_check(fact.fact_text, existing_text):
                            contradictions.append(Contradiction(
                                new_fact=fact.fact_text[:200],
                                existing_fact=existing_text[:200],
                                reason="Potential keyword contradiction detected",
                                severity="review",
                            ))

        except Exception as e:
            logger.debug(f"Contradiction checking skipped: {e}")

        context.contradictions = contradictions
        logger.info(f"Found {len(contradictions)} potential contradictions")
        return context

    def _simple_contradiction_check(self, new_fact: str, existing_fact: str) -> bool:
        """Simple heuristic contradiction check as fallback."""
        opposing_pairs = [
            ("approved", "denied"), ("covered", "excluded"),
            ("active", "inactive"), ("increased", "decreased"),
            ("required", "optional"), ("included", "excluded"),
        ]

        new_lower = new_fact.lower()
        existing_lower = existing_fact.lower()

        for pos, neg in opposing_pairs:
            if (pos in new_lower and neg in existing_lower) or \
               (neg in new_lower and pos in existing_lower):
                return True

        return False