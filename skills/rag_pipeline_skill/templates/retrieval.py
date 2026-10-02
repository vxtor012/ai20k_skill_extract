"""
Enterprise Hybrid Retrieval Engine with RRF & Adaptive Fallback.

Combines Dense Semantic Search (Bi-encoder embeddings) and Sparse Lexical Search (BM25),
fuses rankings using Reciprocal Rank Fusion (RRF), and triggers fallback routing when
dense semantic confidence drops below calibrated threshold.
"""

from typing import Callable, Dict, List, Optional
from rank_bm25 import BM25Okapi
from .contracts import Chunk, SearchResult


class BM25LexicalIndex:
    """In-memory BM25 lexical search engine over chunk corpus."""

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.corpus_ids = [c["id"] for c in chunks]
        self.tokenized_corpus = [self._tokenize(c["content"]) for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return text.lower().replace("\n", " ").split()

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        if not self.bm25 or not self.chunks:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        scored_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results: List[SearchResult] = []
        for idx in scored_indices:
            chunk = self.chunks[idx]
            results.append({
                "id": chunk["id"],
                "content": chunk["content"],
                "score": float(scores[idx]),
                "metadata": chunk["metadata"],
                "retrieval_method": "bm25",
            })
        return results


def reciprocal_rank_fusion(
    ranked_lists: List[List[SearchResult]],
    top_k: int = 5,
    k: int = 60,
) -> List[SearchResult]:
    """
    Fuses multiple ranked result lists using Reciprocal Rank Fusion (RRF).
    Formula: RRF_score(d) = sum(1 / (k + rank_i(d)))
    """
    scores: Dict[str, float] = {}
    items: Dict[str, SearchResult] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank))
            if item_id not in items:
                items[item_id] = item

    sorted_ids = sorted(scores.keys(), key=lambda doc_id: scores[doc_id], reverse=True)

    fused_results: List[SearchResult] = []
    for item_id in sorted_ids[:top_k]:
        item_copy = dict(items[item_id])
        item_copy["score"] = scores[item_id]
        item_copy["retrieval_method"] = "hybrid"
        fused_results.append(item_copy)  # type: ignore

    return fused_results


class HybridRetrievalPipeline:
    """
    Orchestrates Dense + Lexical retrieval, single-pass RRF fusion,
    and threshold-based fallback routing.
    """

    def __init__(
        self,
        dense_search_fn: Callable[[str, int], List[SearchResult]],
        lexical_search_fn: Callable[[str, int], List[SearchResult]],
        fallback_search_fn: Optional[Callable[[str, int], List[SearchResult]]] = None,
        dense_score_threshold: float = 0.35,
        default_top_k: int = 5,
        rrf_k: int = 60,
    ):
        self.dense_search_fn = dense_search_fn
        self.lexical_search_fn = lexical_search_fn
        self.fallback_search_fn = fallback_search_fn
        self.dense_score_threshold = dense_score_threshold
        self.default_top_k = default_top_k
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        use_reranking: bool = True,
    ) -> List[SearchResult]:
        k_val = top_k or self.default_top_k
        threshold = score_threshold if score_threshold is not None else self.dense_score_threshold

        # Step 1: Overfetch candidate chunks from dense and sparse retrievers
        dense_results = self.dense_search_fn(query, k_val * 2)
        sparse_results = self.lexical_search_fn(query, k_val * 2)

        # Step 2: Fuse candidates using RRF (exactly once)
        if use_reranking:
            fused_results = reciprocal_rank_fusion([dense_results, sparse_results], top_k=k_val, k=self.rrf_k)
        else:
            fused_results = dense_results[:k_val]

        # Step 3: Check dense similarity score against threshold (NEVER threshold against RRF score)
        best_dense_score = dense_results[0]["score"] if dense_results else 0.0

        if best_dense_score < threshold and self.fallback_search_fn is not None:
            try:
                fallback_results = self.fallback_search_fn(query, k_val)
                if fallback_results:
                    return fallback_results[:k_val]
            except Exception:
                # Fault tolerance: fallback failure returns hybrid results gracefully
                pass

        return fused_results[:k_val]
