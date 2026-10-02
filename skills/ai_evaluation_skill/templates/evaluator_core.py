"""Generalized Evaluation Core Metrics Engine for Generation & Retrieval."""

from __future__ import annotations

import re
from typing import Sequence

from .models import EvalResult, FailureType, QAPair

DEFAULT_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "as", "by", "and", "or",
    "it", "its", "this", "that", "these", "those", "from", "into", "than",
    "but", "not", "have", "had", "has", "do", "does", "did", "can", "will",
})


def tokenize_text(text: str, stopwords: frozenset[str] = DEFAULT_STOPWORDS) -> set[str]:
    """Extract lowercase word tokens excluding stopwords and punctuation."""
    if not text:
        return set()
    tokens = re.findall(r"\b\w+\b", text.lower())
    return {t for t in tokens if t not in stopwords}


class GenericRAGEvaluator:
    """
    RAG & AI Output Evaluator computing foundational evaluation metrics:
    - Faithfulness (Grounding of answer in provided context)
    - Answer Relevance (Alignment of answer to the user's question)
    - Answer Completeness (Coverage of the expected answer)
    - Context Recall (Retrieved context coverage of ground truth)
    - Context Precision (Rank-aware Average Precision AP@K of retrieved chunks)
    """

    def __init__(
        self,
        pass_threshold: float = 0.5,
        hallucination_threshold: float = 0.3,
        relevance_threshold: float = 0.3,
        completeness_threshold: float = 0.3,
        chunk_relevance_threshold: float = 0.1,
    ) -> None:
        self.pass_threshold = pass_threshold
        self.hallucination_threshold = hallucination_threshold
        self.relevance_threshold = relevance_threshold
        self.completeness_threshold = completeness_threshold
        self.chunk_relevance_threshold = chunk_relevance_threshold

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        """Measure what fraction of answer tokens are supported by the context."""
        answer_tokens = tokenize_text(answer)
        if not answer_tokens:
            return 1.0
        context_tokens = tokenize_text(context)
        score = len(answer_tokens & context_tokens) / len(answer_tokens)
        return max(0.0, min(1.0, score))

    def evaluate_relevance(self, answer: str, question: str) -> float:
        """Measure semantic/lexical overlap between answer and original question."""
        question_tokens = tokenize_text(question)
        if not question_tokens:
            return 1.0
        answer_tokens = tokenize_text(answer)
        score = len(answer_tokens & question_tokens) / len(question_tokens)
        return max(0.0, min(1.0, score))

    def evaluate_completeness(self, answer: str, expected_answer: str) -> float:
        """Measure coverage of expected answer elements present in the actual answer."""
        expected_tokens = tokenize_text(expected_answer)
        if not expected_tokens:
            return 1.0
        answer_tokens = tokenize_text(answer)
        score = len(answer_tokens & expected_tokens) / len(expected_tokens)
        return max(0.0, min(1.0, score))

    def evaluate_context_recall(self, contexts: Sequence[str], expected_answer: str) -> float:
        """Measure fraction of expected ground truth covered by the union of retrieved chunks."""
        expected_tokens = tokenize_text(expected_answer)
        if not expected_tokens:
            return 1.0
        union_tokens: set[str] = set()
        for chunk in contexts:
            union_tokens |= tokenize_text(chunk)
        score = len(expected_tokens & union_tokens) / len(expected_tokens)
        return max(0.0, min(1.0, score))

    def evaluate_context_precision(
        self,
        contexts: Sequence[str],
        expected_answer: str,
        relevance_threshold: float | None = None,
    ) -> float:
        """
        Rank-aware Context Precision via Average Precision (AP@K).
        Rewards retrievers that place relevant chunks at the top of the candidate list.
        """
        threshold = relevance_threshold if relevance_threshold is not None else self.chunk_relevance_threshold
        expected_tokens = tokenize_text(expected_answer)
        if not expected_tokens:
            return 1.0
        if not contexts:
            return 0.0

        is_relevant_flags: list[bool] = []
        for chunk in contexts:
            chunk_tokens = tokenize_text(chunk)
            coverage = len(chunk_tokens & expected_tokens) / len(expected_tokens)
            is_relevant_flags.append(coverage >= threshold)

        total_relevant = sum(1 for flag in is_relevant_flags if flag)
        if total_relevant == 0:
            return 0.0

        sum_precision = 0.0
        relevant_counter = 0
        for k, is_rel in enumerate(is_relevant_flags, start=1):
            if is_rel:
                relevant_counter += 1
                precision_at_k = relevant_counter / k
                sum_precision += precision_at_k

        return max(0.0, min(1.0, sum_precision / total_relevant))

    def evaluate_sample(
        self,
        qa_pair: QAPair,
        actual_answer: str,
        retrieved_contexts: list[str] | None = None,
        latency_seconds: float | None = None,
        error_message: str | None = None,
    ) -> EvalResult:
        """Run full evaluation suite on a single inference sample."""
        if error_message:
            return EvalResult(
                qa_pair=qa_pair,
                actual_answer=actual_answer,
                faithfulness=0.0,
                relevance=0.0,
                completeness=0.0,
                passed=False,
                failure_type=FailureType.TIMEOUT_OR_ERROR,
                latency_seconds=latency_seconds,
                error_message=error_message,
            )

        context_str = qa_pair.context or ""
        faithfulness = self.evaluate_faithfulness(actual_answer, context_str)
        relevance = self.evaluate_relevance(actual_answer, qa_pair.question)
        completeness = self.evaluate_completeness(actual_answer, qa_pair.expected_answer)

        passed = (
            faithfulness >= self.pass_threshold
            and relevance >= self.pass_threshold
            and completeness >= self.pass_threshold
        )

        failure_type: FailureType | None = None
        if not passed:
            if faithfulness < self.hallucination_threshold:
                failure_type = FailureType.HALLUCINATION
            elif relevance < self.relevance_threshold:
                failure_type = FailureType.IRRELEVANT
            elif completeness < self.completeness_threshold:
                failure_type = FailureType.INCOMPLETE
            else:
                failure_type = FailureType.OFF_TOPIC

        chunks = retrieved_contexts if retrieved_contexts is not None else qa_pair.retrieved_contexts
        ctx_recall: float | None = None
        ctx_precision: float | None = None
        if chunks:
            ctx_recall = self.evaluate_context_recall(chunks, qa_pair.expected_answer)
            ctx_precision = self.evaluate_context_precision(chunks, qa_pair.expected_answer)

        return EvalResult(
            qa_pair=qa_pair,
            actual_answer=actual_answer,
            faithfulness=faithfulness,
            relevance=relevance,
            completeness=completeness,
            passed=passed,
            failure_type=failure_type,
            context_precision=ctx_precision,
            context_recall=ctx_recall,
            latency_seconds=latency_seconds,
        )


def rerank_contexts_by_query_overlap(contexts: Sequence[str], query: str) -> list[str]:
    """Lexical reranking baseline: sort context chunks descending by token overlap with query."""
    q_tokens = tokenize_text(query)
    return sorted(contexts, key=lambda c: len(tokenize_text(c) & q_tokens), reverse=True)
