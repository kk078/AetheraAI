"""
Aethera AI — Stage 4: Knowledge Indexer

Chunks extracted text and indexes it into ChromaDB with metadata tags.
Reuses the chunking logic from knowledge_bases/index_all.py.
"""
import hashlib
import logging
from typing import List, Dict, Any

from .stages import PipelineStage
from .context import PipelineContext

logger = logging.getLogger("aethera.pipeline.indexer")

# Token estimation (rough: 1 token ≈ 4 chars)
CHUNK_SIZE_CHARS = 2048  # ~512 tokens
OVERLAP_CHARS = 200       # ~50 tokens


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS,
                overlap: int = OVERLAP_CHARS) -> List[str]:
    """
    Split text into chunks with sentence-boundary awareness and overlap.

    Tries to break at paragraph boundaries first, then sentence boundaries.
    """
    if not text or not text.strip():
        return []

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of current chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

        # Split oversized paragraphs by sentences
        if len(current_chunk) > chunk_size * 2:
            sentences = current_chunk.replace(". ", ".\n").replace("? ", "?\n").replace("! ", "!\n").split("\n")
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = current_chunk + " " + sentence if current_chunk else sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if len(c.strip()) > 50]


# Domain to ChromaDB collection mapping
DOMAIN_COLLECTION_MAP = {
    "healthcare": "healthcare_knowledge",
    "finance": "finance_knowledge",
    "legal": "legal_knowledge",
    "technology": "technology_knowledge",
}


class KnowledgeIndexer(PipelineStage):
    """Stage 4: Index document chunks into ChromaDB."""

    name = "indexer"

    @property
    def depends_on(self) -> list:
        return ["extractor"]

    async def execute(self, context: PipelineContext) -> PipelineContext:
        text = context.raw_text
        if not text:
            return context

        # Select collection based on domain
        collection = DOMAIN_COLLECTION_MAP.get(context.domain, "documents")
        if context.sensitivity in ("phi", "pii"):
            collection = "user_memories"

        # Chunk the text
        chunks = chunk_text(text)
        if not chunks:
            return context

        # Build metadata for each chunk
        metadatas = self._build_chunk_metadata(context, chunks)

        # Generate doc IDs
        doc_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.sha256(f"{context.job_id}_{i}_{chunk[:100]}".encode()).hexdigest()[:16]
            doc_ids.append(doc_id)

        # Index into ChromaDB
        try:
            from memory.vector_store import get_vector_store
            store = get_vector_store()
            # Ensure initialized
            if not store._session:
                await store.initialize()

            result_ids = await store.add_documents_batch(
                collection=collection,
                contents=chunks,
                metadatas=metadatas,
                doc_ids=doc_ids,
            )
            context.indexed_chunks = len(result_ids)
            context.chunk_ids = result_ids

        except Exception as e:
            logger.error(f"ChromaDB indexing failed: {e}")
            # Store chunks info even if indexing fails
            context.indexed_chunks = len(chunks)

        logger.info(f"Indexed {context.indexed_chunks} chunks in {collection}")
        return context

    def _build_chunk_metadata(self, context: PipelineContext,
                               chunks: List[str]) -> List[Dict[str, Any]]:
        """Build metadata dict for each chunk."""
        base_metadata = {
            "source_file": context.filename or context.file_path or context.url,
            "file_type": context.file_type,
            "domain": context.domain,
            "job_id": context.job_id,
        }

        # Add entity names to metadata
        entity_names = [e.name for e in context.entities[:10]]
        if entity_names:
            base_metadata["entities"] = ", ".join(entity_names)

        # Add title from document metadata if available
        if context.metadata.get("title"):
            base_metadata["title"] = context.metadata["title"]

        # Per-chunk metadata
        metadatas = []
        for i, chunk in enumerate(chunks):
            meta = dict(base_metadata)
            meta["chunk_index"] = i
            meta["chunk_hash"] = hashlib.sha256(chunk.encode()).hexdigest()[:12]
            metadatas.append(meta)

        return metadatas