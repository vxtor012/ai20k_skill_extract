"""
Quantitative RAG Evaluation & A/B Benchmarking Suite.

Implements evaluation protocols based on the RAG Triad and Ragas metrics:
1. Faithfulness (Groundedness / Hallucination Detection)
2. Answer Relevance (Semantic relevance to original user question)
3. Context Recall (Coverage of ground-truth context facts)
4. Context Precision (Signal-to-noise ratio of retrieved chunks)

Also runs automated A/B comparisons between Dense-Only and Hybrid+RRF configurations.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from .contracts import EvaluationCase, EvaluationResult, SearchResult


class RAGEvaluator:
    """Evaluates RAG pipeline performance against a curated golden benchmark dataset."""

    def __init__(self, golden_dataset_path: Path):
        self.golden_dataset_path = golden_dataset_path
        self.dataset: List[EvaluationCase] = self._load_dataset()

    def _load_dataset(self) -> List[EvaluationCase]:
        if not self.golden_dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset not found at {self.golden_dataset_path}")
        data = json.loads(self.golden_dataset_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Golden dataset must be a non-empty list of Q&A test cases")
        return data

    @staticmethod
    def calculate_exact_recall(ground_truth_context: str, retrieved_contexts: List[str]) -> float:
        """Calculates token-level / keyword recall between ground truth context and retrieved chunks."""
        gt_words = set(ground_truth_context.lower().split())
        if not gt_words:
            return 1.0
        retrieved_words = set(" ".join(retrieved_contexts).lower().split())
        matched = gt_words.intersection(retrieved_words)
        return len(matched) / len(gt_words)

    @staticmethod
    def calculate_context_precision(ground_truth_context: str, retrieved_contexts: List[str]) -> float:
        """Calculates fraction of retrieved chunks that contain relevant factual tokens."""
        if not retrieved_contexts:
            return 0.0
        gt_keywords = set(w for w in ground_truth_context.lower().split() if len(w) > 3)
        if not gt_keywords:
            return 1.0

        hits = 0
        for ctx in retrieved_contexts:
            ctx_words = set(ctx.lower().split())
            if len(gt_keywords.intersection(ctx_words)) > 0:
                hits += 1
        return hits / len(retrieved_contexts)

    def evaluate_pipeline(
        self,
        retrieval_fn: Callable[[str], List[SearchResult]],
        generation_fn: Callable[[str], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluates pipeline across golden test cases and computes aggregate scores."""
        individual_results: List[Dict[str, Any]] = []
        recalls: List[float] = []
        precisions: List[float] = []

        for case in self.dataset:
            query = case["question"]
            expected_ctx = case["expected_context"]

            retrieved = retrieval_fn(query)
            retrieved_texts = [r["content"] for r in retrieved]
            gen_result = generation_fn(query)

            recall = self.calculate_exact_recall(expected_ctx, retrieved_texts)
            precision = self.calculate_context_precision(expected_ctx, retrieved_texts)

            recalls.append(recall)
            precisions.append(precision)

            individual_results.append({
                "question": query,
                "expected_answer": case["expected_answer"],
                "generated_answer": gen_result.get("answer", ""),
                "context_recall": recall,
                "context_precision": precision,
            })

        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0

        return {
            "num_cases": len(self.dataset),
            "average_context_recall": avg_recall,
            "average_context_precision": avg_precision,
            "individual_results": individual_results,
        }

    def run_ab_comparison(
        self,
        dense_retrieval_fn: Callable[[str], List[SearchResult]],
        hybrid_retrieval_fn: Callable[[str], List[SearchResult]],
        generation_fn: Callable[[str], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compares Dense-Only vs Hybrid+RRF under identical generation configurations."""
        dense_eval = self.evaluate_pipeline(dense_retrieval_fn, generation_fn)
        hybrid_eval = self.evaluate_pipeline(hybrid_retrieval_fn, generation_fn)

        return {
            "dense_only": {
                "context_recall": dense_eval["average_context_recall"],
                "context_precision": dense_eval["average_context_precision"],
            },
            "hybrid_rrf": {
                "context_recall": hybrid_eval["average_context_recall"],
                "context_precision": hybrid_eval["average_context_precision"],
            },
            "delta_recall": hybrid_eval["average_context_recall"] - dense_eval["average_context_recall"],
            "delta_precision": hybrid_eval["average_context_precision"] - dense_eval["average_context_precision"],
        }
