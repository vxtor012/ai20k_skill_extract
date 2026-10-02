"""
Vector Database Adapter Module.

Provides persistent storage, metadata indexing, idempotent upserting,
and dense semantic vector search with cosine similarity scoring.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from .contracts import Chunk, SearchResult


class ChromaVectorStore:
    """ChromaDB persistent vector store adapter."""

    def __init__(
        self,
        persist_dir: str = "vector_db",
        collection_name: str = "enterprise_knowledge_base",
    ):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def upsert_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Idempotently upserts chunks with their embedding vectors and metadata."""
        if not chunks:
            return

        collection = self._get_collection()
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["content"] for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk["metadata"] for chunk in chunks],
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Performs dense vector similarity search, mapping distance to cosine similarity score [0, 1]."""
        collection = self._get_collection()
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        response = collection.query(**query_kwargs)

        results: List[SearchResult] = []
        if not response or not response["ids"] or not response["ids"][0]:
            return results

        ids = response["ids"][0]
        docs = response["documents"][0]
        metas = response["metadatas"][0]
        distances = response["distances"][0]

        for item_id, content, metadata, distance in zip(ids, docs, metas, distances):
            # Chroma cosine distance = 1 - cosine_similarity. Similarity = 1 - distance.
            similarity_score = max(0.0, 1.0 - float(distance))
            results.append({
                "id": item_id,
                "content": content,
                "score": similarity_score,
                "metadata": metadata,  # type: ignore
                "retrieval_method": "dense",
            })

        # Ensure strict descending sort by score
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
