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

from memory.vector_store import VectorStore
from memory.conversation_store import ConversationStore
from memory.user_profile import UserProfile
from memory.knowledge_graph import KnowledgeGraph
from memory.health_records import HealthRecords
from memory.fact_store import FactStore
from memory.contradiction_detector import ContradictionDetector
from memory.learning import LearningStore
from memory.knowledge_gaps import KnowledgeGapStore
from memory.memory_manager import MemoryManager, get_memory_manager

__all__ = [
    "VectorStore",
    "ConversationStore",
    "UserProfile",
    "KnowledgeGraph",
    "HealthRecords",
    "FactStore",
    "ContradictionDetector",
    "LearningStore",
    "KnowledgeGapStore",
    "MemoryManager",
    "get_memory_manager",
]
