"""
Unified End-to-End RAG Pipeline Orchestrator.

Combines Document Ingestion -> Dynamic Chunking -> Vector Store Ingestion -> Query Execution -> Agent Synthesis.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from .agent import KnowledgeBaseAgent, RAGPromptBuilder
from .chunking import (
    BaseChunker,
    FixedSizeChunker,
    RecursiveHierarchicalChunker,
    SentenceChunker,
)
from .config import PipelineConfig
from .embeddings import (
    BaseEmbedder,
    GeminiEmbedder,
    LocalSentenceTransformersEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
)
from .models import Chunk, Document, QueryResult
from .store import BaseVectorStore, ChromaVectorStore, InMemoryVectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    High-level declarative pipeline coordinating all sub-components of a RAG architecture.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        chunker: Optional[BaseChunker] = None,
        embedder: Optional[BaseEmbedder] = None,
        store: Optional[BaseVectorStore] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.chunker = chunker or self._build_chunker()
        self.embedder = embedder or self._build_embedder()
        self.store = store or self._build_store()
        self.llm_fn = llm_fn or self._default_mock_llm
        self.agent = KnowledgeBaseAgent(
            store=self.store,
            llm_fn=self.llm_fn,
            prompt_builder=RAGPromptBuilder(template=self.config.system_prompt_template),
            min_relevance_score=self.config.min_similarity_threshold,
        )

    def _default_mock_llm(self, prompt: str) -> str:
        preview = prompt[:200].replace("\n", " ")
        return f"[MOCK LLM SYNTHESIS based on context preview: {preview}...]"

    def _build_chunker(self) -> BaseChunker:
        cfg = self.config.chunker
        if cfg.strategy == "fixed":
            return FixedSizeChunker(chunk_size=cfg.chunk_size, overlap=cfg.chunk_overlap)
        elif cfg.strategy == "sentence":
            return SentenceChunker(max_sentences_per_chunk=cfg.max_sentences_per_chunk)
        else:
            return RecursiveHierarchicalChunker(
                separators=cfg.separators,
                chunk_size=cfg.chunk_size,
                chunk_overlap=cfg.chunk_overlap,
            )

    def _build_embedder(self) -> BaseEmbedder:
        cfg = self.config.embedder
        if cfg.provider == "local":
            return LocalSentenceTransformersEmbedder(model_name=cfg.model_name)
        elif cfg.provider == "openai":
            return OpenAIEmbedder(model_name=cfg.model_name)
        elif cfg.provider == "gemini":
            return GeminiEmbedder(model_name=cfg.model_name)
        else:
            return MockEmbedder(dim=cfg.dimension)

    def _build_store(self) -> BaseVectorStore:
        cfg = self.config.store
        if cfg.backend == "chroma":
            return ChromaVectorStore(
                collection_name=cfg.collection_name,
                embedding_fn=self.embedder,
                persist_directory=cfg.persist_directory,
            )
        return InMemoryVectorStore(
            collection_name=cfg.collection_name,
            embedding_fn=self.embedder,
        )

    def ingest_documents(self, documents: List[Document]) -> int:
        """
        Ingest a collection of raw Documents:
        1. Segment documents into Chunks
        2. Index chunks into the Vector Store
        Returns total number of chunks indexed.
        """
        all_chunks: List[Chunk] = []
        for doc in documents:
            chunks = self.chunker.chunk_document(doc)
            all_chunks.extend(chunks)

        self.store.add_documents(all_chunks)
        logger.info("Ingested %d documents into %d vector chunks", len(documents), len(all_chunks))
        return len(all_chunks)

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        """Direct vector retrieval search."""
        k = top_k or self.config.default_top_k
        return self.store.search_with_filter(query=question, top_k=k, metadata_filter=metadata_filter)

    def answer(
        self,
        question: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        return_context: bool = False,
    ) -> Union[str, Dict[str, Any]]:
        """Synthesize answer using KnowledgeBaseAgent."""
        k = top_k or self.config.default_top_k
        return self.agent.answer(
            question=question,
            top_k=k,
            metadata_filter=metadata_filter,
            return_context=return_context,
        )
