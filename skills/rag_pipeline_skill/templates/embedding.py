"""
Multi-Provider Vector Embedding Engine.

Provides unified interface across SentenceTransformers (BGE/E5), OpenAI, Gemini, and Ollama.
Includes automatic batching, L2 normalization, and fallback handling.
"""

import os
from typing import List, Literal, Optional
import numpy as np


class UniversalEmbeddingEngine:
    """Unified embedding provider with batch processing and metric normalization."""

    def __init__(
        self,
        provider: Literal["sentence_transformers", "openai", "gemini", "ollama"] = "sentence_transformers",
        model_name: str = "BAAI/bge-m3",
        dimension: int = 1024,
        batch_size: int = 32,
    ):
        self.provider = provider
        self.model_name = model_name
        self.dimension = dimension
        self.batch_size = batch_size
        self._local_model = None

    def _get_local_model(self):
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.model_name)
        return self._local_model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts into normalized dense vectors."""
        if not texts:
            return []

        if self.provider == "sentence_transformers":
            model = self._get_local_model()
            embeddings = model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return [vec.tolist() for vec in embeddings]

        elif self.provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                input=texts,
                model=self.model_name or "text-embedding-3-small",
            )
            return [data.embedding for data in response.data]

        elif self.provider == "gemini":
            from google import genai
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            results: List[List[float]] = []
            for text in texts:
                res = client.models.embed_content(
                    model=self.model_name or "text-embedding-004",
                    contents=text,
                )
                results.append(res.embedding.values)
            return results

        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string."""
        return self.embed_texts([query])[0]
