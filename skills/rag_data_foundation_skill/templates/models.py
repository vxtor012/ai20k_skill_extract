"""
Domain-Agnostic Core Data Models for Vector Pipelines and RAG Systems.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """
    Standard domain-agnostic raw document representation.
    
    Attributes:
        id: Unique identifier string for the document.
        content: Raw text content.
        metadata: Key-value dictionary containing lineage, origin, permissions, and domain tags.
        created_at: Unix epoch timestamp when the document was loaded.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Document:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class Chunk:
    """
    A segmented portion of a Document, ready for embedding and indexing.
    
    Attributes:
        id: Unique chunk identifier (e.g. '{parent_doc_id}_chunk_{index}').
        parent_doc_id: Foreign key back to the parent Document.id.
        content: Chunk textual payload.
        chunk_index: Sequential index position within parent document.
        metadata: Propagated + chunk-specific metadata (e.g. token_count, start_char, end_char).
        embedding: Dense vector representation (None until embedded).
    """
    id: str
    parent_doc_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_doc_id": self.parent_doc_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }


@dataclass
class QueryResult:
    """
    Search result item returned from vector retrieval.
    
    Attributes:
        id: Chunk ID or Document ID retrieved.
        parent_doc_id: Parent document identifier.
        content: Text content retrieved.
        score: Relevance/similarity score (e.g. Cosine Similarity in [-1, 1] or [0, 1]).
        metadata: Associated metadata dictionary.
    """
    id: str
    content: str
    score: float
    parent_doc_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": round(self.score, 4),
            "parent_doc_id": self.parent_doc_id,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkQuery:
    """
    Evaluation query with ground-truth references for RAG benchmarking.
    
    Attributes:
        query_id: Unique benchmark query identifier.
        query_text: The user query string.
        expected_doc_ids: Set/List of doc IDs or chunk IDs considered relevant.
        ground_truth_answer: Optional reference text answer.
        metadata_filter: Optional pre-filter to test structured query constraints.
    """
    query_id: str
    query_text: str
    expected_doc_ids: List[str] = field(default_factory=list)
    ground_truth_answer: Optional[str] = None
    metadata_filter: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    """
    Summary metrics evaluating retrieval or RAG performance across test queries.
    """
    strategy_name: str
    total_queries: int
    hit_rate_at_k: float
    mrr_at_k: float
    avg_latency_ms: float
    details: List[Dict[str, Any]] = field(default_factory=list)
