"""
Aethera AI - Memory Package

Persistent memory system for Aethera:
- Vector store (ChromaDB) for RAG
- User profile (encrypted)
- Conversation history (SQLite)
- Knowledge graph (entity-relationship)
- Health records (SQLCipher encrypted)
- Fact store with confidence scoring
- Contradiction detector
- Adaptive preference learning
- Knowledge gap tracker
"""

import logging

logger = logging.getLogger("aethera.memory")

# Failure-tolerant imports: one subsystem's missing/broken optional dependency
# (e.g. chromadb, or a broken cryptography native backend) must not make the
# whole memory package — including pure-stdlib stores like ConversationStore —
# unimportable. Mirrors proactive/__init__.py and specialists/__init__.py.
# BaseException is caught because a broken native extension can raise a pyo3
# PanicException (not an Exception subclass) at import time.
_OPTIONAL_EXPORTS = {
    "VectorStore": ("memory.vector_store", "VectorStore"),
    "ConversationStore": ("memory.conversation_store", "ConversationStore"),
    "UserProfile": ("memory.user_profile", "UserProfile"),
    "KnowledgeGraph": ("memory.knowledge_graph", "KnowledgeGraph"),
    "HealthRecords": ("memory.health_records", "HealthRecords"),
    "FactStore": ("memory.fact_store", "FactStore"),
    "ContradictionDetector": ("memory.contradiction_detector", "ContradictionDetector"),
    "LearningStore": ("memory.learning", "LearningStore"),
    "KnowledgeGapStore": ("memory.knowledge_gaps", "KnowledgeGapStore"),
    "MemoryManager": ("memory.memory_manager", "MemoryManager"),
    "get_memory_manager": ("memory.memory_manager", "get_memory_manager"),
}

__all__ = []

for _name, (_module, _attr) in _OPTIONAL_EXPORTS.items():
    try:
        _mod = __import__(_module, fromlist=[_attr])
        globals()[_name] = getattr(_mod, _attr)
        __all__.append(_name)
    except BaseException as _exc:  # noqa: BLE001 - tolerate broken native deps
        logger.debug("Memory export '%s' unavailable: %s", _name, _exc)
