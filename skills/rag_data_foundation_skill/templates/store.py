"""
Pluggable Vector Store Engine & Indexing Abstraction.

Implements BaseVectorStore with InMemoryVectorStore (production-grade pure Python
with exact cosine ranking and metadata pre-filtering) and ChromaVectorStore adapter.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from .embeddings import MockEmbedder, cosine_similarity
from .models import Chunk, Document, QueryResult

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Abstract Vector Store contract."""

    @abstractmethod
    def add_documents(self, documents: List[Union[Document, Chunk]]) -> None:
        """Embed and persist documents or pre-segmented chunks."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[QueryResult]:
        """Perform semantic nearest-neighbor search for a query string."""
        pass

    @abstractmethod
    def search_with_filter(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        """Perform similarity search with structured metadata pre-filtering."""
        pass

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """Remove all records/chunks associated with a document ID."""
        pass

    @abstractmethod
    def get_collection_size(self) -> int:
        """Return total number of vector records in store."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """
    High-performance in-memory vector store with deterministic scoring,
    multi-attribute metadata pre-filtering, and zero external infrastructure dependencies.
    """

    def __init__(
        self,
        collection_name: str = "default_collection",
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        self.collection_name = collection_name
        self.embedding_fn = embedding_fn or MockEmbedder()
        self._records: List[Dict[str, Any]] = []

    def _make_record(self, item: Union[Document, Chunk]) -> Dict[str, Any]:
        """Convert a Document or Chunk into an internal vector record."""
        item_id = item.id
        content = item.content
        parent_id = getattr(item, "parent_doc_id", item.metadata.get("doc_id", item_id))
        metadata = dict(item.metadata)

        # Store doc_id in metadata for consistent deletion lookup
        if "doc_id" not in metadata:
            metadata["doc_id"] = parent_id

        # Calculate embedding if not already cached
        embedding = getattr(item, "embedding", None)
        if embedding is None:
            embedding = self.embedding_fn(content)

        return {
            "id": item_id,
            "parent_doc_id": parent_id,
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }

    def add_documents(self, documents: List[Union[Document, Chunk]]) -> None:
        for doc in documents:
            if not doc.content.strip():
                continue
            record = self._make_record(doc)
            self._records.append(record)

    def _matches_filter(self, record_metadata: Dict[str, Any], metadata_filter: Optional[Dict[str, Any]]) -> bool:
        if not metadata_filter:
            return True
        for key, expected_val in metadata_filter.items():
            if record_metadata.get(key) != expected_val:
                return False
        return True

    def _rank_records(self, query_vector: List[float], records: List[Dict[str, Any]], top_k: int) -> List[QueryResult]:
        if not records:
            return []

        scored: List[tuple[float, Dict[str, Any]]] = []
        for rec in records:
            score = cosine_similarity(query_vector, rec["embedding"])
            scored.append((score, rec))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[QueryResult] = []
        for score, rec in scored[:top_k]:
            results.append(
                QueryResult(
                    id=rec["id"],
                    parent_doc_id=rec["parent_doc_id"],
                    content=rec["content"],
                    score=score,
                    metadata=rec["metadata"],
                )
            )
        return results

    def search(self, query: str, top_k: int = 5) -> List[QueryResult]:
        return self.search_with_filter(query=query, top_k=top_k, metadata_filter=None)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        if not self._records:
            return []

        # Step 1: Pre-filter candidate records
        candidates = [rec for rec in self._records if self._matches_filter(rec["metadata"], metadata_filter)]
        if not candidates:
            return []

        # Step 2: Embed query & rank
        query_vector = self.embedding_fn(query)
        return self._rank_records(query_vector, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        initial_count = len(self._records)
        self._records = [
            rec for rec in self._records
            if rec["id"] != doc_id
            and rec["parent_doc_id"] != doc_id
            and rec["metadata"].get("doc_id") != doc_id
            and rec["metadata"].get("parent_id") != doc_id
        ]
        return len(self._records) < initial_count

    def get_collection_size(self) -> int:
        return len(self._records)


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB persistent vector store adapter with automatic fallback to InMemoryVectorStore.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
        persist_directory: Optional[str] = None,
    ) -> None:
        self.collection_name = collection_name
        self.embedding_fn = embedding_fn or MockEmbedder()
        self._fallback_store = InMemoryVectorStore(collection_name, self.embedding_fn)
        self._use_chroma = False
        self._collection = None

        try:
            import chromadb
            if persist_directory:
                client = chromadb.PersistentClient(path=persist_directory)
            else:
                client = chromadb.Client()
            self._collection = client.get_or_create_collection(name=collection_name)
            self._use_chroma = True
            logger.info("Successfully connected to ChromaDB collection '%s'", collection_name)
        except Exception as err:
            logger.warning("ChromaDB initialization failed (%s). Falling back to InMemoryVectorStore.", err)
            self._use_chroma = False

    def add_documents(self, documents: List[Union[Document, Chunk]]) -> None:
        if not self._use_chroma or self._collection is None:
            return self._fallback_store.add_documents(documents)

        ids: List[str] = []
        texts: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []

        for doc in documents:
            if not doc.content.strip():
                continue
            item_id = doc.id
            content = doc.content
            meta = dict(doc.metadata)
            meta["doc_id"] = getattr(doc, "parent_doc_id", meta.get("doc_id", item_id))

            emb = getattr(doc, "embedding", None) or self.embedding_fn(content)

            ids.append(item_id)
            texts.append(content)
            embeddings.append(emb)
            metadatas.append(meta)

        if ids:
            self._collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    def search(self, query: str, top_k: int = 5) -> List[QueryResult]:
        return self.search_with_filter(query=query, top_k=top_k, metadata_filter=None)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        if not self._use_chroma or self._collection is None:
            return self._fallback_store.search_with_filter(query, top_k, metadata_filter)

        query_emb = self.embedding_fn(query)
        where_clause = metadata_filter if metadata_filter else None

        results = self._collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            where=where_clause,
        )

        output: List[QueryResult] = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for item_id, doc_text, meta, dist in zip(ids, docs, metas, distances):
                # Convert Chroma distance to similarity score
                score = 1.0 / (1.0 + max(0.0, dist))
                output.append(
                    QueryResult(
                        id=item_id,
                        parent_doc_id=meta.get("doc_id"),
                        content=doc_text,
                        score=score,
                        metadata=meta,
                    )
                )
        return output

    def delete_document(self, doc_id: str) -> bool:
        if not self._use_chroma or self._collection is None:
            return self._fallback_store.delete_document(doc_id)

        try:
            self._collection.delete(where={"doc_id": doc_id})
            return True
        except Exception:
            return False

    def get_collection_size(self) -> int:
        if not self._use_chroma or self._collection is None:
            return self._fallback_store.get_collection_size()
        return self._collection.count()
