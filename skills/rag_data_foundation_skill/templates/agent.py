"""
Agentic Retrieval-Augmented Generation (RAG) Orchestrator.

Integrates Vector Store retrieval, context formatting, citation tagging,
and LLM synthesis with configurable prompt templates and guardrails.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from .models import QueryResult
from .store import BaseVectorStore


class RAGPromptBuilder:
    """Constructs prompt payloads with strict context isolation and source attribution."""

    DEFAULT_SYSTEM_TEMPLATE = (
        "You are an expert AI assistant answering questions based strictly on provided knowledge chunks.\n"
        "Guidelines:\n"
        "1. Only use facts contained within the [CONTEXT] blocks below.\n"
        "2. If the context does not contain enough information to answer truthfully, state: "
        "'I do not have enough information in the provided context to answer this question.'\n"
        "3. Cite source references whenever referencing facts (e.g. [Source: doc_id]).\n\n"
        "[CONTEXT]\n{context}\n\n"
        "[QUESTION]\n{question}\n\n"
        "[ANSWER]"
    )

    def __init__(self, template: Optional[str] = None) -> None:
        self.template = template or self.DEFAULT_SYSTEM_TEMPLATE

    def format_context_block(self, results: List[QueryResult]) -> str:
        if not results:
            return "No relevant context found."

        blocks = []
        for idx, item in enumerate(results, start=1):
            source = item.metadata.get("source") or item.parent_doc_id or item.id
            score = f" (relevance: {item.score:.3f})" if item.score is not None else ""
            block = f"--- Document Chunk {idx} [Source: {source}]{score} ---\n{item.content.strip()}"
            blocks.append(block)
        return "\n\n".join(blocks)

    def build(self, question: str, results: List[QueryResult]) -> str:
        context_str = self.format_context_block(results)
        return self.template.format(context=context_str, question=question.strip())


class KnowledgeBaseAgent:
    """
    RAG Agent coordinating query retrieval, context assembly, and LLM answer generation.
    """

    def __init__(
        self,
        store: BaseVectorStore,
        llm_fn: Callable[[str], str],
        prompt_builder: Optional[RAGPromptBuilder] = None,
        min_relevance_score: float = 0.0,
    ) -> None:
        self.store = store
        self.llm_fn = llm_fn
        self.prompt_builder = prompt_builder or RAGPromptBuilder()
        self.min_relevance_score = min_relevance_score

    def retrieve(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        """Fetch candidate chunks from vector store."""
        results = self.store.search_with_filter(
            query=question,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
        # Filter by minimum relevance threshold
        return [r for r in results if r.score >= self.min_relevance_score]

    def answer(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None,
        return_context: bool = False,
    ) -> Union[str, Dict[str, Any]]:
        """
        Execute full RAG pipeline:
        1. Retrieve top-k relevant chunks
        2. Format prompt context
        3. Invoke LLM synthesizer
        4. Return response (and optionally retrieved context)
        """
        retrieved_chunks = self.retrieve(question, top_k=top_k, metadata_filter=metadata_filter)
        prompt = self.prompt_builder.build(question, retrieved_chunks)
        llm_response = self.llm_fn(prompt)

        if return_context:
            return {
                "question": question,
                "answer": llm_response,
                "retrieved_chunks": [c.to_dict() for c in retrieved_chunks],
                "prompt_preview": prompt[:300] + "...",
            }
        return llm_response
