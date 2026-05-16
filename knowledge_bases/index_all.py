"""
Index all downloaded knowledge into ChromaDB for RAG.

Reads files from /data/knowledge/, chunks them into 512-token segments
with 50-token overlap, generates embeddings via Ollama nomic-embed-text,
and stores in ChromaDB collections organized by category.

Usage:
    python -m knowledge_bases.index_all [--category healthcare|finance|legal|technology] [--force] [--collection name]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from knowledge_bases import CATEGORIES, DATA_ROOT

logger = logging.getLogger("knowledge_bases.index_all")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 50
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED_URL = f"{OLLAMA_URL}/api/embed"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))


def estimate_tokens(text: str) -> int:
    """Estimate token count using heuristic (roughly 4 chars per token for English)."""
    return max(1, len(text) // 4)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS, overlap: int = CHUNK_OVERLAP_TOKENS) -> list:
    """Split text into chunks of approximately chunk_size tokens with overlap.

    Uses sentence-boundary-aware splitting for better coherence.
    """
    if not text.strip():
        return []

    # Split into paragraphs first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_tokens = estimate_tokens(para)

        # If single paragraph exceeds chunk size, split by sentences
        if para_tokens > chunk_size:
            sentences = para.replace(". ", ".\n").replace("? ", "?\n").replace("! ", "!\n").split("\n")
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                sent_tokens = estimate_tokens(sentence)
                if current_tokens + sent_tokens > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Keep overlap from end of current chunk
                    overlap_text = current_chunk[-(overlap * 4):]
                    current_chunk = overlap_text + "\n\n"
                    current_tokens = estimate_tokens(overlap_text)
                current_chunk += sentence + " "
                current_tokens += sent_tokens
        elif current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-(overlap * 4):]
            current_chunk = overlap_text + "\n\n"
            current_tokens = estimate_tokens(overlap_text)
            current_chunk += para + "\n\n"
            current_tokens += para_tokens
        else:
            current_chunk += para + "\n\n"
            current_tokens += para_tokens

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


async def generate_embedding(text: str, client: httpx.AsyncClient) -> list:
    """Generate embedding for text using Ollama nomic-embed-text model."""
    try:
        response = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [])
        if embeddings and isinstance(embeddings[0], list):
            return embeddings[0]
        # Fallback for older Ollama API format
        return data.get("embedding", [])
    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
        raise


async def generate_embeddings_batch(texts: list, client: httpx.AsyncClient) -> list:
    """Generate embeddings for a batch of texts."""
    try:
        response = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings
        # Fallback: generate one at a time
        results = []
        for text in texts:
            emb = await generate_embedding(text, client)
            results.append(emb)
        return results
    except Exception as exc:
        logger.error("Batch embedding generation failed: %s", exc)
        # Fallback to individual generation
        results = []
        for text in texts:
            emb = await generate_embedding(text, client)
            results.append(emb)
        return results


async def get_chroma_collections(client: httpx.AsyncClient) -> list:
    """List existing ChromaDB collections."""
    try:
        response = await client.get(
            f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/collections",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning("Could not list ChromaDB collections: %s", exc)
        return []


async def create_or_get_collection(client: httpx.AsyncClient, name: str) -> dict:
    """Create or retrieve a ChromaDB collection."""
    try:
        # Try to get existing collection
        response = await client.get(
            f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/collections/{name}",
            timeout=30.0,
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # Create new collection
    try:
        response = await client.post(
            f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/collections",
            json={"name": name, "get_or_create": True},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("Failed to create collection '%s': %s", name, exc)
        raise


async def add_to_collection(
    client: httpx.AsyncClient,
    collection_id: str,
    ids: list,
    embeddings: list,
    documents: list,
    metadatas: list,
) -> bool:
    """Add documents to a ChromaDB collection."""
    try:
        response = await client.post(
            f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/collections/{collection_id}/add",
            json={
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents,
                "metadatas": metadatas,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to add documents to collection: %s", exc)
        return False


async def delete_from_collection(
    client: httpx.AsyncClient,
    collection_id: str,
    source_file: str,
) -> bool:
    """Delete documents from a collection by source file metadata."""
    try:
        response = await client.post(
            f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/collections/{collection_id}/delete",
            json={"where": {"source_file": source_file}},
            timeout=30.0,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to delete from collection: %s", exc)
        return False


async def index_file(
    file_path: Path,
    category: str,
    subcategory: str,
    collection_name: str,
    client: httpx.AsyncClient,
    force: bool = False,
) -> dict:
    """Index a single file into ChromaDB."""
    result = {
        "file": str(file_path),
        "chunks": 0,
        "indexed": 0,
        "errors": 0,
    }

    if file_path.suffix == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read %s: %s", file_path, exc)
            result["errors"] += 1
            return result

        # Convert JSON data to indexable text chunks
        if isinstance(data, dict):
            # Skip manifest files
            if "download_date" in data and "file_list" in data:
                return result
            text_content = json.dumps(data, indent=2)
        elif isinstance(data, list):
            # For lists of records, create individual chunks per record or batch
            text_content = json.dumps(data, indent=2)
        else:
            text_content = str(data)
    elif file_path.suffix in (".txt", ".md", ".csv"):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                text_content = fh.read()
        except OSError as exc:
            logger.error("Failed to read %s: %s", file_path, exc)
            result["errors"] += 1
            return result
    else:
        logger.debug("Skipping unsupported file type: %s", file_path)
        return result

    chunks = chunk_text(text_content)
    result["chunks"] = len(chunks)

    if not chunks:
        return result

    # Get or create collection
    collection = await create_or_get_collection(client, collection_name)
    collection_id = collection.get("id")
    if not collection_id:
        logger.error("Could not obtain collection ID for '%s'", collection_name)
        result["errors"] += 1
        return result

    # If force, delete existing documents from this source file
    if force:
        await delete_from_collection(client, collection_id, str(file_path))

    # Process chunks in batches
    batch_size = 16
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        batch_end = min(batch_start + batch_size, len(chunks))

        # Generate embeddings
        try:
            embeddings = await generate_embeddings_batch(batch, client)
        except Exception as exc:
            logger.error("Embedding failed for batch starting at chunk %d: %s", batch_start, exc)
            result["errors"] += len(batch)
            continue

        if len(embeddings) != len(batch):
            logger.error(
                "Embedding count mismatch: got %d, expected %d",
                len(embeddings), len(batch),
            )
            result["errors"] += len(batch)
            continue

        # Prepare IDs, documents, and metadata
        ids = [
            f"{file_path.stem}_chunk_{batch_start + i}"
            for i in range(len(batch))
        ]
        metadatas = [
            {
                "source_file": str(file_path),
                "category": category,
                "subcategory": subcategory,
                "chunk_index": batch_start + i,
                "total_chunks": len(chunks),
            }
            for i in range(len(batch))
        ]

        success = await add_to_collection(
            client, collection_id, ids, embeddings, batch, metadatas
        )
        if success:
            result["indexed"] += len(batch)
        else:
            result["errors"] += len(batch)

    return result


async def index_category(
    category: str,
    client: httpx.AsyncClient,
    force: bool = False,
    collection_name: Optional[str] = None,
) -> dict:
    """Index all files for a given category."""
    category_path = Path(DATA_ROOT) / category
    if not category_path.exists():
        logger.warning("Category directory does not exist: %s", category_path)
        return {"category": category, "total_files": 0, "total_chunks": 0, "total_indexed": 0, "total_errors": 0}

    coll_name = collection_name or f"{category}_knowledge"
    results = []
    total_files = 0
    total_chunks = 0
    total_indexed = 0
    total_errors = 0

    # Find all data files recursively
    for file_path in sorted(category_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name == "manifest.json":
            continue
        if file_path.suffix not in (".json", ".txt", ".md", ".csv"):
            continue

        # Determine subcategory from path
        relative = file_path.relative_to(category_path)
        parts = relative.parts
        subcategory = parts[0] if len(parts) > 1 else "general"

        total_files += 1
        logger.info(
            "[%s] Indexing: %s (%d/%d)",
            category, file_path.name, total_files, "?",
        )

        result = await index_file(
            file_path, category, subcategory, coll_name, client, force,
        )
        results.append(result)
        total_chunks += result["chunks"]
        total_indexed += result["indexed"]
        total_errors += result["errors"]

        logger.info(
            "  -> %d chunks, %d indexed, %d errors",
            result["chunks"], result["indexed"], result["errors"],
        )

    return {
        "category": category,
        "collection": coll_name,
        "total_files": total_files,
        "total_chunks": total_chunks,
        "total_indexed": total_indexed,
        "total_errors": total_errors,
        "file_results": results,
    }


async def index_all(
    categories: Optional[list] = None,
    force: bool = False,
    collection_name: Optional[str] = None,
) -> list:
    """Index all knowledge bases into ChromaDB."""
    cats = categories or CATEGORIES
    all_results = []

    async with httpx.AsyncClient() as client:
        # Check Ollama availability
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=10.0)
            resp.raise_for_status()
            logger.info("Ollama is available")
        except Exception as exc:
            logger.error("Ollama is not available at %s: %s", OLLAMA_URL, exc)
            logger.error("Please start Ollama and ensure nomic-embed-text model is pulled")
            return []

        # Check ChromaDB availability
        try:
            resp = await client.get(f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/heartbeat", timeout=10.0)
            resp.raise_for_status()
            logger.info("ChromaDB is available")
        except Exception as exc:
            logger.error("ChromaDB is not available at %s:%d: %s", CHROMA_HOST, CHROMA_PORT, exc)
            logger.error("Please start ChromaDB server")
            return []

        for category in cats:
            if category not in CATEGORIES:
                logger.warning("Unknown category: %s, skipping", category)
                continue

            logger.info("=" * 60)
            logger.info("Indexing category: %s", category)
            logger.info("=" * 60)

            result = await index_category(category, client, force, collection_name)
            all_results.append(result)

            logger.info(
                "[%s] Complete: %d files, %d chunks, %d indexed, %d errors",
                category,
                result["total_files"],
                result["total_chunks"],
                result["total_indexed"],
                result["total_errors"],
            )

    # Save index report
    report_path = Path(DATA_ROOT) / "index_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "results": all_results,
            },
            fh,
            indent=2,
        )
    logger.info("Index report saved to %s", report_path)
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Index all AetheraAI knowledge bases into ChromaDB"
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=CATEGORIES,
        help="Filter to specific categories (can be repeated)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-index even if documents already exist",
    )
    parser.add_argument(
        "--collection",
        type=str,
        help="Override collection name (default: <category>_knowledge)",
    )
    args = parser.parse_args()
    asyncio.run(index_all(
        categories=args.category,
        force=args.force,
        collection_name=args.collection,
    ))


if __name__ == "__main__":
    main()