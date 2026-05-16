"""
Aethera AI - Vector Store Module

ChromaDB operations for RAG (Retrieval Augmented Generation).
Stores embeddings of healthcare knowledge bases, user memories, and documents.
"""

import asyncio
import hashlib
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")


@dataclass
class Document:
    """Document for vector storage."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class VectorStore:
    """
    ChromaDB vector store for RAG.

    Collections:
    - healthcare_knowledge: Medical coding, regulations, guidelines
    - finance_knowledge: Financial data, regulations
    - legal_knowledge: Legal data, case law
    - technology_knowledge: Tech reference data
    - user_memories: User preferences, facts, learned information
    - documents: Uploaded and processed documents
    - conversations: Embedded conversation history
    """

    def __init__(self, chromadb_url: str = "http://chromadb:8000"):
        self.chromadb_url = chromadb_url
        self._session: Optional[httpx.AsyncClient] = None
        self._collections: Dict[str, str] = {}  # name -> collection_id

    async def initialize(self):
        """Initialize connection and create collections."""
        self._session = httpx.AsyncClient(base_url=self.chromadb_url, timeout=30)

        # Create default collections
        collections = [
            "healthcare_knowledge",
            "finance_knowledge",
            "legal_knowledge",
            "technology_knowledge",
            "user_memories",
            "documents",
            "conversations"
        ]

        for name in collections:
            await self._create_collection(name)

    async def close(self):
        """Close connection."""
        if self._session:
            await self._session.aclose()

    async def _create_collection(self, name: str):
        """Create a collection if it doesn't exist."""
        try:
            response = await self._session.post(
                "/api/v1/collections",
                json={"name": name}
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self._collections[name] = data.get("id", name)
        except Exception:
            pass  # Collection may already exist

    async def add_document(
        self,
        collection: str,
        content: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store.

        Args:
            collection: Collection name
            content: Document text content
            metadata: Document metadata
            doc_id: Optional document ID

        Returns:
            Document ID
        """
        # Generate embedding
        embedding = await self._generate_embedding(content)

        # Generate ID if not provided
        if not doc_id:
            doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Add to ChromaDB
        try:
            collection_id = self._collections.get(collection, collection)
            await self._session.post(
                f"/api/v1/collections/{collection_id}/add",
                json={
                    "ids": [doc_id],
                    "embeddings": [embedding],
                    "documents": [content],
                    "metadatas": [metadata]
                }
            )
        except Exception as e:
            raise Exception(f"Failed to add document: {e}")

        return doc_id

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            collection: Collection name
            query: Search query
            top_k: Number of results
            filter_metadata: Metadata filter

        Returns:
            List of matching documents with scores
        """
        # Generate embedding for query
        embedding = await self._generate_embedding(query)

        try:
            collection_id = self._collections.get(collection, collection)
            response = await self._session.post(
                f"/api/v1/collections/{collection_id}/query",
                json={
                    "query_embeddings": [embedding],
                    "n_results": top_k,
                    "where": filter_metadata
                }
            )
            response.raise_for_status()
            data = response.json()

            # Format results
            results = []
            if data.get("ids"):
                for i, doc_id in enumerate(data["ids"][0]):
                    results.append({
                        "id": doc_id,
                        "content": data["documents"][0][i] if data.get("documents") else "",
                        "metadata": data["metadatas"][0][i] if data.get("metadatas") else {},
                        "distance": data["distances"][0][i] if data.get("distances") else 0
                    })

            return results
        except Exception as e:
            return [{"error": str(e)}]

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/embed",
                    json={
                        "model": "nomic-embed-text",
                        "input": text
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                if embeddings and isinstance(embeddings[0], list):
                    return embeddings[0]
                return data.get("embedding", [])
        except Exception:
            # Return zero vector as fallback
            return [0.0] * 768

    async def add_documents_batch(
        self,
        collection: str,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add multiple documents to the vector store in batch.

        Args:
            collection: Collection name
            contents: List of document text contents
            metadatas: Optional list of metadata dicts
            doc_ids: Optional list of document IDs

        Returns:
            List of document IDs
        """
        if not contents:
            return []

        if metadatas is None:
            metadatas = [{} for _ in contents]
        if doc_ids is None:
            doc_ids = [hashlib.sha256(c.encode()).hexdigest()[:16] for c in contents]

        # Generate embeddings in batch
        embeddings = []
        for content in contents:
            emb = await self._generate_embedding(content)
            embeddings.append(emb)

        # Add all to ChromaDB in one request
        try:
            collection_id = self._collections.get(collection, collection)
            await self._session.post(
                f"/api/v1/collections/{collection_id}/add",
                json={
                    "ids": doc_ids,
                    "embeddings": embeddings,
                    "documents": contents,
                    "metadatas": metadatas
                }
            )
        except Exception as e:
            raise Exception(f"Failed to add documents batch: {e}")

        return doc_ids

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        try:
            collection_id = self._collections.get(collection, collection)
            await self._session.post(
                f"/api/v1/collections/{collection_id}/delete",
                json={"ids": [doc_id]}
            )
            return True
        except Exception:
            return False

    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection_id = self._collections.get(collection, collection)
            response = await self._session.get(
                f"/api/v1/collections/{collection_id}"
            )
            response.raise_for_status()
            data = response.json()
            return {
                "name": data.get("name"),
                "document_count": data.get("metadata", {}).get("count", 0),
                "id": collection_id
            }
        except Exception as e:
            return {"error": str(e)}

    async def list_collections(self) -> List[str]:
        """List all collections."""
        return list(self._collections.keys())


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(chromadb_url: str = "http://chromadb:8000") -> VectorStore:
    """Get or create the vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(chromadb_url)
    return _vector_store
