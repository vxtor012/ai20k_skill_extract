"""
Pluggable Embedding Providers & Vector Math Library.

Supports Mock (deterministic, zero external API dependency for local/CI tests),
Local Hugging Face / SentenceTransformers, OpenAI API, and Google Gemini API.
"""

from __future__ import annotations

import hashlib
import math
import os
from abc import ABC, abstractmethod
from typing import List, Optional


def l2_normalize(vector: List[float]) -> List[float]:
    """Compute L2 unit norm of a vector. Returns 0-vector if norm is 0."""
    squared_sum = sum(x * x for x in vector)
    if squared_sum <= 0.0:
        return [0.0] * len(vector)
    norm = math.sqrt(squared_sum)
    return [x / norm for x in vector]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two float vectors.
    
    Formula: dot(a, b) / (||a|| * ||b||)
    Returns 0.0 if either vector has zero magnitude or if vectors are of unequal lengths.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class BaseEmbedder(ABC):
    """Abstract Base Class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single string into a dense float vector."""
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of strings. Subclasses can override for vector-parallel speedups."""
        return [self.embed_text(t) for t in texts]

    def __call__(self, text: str) -> List[float]:
        """Convenience callable interface."""
        return self.embed_text(text)


class MockEmbedder(BaseEmbedder):
    """
    Deterministic pseudo-random embedding generator based on MD5 hashing.
    Zero external dependencies, ideal for unit testing, CI pipelines, and offline labs.
    """

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = f"MockEmbedder(dim={dim})"

    def embed_text(self, text: str) -> List[float]:
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        seed = int(digest, 16)
        vector: List[float] = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        return l2_normalize(vector)


class LocalSentenceTransformersEmbedder(BaseEmbedder):
    """
    Local embedding backend powered by Hugging Face sentence-transformers.
    Runs locally on CPU or GPU without external API egress.
    """

    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: Optional[str] = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. Install with `pip install sentence-transformers`"
            ) from exc

        self.model_name = model_name or self.DEFAULT_MODEL
        self._backend_name = f"LocalSentenceTransformers({self.model_name})"
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(x) for x in embedding]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [[float(x) for x in vec] for vec in embeddings]


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI Embeddings API client (e.g. text-embedding-3-small, text-embedding-3-large).
    """

    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("openai is not installed. Install with `pip install openai`") from exc

        self.model_name = model_name or os.getenv("OPENAI_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._backend_name = f"OpenAIEmbedder({self.model_name})"
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return [float(x) for x in response.data[0].embedding]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        return [[float(x) for x in item.embedding] for item in response.data]


class GeminiEmbedder(BaseEmbedder):
    """
    Google Gemini Embeddings client using google-genai SDK.
    """

    DEFAULT_MODEL = "gemini-embedding-001"

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("google-genai is not installed. Install with `pip install google-genai`") from exc

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required.")

        self.model_name = model_name or os.getenv("GEMINI_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._backend_name = f"GeminiEmbedder({self.model_name})"
        self.client = genai.Client(api_key=key)

    def embed_text(self, text: str) -> List[float]:
        response = self.client.models.embed_content(model=self.model_name, contents=text)
        return [float(x) for x in response.embeddings[0].values]


_mock_embed = MockEmbedder()
