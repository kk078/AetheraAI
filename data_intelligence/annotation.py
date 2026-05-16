"""
Aethera AI — Stage 2: Data Annotation

Labels data for categories, sentiment, entities, and relationships.
Uses LLM for intelligent annotation with heuristic fallback.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from .context import DataPipelineContext
from .stages import DataPipelineStage
from .llm import DataIntelligenceLLM

logger = logging.getLogger("aethera.data_intelligence.annotation")

# Heuristic patterns for entity extraction (reused from pipeline/entities.py)
ENTITY_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone": re.compile(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "date": re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'),
    "amount": re.compile(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:\.\d{2})?\s*(?:dollars?|USD)\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "zip": re.compile(r'\b\d{5}(?:-\d{4})?\b'),
}

# Simple sentiment patterns
POSITIVE_WORDS = {"good", "great", "excellent", "outstanding", "positive", "success", "happy", "best", "improve", "benefit"}
NEGATIVE_WORDS = {"bad", "poor", "terrible", "awful", "negative", "fail", "failure", "worst", "decline", "problem", "issue"}


class DataAnnotationStage(DataPipelineStage):
    """Label data for categories, sentiment, entities, and relationships."""

    name = "annotation"

    @property
    def depends_on(self) -> list:
        return ["curation"]

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        rows = context.cleaned_rows or context.rows
        if not rows:
            logger.warning("Annotation: no rows to annotate")
            return context

        options = context.options
        annotation_types = options.get("annotation_types", ["category", "sentiment", "entity"])
        sample_size = options.get("annotation_sample_size", 500)
        use_llm = options.get("use_llm", True)

        # Sample rows if dataset is large
        if len(rows) > sample_size:
            step = len(rows) // sample_size
            sample_indices = list(range(0, len(rows), step))[:sample_size]
        else:
            sample_indices = list(range(len(rows)))

        annotations = []

        # LLM annotation (sampled)
        if use_llm:
            llm_annotations = await self._llm_annotate(
                rows, sample_indices, annotation_types, context
            )
            annotations.extend(llm_annotations)

        # Heuristic annotation (all rows)
        heuristic_annotations = self._heuristic_annotate(rows, annotation_types)
        annotations.extend(heuristic_annotations)

        # Store annotations
        store = self._get_store()
        if store:
            store_anns = []
            for ann in annotations:
                store_anns.append({
                    "dataset_id": context.dataset_id,
                    "row_index": ann.get("row_index"),
                    "column_name": ann.get("column_name"),
                    "annotation_type": ann["annotation_type"],
                    "annotation_value": ann["annotation_value"],
                    "confidence": ann.get("confidence", 1.0),
                    "source": ann.get("source", "heuristic"),
                })
            if store_anns:
                store.add_annotations_batch(store_anns)

        context.annotations = annotations
        logger.info(f"Annotation: {len(annotations)} annotations created")
        return context

    async def _llm_annotate(
        self,
        rows: List[Dict[str, Any]],
        indices: List[int],
        annotation_types: List[str],
        context: DataPipelineContext,
    ) -> List[Dict[str, Any]]:
        """Annotate sampled rows using LLM."""
        llm = DataIntelligenceLLM()
        annotations = []

        for idx in indices:
            row = rows[idx]
            try:
                result = await llm.annotate_row(
                    row=row,
                    annotation_types=annotation_types,
                    domain_hint=context.options.get("domain", "general"),
                )
                for ann_type, ann_value in result.items():
                    if ann_type in annotation_types and ann_value:
                        annotations.append({
                            "row_index": idx,
                            "annotation_type": ann_type,
                            "annotation_value": str(ann_value),
                            "confidence": 0.7 if isinstance(ann_value, dict) else 0.8,
                            "source": "llm",
                        })
            except Exception as e:
                logger.debug(f"LLM annotation failed for row {idx}: {e}")

        return annotations

    def _heuristic_annotate(
        self,
        rows: List[Dict[str, Any]],
        annotation_types: List[str],
    ) -> List[Dict[str, Any]]:
        """Annotate all rows using heuristic patterns."""
        annotations = []

        for idx, row in enumerate(rows):
            row_text = " ".join(str(v) for v in row.values() if v is not None)

            # Entity annotation
            if "entity" in annotation_types:
                for entity_type, pattern in ENTITY_PATTERNS.items():
                    matches = pattern.findall(row_text)
                    for match in matches[:5]:  # Limit to 5 per type per row
                        annotations.append({
                            "row_index": idx,
                            "annotation_type": "entity",
                            "annotation_value": f"{entity_type}: {match}",
                            "confidence": 0.9,
                            "source": "heuristic",
                        })

            # Sentiment annotation
            if "sentiment" in annotation_types:
                words = set(row_text.lower().split())
                pos_count = len(words & POSITIVE_WORDS)
                neg_count = len(words & NEGATIVE_WORDS)

                if pos_count > neg_count:
                    sentiment = "positive"
                    confidence = 0.6 + 0.1 * min(pos_count, 4)
                elif neg_count > pos_count:
                    sentiment = "negative"
                    confidence = 0.6 + 0.1 * min(neg_count, 4)
                else:
                    sentiment = "neutral"
                    confidence = 0.5

                annotations.append({
                    "row_index": idx,
                    "annotation_type": "sentiment",
                    "annotation_value": sentiment,
                    "confidence": confidence,
                    "source": "heuristic",
                })

        return annotations

    def _get_store(self):
        """Lazy-load the dataset store."""
        try:
            from .store import get_dataset_store
            return get_dataset_store()
        except Exception:
            return None