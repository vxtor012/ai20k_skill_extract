"""
Quantitative RAG & Vector Retrieval Evaluation Harness.

Computes precision metrics (Hit Rate@K, Mean Reciprocal Rank @ K) and latency
benchmarks across standard queries and ground truth sets.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .models import BenchmarkQuery, EvaluationResult
from .store import BaseVectorStore


class RetrievalEvaluator:
    """
    Evaluates vector store retrieval quality against labeled benchmark queries.
    """

    def __init__(self, store: BaseVectorStore) -> None:
        self.store = store

    def evaluate_query(self, query: BenchmarkQuery, top_k: int = 3) -> Dict[str, Any]:
        """
        Evaluate a single benchmark query:
        - Check if any expected_doc_id is present in top-k results (Hit)
        - Find first rank position of expected doc (Reciprocal Rank)
        """
        start_time = time.perf_counter()
        results = self.store.search_with_filter(
            query=query.query_text,
            top_k=top_k,
            metadata_filter=query.metadata_filter,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        retrieved_ids = [r.parent_doc_id or r.id for r in results]
        expected_set = set(query.expected_doc_ids)

        hit = 0
        reciprocal_rank = 0.0

        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in expected_set or any(doc_id.startswith(exp) for exp in expected_set):
                hit = 1
                reciprocal_rank = 1.0 / rank
                break

        return {
            "query_id": query.query_id,
            "query_text": query.query_text,
            "top_k": top_k,
            "retrieved_ids": retrieved_ids,
            "expected_ids": query.expected_doc_ids,
            "hit": hit,
            "reciprocal_rank": reciprocal_rank,
            "latency_ms": round(latency_ms, 2),
        }

    def run_benchmark(
        self,
        benchmark_queries: List[BenchmarkQuery],
        top_k: int = 3,
        strategy_name: str = "default_strategy",
    ) -> EvaluationResult:
        """
        Run a full evaluation batch and compute aggregate Hit Rate@K, MRR@K, and avg latency.
        """
        if not benchmark_queries:
            return EvaluationResult(
                strategy_name=strategy_name,
                total_queries=0,
                hit_rate_at_k=0.0,
                mrr_at_k=0.0,
                avg_latency_ms=0.0,
            )

        details: List[Dict[str, Any]] = []
        total_hits = 0
        total_rr = 0.0
        total_latency = 0.0

        for bq in benchmark_queries:
            detail = self.evaluate_query(bq, top_k=top_k)
            details.append(detail)
            total_hits += detail["hit"]
            total_rr += detail["reciprocal_rank"]
            total_latency += detail["latency_ms"]

        num_queries = len(benchmark_queries)
        return EvaluationResult(
            strategy_name=strategy_name,
            total_queries=num_queries,
            hit_rate_at_k=round(total_hits / num_queries, 4),
            mrr_at_k=round(total_rr / num_queries, 4),
            avg_latency_ms=round(total_latency / num_queries, 2),
            details=details,
        )
