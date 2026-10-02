"""
Enterprise RAG System Contracts & Data Invariants.

This module defines deterministic schemas, TypeDicts, and runtime invariant validators
used across the entire pipeline (Ingestion -> Indexing -> Retrieval -> Generation -> Evaluation).
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict


RetrievalMethod = Literal["dense", "bm25", "hybrid", "pageindex", "reranked"]
RetrievalSource = Literal["hybrid", "dense", "bm25", "pageindex", "none"]


class DocumentMetadata(TypedDict, total=False):
    source: str
    title: str
    doc_type: str
    url: Optional[str]
    created_at: Optional[str]
    extra: Optional[Dict[str, Any]]


class ChunkMetadata(DocumentMetadata):
    chunk_index: int
    parent_id: Optional[str]
    char_count: Optional[int]


class Document(TypedDict):
    id: str
    content: str
    metadata: DocumentMetadata


class Chunk(TypedDict):
    id: str
    content: str
    metadata: ChunkMetadata


class EmbeddedChunk(Chunk):
    embedding: List[float]


class SearchResult(TypedDict):
    id: str
    content: str
    score: float
    metadata: ChunkMetadata
    retrieval_method: RetrievalMethod


class GenerationResult(TypedDict):
    answer: str
    sources: List[SearchResult]
    retrieval_source: RetrievalSource


class EvaluationCase(TypedDict):
    question: str
    expected_answer: str
    expected_context: str


class EvaluationResult(TypedDict):
    question: str
    generated_answer: str
    retrieved_contexts: List[str]
    faithfulness_score: float
    answer_relevance_score: float
    context_recall_score: float
    context_precision_score: float


# ============================================================================
# Invariant Validation Functions
# ============================================================================

def validate_document(item: Any, *, require_chunk: bool = False) -> None:
    """Validates structural and data integrity of a Document or Chunk."""
    if not isinstance(item, dict):
        raise ValueError("Item must be a dictionary")
    if not isinstance(item.get("id"), str) or not item["id"].strip():
        raise ValueError("Field 'id' must be a non-empty string")
    if not isinstance(item.get("content"), str) or not item["content"].strip():
        raise ValueError("Field 'content' must be a non-empty string")

    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Field 'metadata' must be a dictionary")

    for key in ("source", "title"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"metadata.{key} must be a non-empty string")

    if require_chunk:
        chunk_idx = metadata.get("chunk_index")
        if not isinstance(chunk_idx, int) or chunk_idx < 0:
            raise ValueError("metadata.chunk_index must be a non-negative integer for chunks")


def validate_search_results(
    results: Any,
    *,
    top_k: Optional[int] = None,
    expected_method: Optional[RetrievalMethod] = None,
) -> None:
    """
    Validates SearchResult array properties:
    - Proper schema conformance.
    - Result count <= top_k.
    - Unique chunk IDs (no duplicate elements).
    - Monotonically decreasing score order (sorted descending).
    - Match expected retrieval method if specified.
    """
    if not isinstance(results, list):
        raise ValueError("Search results must be a list")
    if top_k is not None and len(results) > max(top_k, 0):
        raise ValueError(f"Search results length ({len(results)}) exceeds top_k ({top_k})")

    ids: List[str] = []
    scores: List[float] = []
    valid_methods = {"dense", "bm25", "hybrid", "pageindex", "reranked"}

    for item in results:
        validate_document(item, require_chunk=True)
        score = item.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("SearchResult.score must be numeric")
        method = item.get("retrieval_method")
        if method not in valid_methods:
            raise ValueError(f"SearchResult.retrieval_method '{method}' is not in {valid_methods}")
        if expected_method is not None and method != expected_method:
            raise ValueError(f"Expected retrieval_method '{expected_method}', got '{method}'")

        ids.append(item["id"])
        scores.append(float(score))

    if len(ids) != len(set(ids)):
        raise ValueError("SearchResult list contains duplicate IDs")
    if scores != sorted(scores, reverse=True):
        raise ValueError("SearchResult list must be strictly sorted by score descending")


def validate_generation_result(result: Any) -> None:
    """Validates the structure and sources of a GenerationResult."""
    if not isinstance(result, dict):
        raise ValueError("GenerationResult must be a dictionary")
    if not isinstance(result.get("answer"), str) or not result["answer"].strip():
        raise ValueError("GenerationResult.answer must be a non-empty string")
    validate_search_results(result.get("sources", []))
    valid_sources = {"hybrid", "dense", "bm25", "pageindex", "none"}
    if result.get("retrieval_source") not in valid_sources:
        raise ValueError(f"GenerationResult.retrieval_source is invalid. Must be one of {valid_sources}")
