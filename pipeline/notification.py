"""
Aethera AI — Stage 10: Notification Builder

Assembles a human-readable summary of what the pipeline learned
from a document, including entities, facts, contradictions, and relevant skills.
"""
import logging

from .stages import PipelineStage
from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline.notification")


class NotificationBuilder(PipelineStage):
    """Stage 10: Build a human-readable notification summarizing pipeline results."""

    name = "notification"

    @property
    def required_content(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> PipelineContext:
        parts = []

        # Core message
        doc_name = context.filename or context.url or "document"
        if context.domain != "general":
            parts.append(f"I've learned from this {context.domain} {context.file_type} document: **{doc_name}**")
        else:
            parts.append(f"I've learned from this {context.file_type} document: **{doc_name}**")

        # Sensitivity note
        if context.sensitivity in ("phi", "pii"):
            parts.append(f"⚠ Content classified as {context.sensitivity.upper()} — stored locally only")

        # Entities
        if context.entities:
            entity_summary = self._summarize_entities(context.entities)
            parts.append(f"**{len(context.entities)} entities** extracted: {entity_summary}")

        # Facts
        if context.extracted_facts:
            parts.append(f"**{len(context.extracted_facts)} facts** stored with source attribution")

        # Chunks indexed
        if context.indexed_chunks:
            parts.append(f"**{context.indexed_chunks} chunks** indexed for semantic search")

        # Knowledge graph
        if context.entity_ids or context.relation_ids:
            parts.append(f"**{len(context.entity_ids)} nodes** and **{len(context.relation_ids)} edges** added to knowledge graph")

        # Contradictions
        if context.contradictions:
            parts.append(f"⚠ **{len(context.contradictions)} contradiction(s)** detected — flagged for review")
            for c in context.contradictions[:3]:
                parts.append(f"  - {c.reason}")

        # Skills detected
        if context.detected_skills:
            parts.append(f"Relevant skills: {', '.join(context.detected_skills[:5])}")

        # Preferences updated
        if context.preferences_updated:
            parts.append(f"Profile preferences updated: {', '.join(context.preferences_updated[:3])}")

        # Stage failures
        if context.stages_failed:
            failed_names = ", ".join(context.stages_failed.keys())
            parts.append(f"Some stages had issues: {failed_names}")

        context.notification = "\n".join(parts)
        logger.info(f"Notification built: {len(context.notification)} chars")
        return context

    def _summarize_entities(self, entities) -> str:
        """Create a concise summary of extracted entities."""
        type_counts = {}
        for e in entities:
            type_counts[e.entity_type] = type_counts.get(e.entity_type, 0) + 1

        summary_parts = []
        for etype, count in sorted(type_counts.items(), key=lambda x: -x[1])[:5]:
            summary_parts.append(f"{count} {etype}")

        # Add top entity names
        top_names = [e.name for e in entities[:5] if len(e.name) < 50]
        if top_names:
            summary_parts.append(f"including {', '.join(top_names[:3])}")

        return ", ".join(summary_parts)