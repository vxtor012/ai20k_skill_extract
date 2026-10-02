import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class IngestionConfig:
    raw_dir: str = "data/raw"
    standardized_dir: str = "data/standardized"
    supported_extensions: list[str] = field(
        default_factory=lambda: [".pdf", ".docx", ".doc", ".html", ".txt", ".json", ".md"]
    )


@dataclass
class ChunkingConfig:
    chunk_size: int = 500
    chunk_overlap: int = 50
    strategy: Literal["recursive", "character", "token", "semantic"] = "recursive"
    separators: list[str] = field(
        default_factory=lambda: ["\n\n", "\n", ". ", "; ", " ", ""]
    )


@dataclass
class EmbeddingConfig:
    provider: Literal["sentence_transformers", "openai", "gemini", "ollama", "jina"] = "sentence_transformers"
    model_name: str = "BAAI/bge-m3"
    dimension: int = 1024
    batch_size: int = 32
    normalize_embeddings: bool = True


@dataclass
class VectorStoreConfig:
    engine: Literal["chroma", "qdrant", "faiss"] = "chroma"
    persist_directory: str = "vector_db"
    collection_name: str = "enterprise_knowledge_base"
    distance_metric: Literal["cosine", "l2", "ip"] = "cosine"


@dataclass
class RetrievalConfig:
    dense_top_k: int = 10
    lexical_top_k: int = 10
    final_top_k: int = 5
    rrf_k: int = 60
    dense_score_threshold: float = 0.35  # Cosine similarity threshold for OOD fallback trigger
    enable_reranking: bool = True
    enable_fallback: bool = True


@dataclass
class GenerationConfig:
    provider: Literal["openai", "gemini", "anthropic", "ollama"] = "openai"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 2048
    safe_refusal_message: str = "Tôi không thể xác minh thông tin này từ các nguồn tài liệu được cung cấp."


@dataclass
class PipelineConfig:
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        config = cls()
        config.embedding.provider = os.getenv("EMBEDDING_PROVIDER", config.embedding.provider)  # type: ignore
        config.embedding.model_name = os.getenv("EMBEDDING_MODEL", config.embedding.model_name)
        config.generation.provider = os.getenv("LLM_PROVIDER", config.generation.provider)  # type: ignore
        config.generation.model_name = os.getenv("LLM_MODEL", config.generation.model_name)
        return config
