"""
Aethera AI — Stage 8: Memory Updater

Creates knowledge graph nodes and edges from extracted entities and facts.
Uses LLM for relationship extraction when sensitivity-safe.
"""
import logging
from typing import List, Dict, Any

from .stages import PipelineStage
from .context import PipelineContext
from .entities import PATTERN_TO_ENTITY_TYPE

logger = logging.getLogger("aethera.pipeline.memory_update")


class MemoryUpdater(PipelineStage):
    """Stage 8: Create KnowledgeGraph nodes and edges from entities."""

    name = "memory_update"

    @property
    def depends_on(self) -> list:
        return ["entities", "facts"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.entities and not context.extracted_facts:
            return context

        # Build entity nodes for KnowledgeGraph
        entity_records = self._build_entity_records(context)

        # Build relation edges
        relation_records = await self._build_relation_records(context)

        # Batch insert into KnowledgeGraph
        entity_ids, relation_ids = self._store_in_graph(entity_records, relation_records, context)

        context.entity_ids = entity_ids
        context.relation_ids = relation_ids

        logger.info(f"Created {len(entity_ids)} nodes, {len(relation_ids)} edges in knowledge graph")
        return context

    def _build_entity_records(self, context: PipelineContext) -> List[Dict[str, Any]]:
        """Build entity records for batch insertion."""
        records = []
        seen_names = set()

        for entity in context.entities:
            name_key = (entity.entity_type, entity.name.lower())
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            records.append({
                "entity_type": entity.entity_type,
                "name": entity.name[:200],
                "attributes": {
                    "source_file": context.filename or context.file_path or "",
                    "domain": context.domain,
                    "confidence": entity.confidence,
                    **entity.attributes,
                },
            })

        return records

    async def _build_relation_records(self, context: PipelineContext) -> List[Dict[str, Any]]:
        """Build relation records between co-occurring entities."""
        relations = []

        # If we have entity IDs from the graph, create co-occurrence edges
        # For now, create relations between entities in the same document
        if len(context.entities) < 2:
            return relations

        # LLM-based relation extraction (if sensitivity-safe)
        if context.sensitivity in ("public", "internal"):
            llm_relations = await self._extract_llm_relations(context)
            if llm_relations:
                return llm_relations

        # Fallback: create co-occurrence relations for same-type entities
        # Entities from the same document that share types get "related_to" edges
        for i, entity_a in enumerate(context.entities):
            for entity_b in context.entities[i+1:i+5]:  # Link to next 4 entities
                if entity_a.entity_type != entity_b.entity_type:
                    relations.append({
                        "source_id": f"entity_placeholder_{i}",
                        "relation": "related_to",
                        "target_id": f"entity_placeholder_{context.entities.index(entity_b)}",
                        "attributes": {
                            "co_occurrence": True,
                            "source_file": context.filename or "",
                        },
                        "weight": 0.3,
                    })

        return relations[:50]

    async def _extract_llm_relations(self, context: PipelineContext) -> List[Dict[str, Any]]:
        """Extract relationships between entities using LLM."""
        relations = []
        entity_names = [e.name for e in context.entities[:15]]

        if len(entity_names) < 2:
            return relations

        prompt = (
            "Given these entities extracted from a document, identify relationships between them. "
            "Return a JSON array where each item has: "
            '"source" (entity name), "relation" (one of: treats, billed_by, covered_by, '
            'regulated_by, interacts_with, performs, employs, prescribes, diagnoses, '
            'refers_to, belongs_to, located_at, reimburses, supersedes, related_to, part_of), '
            '"target" (entity name), "weight" (0.0-1.0 confidence).\n\n'
            f"Entities: {', '.join(entity_names)}\n\n"
            f"Document excerpt: {context.raw_text[:2000]}\n\nRelationships:"
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
                    relations = self._parse_llm_relations(content, context)
        except Exception as e:
            logger.debug(f"LLM relation extraction unavailable: {e}")

        return relations

    def _parse_llm_relations(self, content: str, context: PipelineContext) -> List[Dict[str, Any]]:
        """Parse LLM response into relation records."""
        import json
        relations = []
        entity_name_map = {e.name.lower(): i for i, e in enumerate(context.entities)}

        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                arr = json.loads(content[start:end])
                for item in arr[:30]:
                    if not isinstance(item, dict):
                        continue
                    source_name = item.get("source", "")
                    target_name = item.get("target", "")
                    relation = item.get("relation", "related_to")

                    source_idx = entity_name_map.get(source_name.lower())
                    target_idx = entity_name_map.get(target_name.lower())

                    if source_idx is not None and target_idx is not None:
                        relations.append({
                            "source_id": f"entity_placeholder_{source_idx}",
                            "relation": relation,
                            "target_id": f"entity_placeholder_{target_idx}",
                            "weight": min(1.0, max(0.1, float(item.get("weight", 0.5)))),
                        })
        except (json.JSONDecodeError, ValueError):
            pass

        return relations

    def _store_in_graph(self, entity_records: List[Dict[str, Any]],
                        relation_records: List[Dict[str, Any]],
                        context: PipelineContext) -> tuple:
        """Batch insert entities and relations into the KnowledgeGraph."""
        entity_ids = []
        relation_ids = []

        try:
            from memory.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            if not kg._conn:
                kg.initialize()

            # First, insert entities and get real IDs
            id_map = {}
            for i, rec in enumerate(entity_records):
                eid = kg.add_entity(
                    entity_type=rec["entity_type"],
                    name=rec["name"],
                    attributes=rec.get("attributes", {}),
                )
                entity_ids.append(eid)
                id_map[f"entity_placeholder_{i}"] = eid

            # Then, resolve placeholder IDs and insert relations
            resolved_relations = []
            for rel in relation_records:
                source_id = id_map.get(rel["source_id"])
                target_id = id_map.get(rel["target_id"])
                if source_id and target_id:
                    resolved_relations.append({
                        "source_id": source_id,
                        "relation": rel["relation"],
                        "target_id": target_id,
                        "weight": rel.get("weight", 1.0),
                        "attributes": rel.get("attributes", {}),
                    })

            if resolved_relations:
                kg.add_entities_and_relations_batch([], resolved_relations)
                relation_ids = [r["source_id"] for r in resolved_relations]

        except Exception as e:
            logger.error(f"KnowledgeGraph update failed: {e}")

        return entity_ids, relation_ids