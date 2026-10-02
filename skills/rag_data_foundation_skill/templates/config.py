"""
Configuration Schemas for Generalized RAG & Vector Data Foundations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class ChunkerConfig:
    """Chunking strategy parameters."""
    strategy: Literal["fixed", "sentence", "recursive", "custom"] = "recursive"
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_sentences_per_chunk: int = 3
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


@dataclass
class EmbedderConfig:
    """Embedding backend configuration."""
    provider: Literal["mock", "local", "openai", "gemini", "custom"] = "mock"
    model_name: Optional[str] = None
    dimension: int = 64
    batch_size: int = 32
    normalize: bool = True

    @classmethod
    def from_env(cls) -> EmbedderConfig:
        provider = os.getenv("EMBEDDING_PROVIDER", "mock").lower()
        model_name = os.getenv("EMBEDDING_MODEL")
        if not model_name:
            if provider == "openai":
                model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            elif provider == "gemini":
                model_name = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
            elif provider == "local":
                model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        return cls(
            provider=provider,  # type: ignore
            model_name=model_name,
        )


@dataclass
class StoreConfig:
    """Vector storage configuration."""
    backend: Literal["memory", "chroma", "faiss", "custom"] = "memory"
    collection_name: str = "rag_knowledge_base"
    persist_directory: Optional[str] = None
    similarity_metric: Literal["cosine", "dot", "euclidean"] = "cosine"


@dataclass
class PipelineConfig:
    """End-to-end RAG orchestrator configuration."""
    chunker: ChunkerConfig = field(default_factory=ChunkerConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    default_top_k: int = 3
    min_similarity_threshold: float = 0.0
    system_prompt_template: str = (
        "You are an expert AI assistant. Answer the user's question accurately using ONLY "
        "the provided Context chunks. If the answer cannot be determined from the Context, "
        "clearly state that the information is not available.\n\n"
        "--- CONTEXT ---\n{context}\n\n"
        "--- QUESTION ---\n{question}\n\n"
        "--- ANSWER ---"
    )
