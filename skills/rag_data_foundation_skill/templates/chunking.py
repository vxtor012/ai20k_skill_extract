"""
Generalized Text Segmentation (Chunking) Engine.

Provides multiple deterministic chunking strategies (Fixed-Size Sliding Window,
Sentence-Boundary Tokenizer, Recursive Hierarchical Splitter) and quantitative comparators.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import Chunk, Document


class BaseChunker(ABC):
    """Abstract Base Class for text segmenters."""

    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """Split a raw string into segmented text slices."""
        pass

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Convert a Document entity into typed Chunk entities with propagated metadata."""
        text = document.content.strip()
        if not text:
            return []

        raw_chunks = self.chunk(text)
        chunks: List[Chunk] = []

        start_offset = 0
        for idx, text_piece in enumerate(raw_chunks):
            chunk_id = f"{document.id}_chunk_{idx}"
            chunk_metadata = {
                **document.metadata,
                "parent_id": document.id,
                "chunk_index": idx,
                "char_length": len(text_piece),
                "total_chunks_in_doc": len(raw_chunks),
            }

            chunks.append(
                Chunk(
                    id=chunk_id,
                    parent_doc_id=document.id,
                    content=text_piece,
                    chunk_index=idx,
                    metadata=chunk_metadata,
                )
            )
        return chunks


class FixedSizeChunker(BaseChunker):
    """
    Splits text into fixed character or token windows with sliding overlap.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if overlap >= chunk_size:
            raise ValueError(f"overlap ({overlap}) must be strictly less than chunk_size ({chunk_size})")
        self.chunk_size = max(1, chunk_size)
        self.overlap = max(0, overlap)

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: List[str] = []
        for start in range(0, len(text), step):
            piece = text[start : start + self.chunk_size]
            chunks.append(piece)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker(BaseChunker):
    """
    Splits text by sentence boundaries (periods, question marks, exclamation points, newlines)
    and aggregates them up to a specified sentence quota.
    """

    # Matches sentence boundary followed by space or newline, or double newlines
    SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+|\n+')

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []

        # Split into raw sentences and filter out blanks
        raw_sentences = self.SENTENCE_SPLIT_REGEX.split(text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return []

        chunks: List[str] = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            chunk_slice = sentences[i : i + self.max_sentences_per_chunk]
            chunk_text = " ".join(chunk_slice).strip()
            if chunk_text:
                chunks.append(chunk_text)

        return chunks


class RecursiveHierarchicalChunker(BaseChunker):
    """
    Splits text hierarchically using a priority list of separators.
    Preserves structural units (paragraphs -> sentences -> words) before falling back to character cuts.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
        self,
        separators: Optional[List[str]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, chunk_overlap)

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Fallback when no separators left: slice by character window
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        current_sep = separators[0]
        remaining_seps = separators[1:]

        if current_sep == "":
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        if current_sep in text:
            splits = text.split(current_sep)
            good_splits: List[str] = []
            
            accumulated: List[str] = []
            accumulated_len = 0

            for part in splits:
                part_len = len(part) + len(current_sep)
                if accumulated_len + part_len <= self.chunk_size:
                    accumulated.append(part)
                    accumulated_len += part_len
                else:
                    if accumulated:
                        good_splits.append(current_sep.join(accumulated))
                        accumulated = []
                        accumulated_len = 0

                    if len(part) > self.chunk_size:
                        sub_chunks = self._split_recursive(part, remaining_seps)
                        good_splits.extend(sub_chunks)
                    else:
                        accumulated.append(part)
                        accumulated_len = part_len

            if accumulated:
                good_splits.append(current_sep.join(accumulated))

            return [s.strip() for s in good_splits if s.strip()]

        return self._split_recursive(text, remaining_seps)


class ChunkingStrategyComparator:
    """
    Executes multiple chunking strategies on a given text corpus
    and returns comparative analytical metrics.
    """

    def __init__(self) -> None:
        pass

    def compare(self, text: str, chunk_size: int = 500) -> Dict[str, Dict[str, Any]]:
        fixed = FixedSizeChunker(chunk_size=chunk_size, overlap=min(50, chunk_size // 5))
        sentence = SentenceChunker(max_sentences_per_chunk=3)
        recursive = RecursiveHierarchicalChunker(chunk_size=chunk_size)

        strategies = {
            "fixed_size": fixed.chunk(text),
            "by_sentences": sentence.chunk(text),
            "recursive": recursive.chunk(text),
        }

        results: Dict[str, Dict[str, Any]] = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            lengths = [len(c) for c in chunks]
            avg_length = (sum(lengths) / count) if count > 0 else 0.0
            min_length = min(lengths) if lengths else 0
            max_length = max(lengths) if lengths else 0

            results[name] = {
                "count": count,
                "avg_length": round(avg_length, 2),
                "min_length": min_length,
                "max_length": max_length,
                "chunks": chunks,
            }

        return results
