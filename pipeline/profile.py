"""
Aethera AI — Stage 6: Profile Updater

Checks if document content reveals user preferences and context,
then updates the LearningStore accordingly.
"""
import logging
from typing import Dict, Any

from .stages import PipelineStage
from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline.profile")


class ProfileUpdater(PipelineStage):
    """Stage 6: Detect user preferences from document content and update profile."""

    name = "profile"

    @property
    def depends_on(self) -> list:
        return ["extractor"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        updates = []

        # Detect domain preferences from file type and domain
        domain_pref = self._detect_domain_preference(context)
        if domain_pref:
            updates.append(domain_pref)

        # Detect preferences from document metadata
        meta_prefs = self._detect_metadata_preferences(context)
        updates.extend(meta_prefs)

        # Detect preferences from content patterns
        content_prefs = self._detect_content_preferences(context)
        updates.extend(content_prefs)

        # Record interaction in LearningStore
        try:
            from memory.learning import get_learning_store
            store = get_learning_store()
            if not store._conn:
                store.initialize()

            store.record_interaction(
                interaction_type="document_upload",
                context={
                    "file_type": context.file_type,
                    "domain": context.domain,
                    "entity_count": len(context.entities),
                    "fact_count": len(context.extracted_facts),
                    "sensitivity": context.sensitivity,
                },
                user_id="default_user",
            )

            # Apply preference updates
            for pref in updates:
                store.update_weight(
                    preference_key=pref["key"],
                    delta=pref.get("delta", 0.1),
                    value=pref.get("value"),
                )
        except Exception as e:
            logger.debug(f"LearningStore update skipped: {e}")

        context.preferences_updated = [u["key"] for u in updates]
        logger.info(f"Updated {len(updates)} profile preferences")
        return context

    def _detect_domain_preference(self, context: PipelineContext) -> Dict[str, Any]:
        """Detect domain preference from document content."""
        domain_specialist_map = {
            "healthcare": "healthcare_provider",
            "finance": "finance",
            "legal": "legal",
            "technology": "software_engineering",
        }

        specialist = domain_specialist_map.get(context.domain)
        if specialist:
            return {
                "key": f"preferred_specialist",
                "value": specialist,
                "delta": 0.05,
            }
        return {}

    def _detect_metadata_preferences(self, context: PipelineContext) -> list:
        """Detect preferences from document metadata."""
        prefs = []

        # Author preference
        author = context.metadata.get("author", "")
        if author and len(author) < 100:
            prefs.append({
                "key": f"known_author:{author}",
                "value": context.filename,
                "delta": 0.1,
            })

        # Document type frequency preference
        if context.file_type:
            prefs.append({
                "key": f"upload_type:{context.file_type}",
                "value": "frequent",
                "delta": 0.1,
            })

        return prefs

    def _detect_content_preferences(self, context: PipelineContext) -> list:
        """Detect preferences from document content patterns."""
        prefs = []
        text = context.raw_text.lower()

        # Detect recurring entity types as interest signals
        entity_type_counts: Dict[str, int] = {}
        for entity in context.entities:
            entity_type_counts[entity.entity_type] = entity_type_counts.get(entity.entity_type, 0) + 1

        for etype, count in entity_type_counts.items():
            if count >= 3:
                prefs.append({
                    "key": f"interest:{etype}",
                    "value": count,
                    "delta": 0.05 * min(count, 5),
                })

        return prefs