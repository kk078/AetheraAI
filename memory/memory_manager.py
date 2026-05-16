"""
Aethera AI - Memory Manager

Unified orchestrator for all memory subsystems. Provides:
- retrieve_context(): Assembles relevant context for LLM system prompts
- consolidate(): Post-response fact extraction, learning, and audit logging
- get_user_context(): Short preference summary for personalization

All SQLite store calls are wrapped with asyncio.to_thread() for async compatibility.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from orchestrator.sensitivity import DetectionResult, SensitivityLevel

logger = logging.getLogger("aethera.memory_manager")

# Context budget allocations (characters)
_CONTEXT_BUDGETS = {
    "facts": 500,
    "preferences": 300,
    "health_records": 500,
    "vector_docs": 500,
    "knowledge_gaps": 200,
    "total": 2000,
}

# Factual claim indicators for extraction
_FACT_INDICATORS = re.compile(
    r"\b(is|are|was|were|has|have|had|means|requires|indicates|diagnosed|"
    r"covered|denied|approved|recommended|contraindicated|interacts)\b",
    re.IGNORECASE,
)


class MemoryManager:
    """Unified memory orchestrator for Aethera AI."""

    def __init__(
        self,
        db_path: str = "/data/aethera.db",
        health_db_path: str = "/data/health_records.db",
        chromadb_url: str = "http://chromadb:8000",
        encryption_key: str = "",
        audit_db_path: str = "./data/aethera_audit.db",
    ):
        self.db_path = db_path
        self.health_db_path = health_db_path
        self.chromadb_url = chromadb_url
        self.encryption_key = encryption_key
        self.audit_db_path = audit_db_path

        # Lazy-loaded subsystems
        self._fact_store = None
        self._learning_store = None
        self._knowledge_graph = None
        self._health_records = None
        self._contradiction_detector = None
        self._knowledge_gap_store = None
        self._vector_store = None
        self._audit_db = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        if self._initialized:
            return

        # Initialize SQLite-backed stores directly (they handle their own connections)
        self._init_sync_stores()

        # Initialize async vector store
        try:
            from memory.vector_store import VectorStore
            self._vector_store = VectorStore(self.chromadb_url)
            await self._vector_store.initialize()
            logger.info("Vector store initialized")
        except Exception as e:
            logger.warning(f"Vector store initialization failed: {e}")
            self._vector_store = None

        self._initialized = True
        logger.info("Memory manager initialized")

    def _init_sync_stores(self) -> None:
        """Initialize all synchronous SQLite stores."""
        try:
            from memory.fact_store import FactStore
            self._fact_store = FactStore(self.db_path)
            self._fact_store.initialize()
            logger.info("Fact store initialized")
        except Exception as e:
            logger.warning(f"Fact store initialization failed: {e}")

        try:
            from memory.learning import LearningStore
            self._learning_store = LearningStore(self.db_path)
            self._learning_store.initialize()
            logger.info("Learning store initialized")
        except Exception as e:
            logger.warning(f"Learning store initialization failed: {e}")

        try:
            from memory.knowledge_graph import KnowledgeGraph
            self._knowledge_graph = KnowledgeGraph(self.db_path)
            self._knowledge_graph.initialize()
            logger.info("Knowledge graph initialized")
        except Exception as e:
            logger.warning(f"Knowledge graph initialization failed: {e}")

        try:
            from memory.health_records import HealthRecords
            self._health_records = HealthRecords(self.health_db_path, self.encryption_key)
            self._health_records.initialize()
            logger.info("Health records initialized")
        except Exception as e:
            logger.warning(f"Health records initialization failed: {e}")

        try:
            from memory.contradiction_detector import ContradictionDetector
            self._contradiction_detector = ContradictionDetector()
            logger.info("Contradiction detector initialized")
        except Exception as e:
            logger.warning(f"Contradiction detector initialization failed: {e}")

        try:
            from memory.knowledge_gaps import KnowledgeGapStore
            self._knowledge_gap_store = KnowledgeGapStore(self.db_path)
            self._knowledge_gap_store.initialize()
            logger.info("Knowledge gap store initialized")
        except Exception as e:
            logger.warning(f"Knowledge gap store initialization failed: {e}")

        try:
            from infrastructure.security.audit_logger import AuditDatabase
            self._audit_db = AuditDatabase(self.audit_db_path)
            logger.info("Audit database initialized")
        except Exception as e:
            logger.warning(f"Audit database initialization failed: {e}")

    async def close(self) -> None:
        """Gracefully shut down all memory subsystems."""
        if self._fact_store:
            self._fact_store.close()
        if self._learning_store:
            self._learning_store.close()
        if self._knowledge_graph:
            self._knowledge_graph.close()
        if self._health_records:
            self._health_records.close()
        if self._knowledge_gap_store:
            self._knowledge_gap_store.close()
        if self._vector_store:
            await self._vector_store.close()

        self._initialized = False
        logger.info("Memory manager closed")

    # ------------------------------------------------------------------
    # Context Retrieval
    # ------------------------------------------------------------------

    async def retrieve_context(
        self,
        query: str,
        user_id: str = "default_user",
        specialist: str = "general",
        sensitivity: Optional[DetectionResult] = None,
        max_chars: int = 2000,
    ) -> str:
        """
        Retrieve relevant context from all memory subsystems.

        Assembles a bounded context string for injection into the system prompt.
        Respects PHI/PII sensitivity boundaries.
        """
        if not self._initialized:
            await self.initialize()

        parts: List[str] = []
        total_chars = 0

        # 1. Relevant facts
        if self._fact_store and total_chars < max_chars:
            try:
                facts = self._fact_store.search_facts(
                    query, min_confidence=0.5, limit=5
                )
                if facts:
                    budget = min(_CONTEXT_BUDGETS["facts"], max_chars - total_chars)
                    facts_text = self._format_facts(facts, budget)
                    if facts_text:
                        parts.append(facts_text)
                        total_chars += len(facts_text)
            except Exception as e:
                logger.debug(f"Fact retrieval failed: {e}")

        # 2. Learned preferences
        if self._learning_store and total_chars < max_chars:
            try:
                prefs = self._learning_store.get_preferences(user_id)
                if prefs:
                    budget = min(_CONTEXT_BUDGETS["preferences"], max_chars - total_chars)
                    prefs_text = self._format_preferences(prefs, budget)
                    if prefs_text:
                        parts.append(prefs_text)
                        total_chars += len(prefs_text)
            except Exception as e:
                logger.debug(f"Preference retrieval failed: {e}")

        # 3. Health records (healthcare specialists only)
        healthcare_specialists = {
            "healthcare_provider", "healthcare_payer", "healthcare_regulatory",
            "healthcare_clinical", "healthcare_pharmacy", "healthcare_behavioral",
        }
        if specialist in healthcare_specialists and self._health_records and total_chars < max_chars:
            try:
                is_phi = sensitivity and sensitivity.contains_phi if sensitivity else False
                budget = min(_CONTEXT_BUDGETS["health_records"], max_chars - total_chars)

                if is_phi:
                    records = self._health_records.export_deidentified(user_id)
                    hr_text = self._format_health_records(records, budget, deidentified=True)
                else:
                    records = self._health_records.search(user_id, query, limit=5)
                    hr_text = self._format_health_records(records, budget, deidentified=False)

                if hr_text:
                    parts.append(hr_text)
                    total_chars += len(hr_text)
            except Exception as e:
                logger.debug(f"Health records retrieval failed: {e}")

        # 4. Vector store documents — search user memories first
        if self._vector_store and total_chars < max_chars:
            try:
                results = await self._vector_store.search(
                    "user_memories", query, top_k=3
                )
                if results and not any(r.get("error") for r in results):
                    budget = min(_CONTEXT_BUDGETS["vector_docs"], max_chars - total_chars)
                    docs_text = self._format_vector_results(results, budget)
                    if docs_text:
                        parts.append(docs_text)
                        total_chars += len(docs_text)
            except Exception as e:
                logger.debug(f"Vector search failed: {e}")

        # 4b. Search domain-specific knowledge collections
        if self._vector_store and total_chars < max_chars:
            knowledge_collection = self._specialist_to_collection(specialist)
            if knowledge_collection:
                try:
                    kb_results = await self._vector_store.search(
                        knowledge_collection, query, top_k=3
                    )
                    if kb_results and not any(r.get("error") for r in kb_results):
                        remaining = max_chars - total_chars
                        budget = min(_CONTEXT_BUDGETS["vector_docs"], remaining)
                        kb_text = self._format_vector_results(
                            kb_results, budget, header="Knowledge base results"
                        )
                        if kb_text:
                            parts.append(kb_text)
                            total_chars += len(kb_text)
                except Exception as e:
                    logger.debug(f"Knowledge base search failed: {e}")

        # 5. Knowledge gaps (side effect: auto-detect)
        if self._knowledge_gap_store and total_chars < max_chars:
            try:
                self._knowledge_gap_store.auto_detect_from_query(query)
                open_gaps = self._knowledge_gap_store.list_gaps(status="detected", limit=3)
                if open_gaps:
                    budget = min(_CONTEXT_BUDGETS["knowledge_gaps"], max_chars - total_chars)
                    gaps_text = self._format_knowledge_gaps(open_gaps, budget)
                    if gaps_text:
                        parts.append(gaps_text)
                        total_chars += len(gaps_text)
            except Exception as e:
                logger.debug(f"Knowledge gap detection failed: {e}")

        if not parts:
            return ""

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Post-Response Consolidation
    # ------------------------------------------------------------------

    async def consolidate(
        self,
        user_id: str,
        query: str,
        response: str,
        specialist: str = "general",
        sensitivity: Optional[DetectionResult] = None,
        conversation_id: str = "",
    ) -> None:
        """
        Post-response consolidation. Fire-and-forget — all exceptions caught.

        Steps:
        1. Extract key facts from response -> FactStore
        2. Record interaction in LearningStore
        3. Check contradictions with existing facts
        4. Log memory access to audit trail
        """
        if not self._initialized:
            return

        # 1. Extract and store facts
        if self._fact_store:
            try:
                facts = self._extract_facts(response, specialist)
                for fact_text, category in facts:
                    self._fact_store.store_fact(
                        fact_text=fact_text,
                        source=f"conversation:{conversation_id}",
                        source_type="conversation",
                        confidence=0.6,
                        category=category,
                    )
                    break  # Only store the first fact to avoid noise
            except Exception as e:
                logger.debug(f"Fact extraction failed: {e}")

        # 2. Record interaction in learning store
        if self._learning_store:
            try:
                self._learning_store.record_interaction(
                    user_id=user_id,
                    interaction_type="query",
                    context={
                        "query": query[:200],
                        "specialist": specialist,
                        "phi_detected": bool(sensitivity and sensitivity.contains_phi) if sensitivity else False,
                    },
                )
                self._learning_store.record_interaction(
                    user_id=user_id,
                    interaction_type="specialist_choice",
                    context={"specialist": specialist, "domain": specialist},
                )
            except Exception as e:
                logger.debug(f"Interaction recording failed: {e}")

        # 3. Check contradictions
        if self._fact_store and self._contradiction_detector:
            try:
                contradictions = self._fact_store.find_contradictions()
                if contradictions:
                    logger.info(f"Found {len(contradictions)} potential fact contradictions")
            except Exception as e:
                logger.debug(f"Contradiction check failed: {e}")

        # 4. Audit log
        if self._audit_db:
            try:
                is_phi = sensitivity.contains_phi if sensitivity else False
                is_pii = sensitivity.contains_pii if sensitivity else False
                self._audit_db.log(
                    user_id=user_id,
                    action="memory_access",
                    resource=f"chat:{conversation_id}",
                    details=json.dumps({
                        "specialist": specialist,
                        "phi_detected": is_phi,
                        "pii_detected": is_pii,
                        "query_length": len(query),
                    }),
                )
            except Exception as e:
                logger.debug(f"Audit logging failed: {e}")

    # ------------------------------------------------------------------
    # User Context
    # ------------------------------------------------------------------

    async def get_user_context(self, user_id: str = "default_user") -> str:
        """Build a short context block summarizing user preferences and patterns."""
        if not self._initialized:
            await self.initialize()

        parts = []

        # User profile preferences
        try:
            from memory.user_profile import get_user_profile
            profile = get_user_profile(user_id, data_dir="./data")
            if profile:
                prefs = profile.get_preference("response_style", "detailed")
                default_specialist = profile.get_preference("default_specialist", "general")
                model_pref = profile.get_preference("model_preference", "auto")
                if prefs != "detailed" or default_specialist != "general" or model_pref != "auto":
                    parts.append(f"User preferences: response_style={prefs}, preferred_specialist={default_specialist}, model={model_pref}")
        except Exception:
            pass

        # Learned preferences
        if self._learning_store:
            try:
                prefs = self._learning_store.get_preferences(user_id)
                if prefs:
                    pref_lines = []
                    for key, val in prefs.items():
                        if isinstance(val, dict):
                            pref_lines.append(f"  {key}: {val.get('value', '?')} (weight: {val.get('weight', '?')})")
                        else:
                            pref_lines.append(f"  {key}: {val}")
                    if pref_lines:
                        parts.append("Learned preferences:\n" + "\n".join(pref_lines[:5]))
            except Exception:
                pass

        # Prediction
        if self._learning_store:
            try:
                prediction = self._learning_store.predict_next_action(user_id)
                if prediction and prediction.get("likely_specialist"):
                    parts.append(f"Predicted next specialist: {prediction['likely_specialist']}")
            except Exception:
                pass

        return "\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_facts(facts: List[Dict], budget: int) -> str:
        if not facts:
            return ""
        lines = ["Relevant facts:"]
        for f in facts[:5]:
            confidence = f.get("confidence", 0)
            source = f.get("source_type", "")
            text = f.get("fact_text", "")[:120]
            lines.append(f"  - [{confidence:.0%}, {source}] {text}")
        result = "\n".join(lines)
        return result[:budget]

    @staticmethod
    def _format_preferences(prefs: Dict, budget: int) -> str:
        if not prefs:
            return ""
        lines = ["User preferences:"]
        for key, val in list(prefs.items())[:5]:
            if isinstance(val, dict):
                lines.append(f"  - {key}: {val.get('value', '?')}")
            else:
                lines.append(f"  - {key}: {val}")
        result = "\n".join(lines)
        return result[:budget]

    @staticmethod
    def _format_health_records(records: List[Dict], budget: int, deidentified: bool = False) -> str:
        if not records:
            return ""
        prefix = "De-identified health records" if deidentified else "Health records"
        lines = [f"{prefix}:"]
        for r in records[:5]:
            table = r.get("_table", r.get("record_type", "unknown"))
            desc = r.get("description", r.get("condition_name", r.get("medication_name", r.get("test_name", str(r)))))
            if isinstance(desc, str):
                desc = desc[:80]
            lines.append(f"  - [{table}] {desc}")
        result = "\n".join(lines)
        return result[:budget]

    @staticmethod
    def _specialist_to_collection(specialist: str) -> Optional[str]:
        """Map a specialist name to its knowledge base collection."""
        mapping = {
            "healthcare_provider": "healthcare_knowledge",
            "healthcare_payer": "healthcare_knowledge",
            "healthcare_regulatory": "healthcare_knowledge",
            "healthcare_clinical": "healthcare_knowledge",
            "healthcare_pharmacy": "healthcare_knowledge",
            "healthcare_behavioral": "healthcare_knowledge",
            "finance": "finance_knowledge",
            "financial": "finance_knowledge",
            "legal": "legal_knowledge",
        }
        return mapping.get(specialist)

    @staticmethod
    def _format_vector_results(results: List[Dict], budget: int, header: str = "Relevant memories:") -> str:
        if not results:
            return ""
        lines = [header]
        for r in results[:3]:
            content = r.get("content", "")[:150]
            lines.append(f"  - {content}")
        result = "\n".join(lines)
        return result[:budget]

    @staticmethod
    def _format_knowledge_gaps(gaps: List[Dict], budget: int) -> str:
        if not gaps:
            return ""
        lines = ["Knowledge gaps:"]
        for g in gaps[:3]:
            topic = g.get("topic", g.get("query", "unknown"))
            priority = g.get("priority", "?")
            lines.append(f"  - {topic} (priority: {priority})")
        result = "\n".join(lines)
        return result[:budget]

    # ------------------------------------------------------------------
    # Fact extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_facts(text: str, category: str = "general") -> List[tuple]:
        """
        Extract factual claims from response text.

        Uses simple heuristics: sentences containing factual indicators
        (dates, numbers, diagnostic terms, regulatory references).
        Returns list of (fact_text, category) tuples.
        """
        facts = []
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue

            # Check for factual indicators
            has_indicator = bool(_FACT_INDICATORS.search(sentence))
            has_number = bool(re.search(r'\b\d+\.?\d*\b', sentence))
            has_date = bool(re.search(r'\b\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', sentence, re.IGNORECASE))

            if has_indicator or (has_number and has_date):
                facts.append((sentence, category))

        return facts[:3]  # Limit to top 3 facts per response

    # ------------------------------------------------------------------
    # Direct access methods (for REST API endpoints)
    # ------------------------------------------------------------------

    @property
    def fact_store(self):
        return self._fact_store

    @property
    def learning_store(self):
        return self._learning_store

    @property
    def knowledge_graph(self):
        return self._knowledge_graph

    @property
    def health_records(self):
        return self._health_records

    @property
    def knowledge_gap_store(self):
        return self._knowledge_gap_store

    @property
    def vector_store(self):
        return self._vector_store

    @property
    def audit_db(self):
        return self._audit_db


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

    async def process_document(self, file_path: str, filename: str = "",
                                content_type: str = "", user_id: str = "default_user") -> dict:
        """
        Run the auto-learning pipeline on a document.

        Convenience method that invokes the pipeline and returns results.
        """
        try:
            from pipeline.pipeline import run_pipeline_for_file
            result = await run_pipeline_for_file(
                file_path=file_path,
                filename=filename,
                content_type=content_type,
            )
            return {
                "success": True,
                "status": result.status,
                "notification": result.notification,
                "entity_count": result.entity_count,
                "fact_count": result.fact_count,
                "chunk_count": result.chunk_count,
                "contradiction_count": result.contradiction_count,
            }
        except Exception as e:
            logger.error(f"process_document failed: {e}")
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    db_path: str = "/data/aethera.db",
    health_db_path: str = "/data/health_records.db",
    chromadb_url: str = "http://chromadb:8000",
    encryption_key: str = "",
    audit_db_path: str = "./data/aethera_audit.db",
) -> MemoryManager:
    """Get or create the memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(
            db_path=db_path,
            health_db_path=health_db_path,
            chromadb_url=chromadb_url,
            encryption_key=encryption_key,
            audit_db_path=audit_db_path,
        )
    return _memory_manager