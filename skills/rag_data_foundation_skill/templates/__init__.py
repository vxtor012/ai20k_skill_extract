"""
Generic RAG & Vector Data Foundation Templates Package.
Provides production-ready, domain-agnostic abstractions for building RAG pipelines.
"""

from .config import ChunkerConfig, EmbedderConfig, PipelineConfig, StoreConfig
from .models import BenchmarkQuery, Chunk, Document, EvaluationResult, QueryResult
from .chunking import (
    BaseChunker,
    ChunkingStrategyComparator,
    FixedSizeChunker,
    RecursiveHierarchicalChunker,
    SentenceChunker,
)
from .embeddings import (
    BaseEmbedder,
    GeminiEmbedder,
    LocalSentenceTransformersEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
    cosine_similarity,
    l2_normalize,
)
from .store import BaseVectorStore, ChromaVectorStore, InMemoryVectorStore
from .agent import KnowledgeBaseAgent, RAGPromptBuilder
from .pipeline import RAGPipeline
from .evaluation import RetrievalEvaluator

__all__ = [
    "ChunkerConfig",
    "EmbedderConfig",
    "StoreConfig",
    "PipelineConfig",
    "Document",
    "Chunk",
    "QueryResult",
    "BenchmarkQuery",
    "EvaluationResult",
    "BaseChunker",
    "FixedSizeChunker",
    "SentenceChunker",
    "RecursiveHierarchicalChunker",
    "ChunkingStrategyComparator",
    "BaseEmbedder",
    "MockEmbedder",
    "LocalSentenceTransformersEmbedder",
    "OpenAIEmbedder",
    "GeminiEmbedder",
    "cosine_similarity",
    "l2_normalize",
    "BaseVectorStore",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "KnowledgeBaseAgent",
    "RAGPromptBuilder",
    "RAGPipeline",
    "RetrievalEvaluator",
]
