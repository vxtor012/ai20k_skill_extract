"""
Configurable Chunking & Provenance Tracking Module.

Splits normalized documents into chunks using configurable strategies while preserving
parent-child lineage, chunk indices, and metadata integrity.
"""

from typing import List, Literal, Optional
from .contracts import Chunk, Document


class DocumentChunker:
    """Configurable text splitter with deterministic chunk numbering and metadata propagation."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: Literal["recursive", "character", "token"] = "recursive",
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        self.separators = separators or ["\n\n", "\n", ". ", "; ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Splits raw text string into chunks."""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )
            return splitter.split_text(text)
        except ImportError:
            # Standalone fallback implementation
            chunks = []
            start = 0
            text_len = len(text)
            step = self.chunk_size - self.chunk_overlap
            while start < text_len:
                end = min(start + self.chunk_size, text_len)
                chunks.append(text[start:end].strip())
                if end == text_len:
                    break
                start += max(1, step)
            return [c for c in chunks if c]

    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """Splits a batch of Document objects into indexed Chunks with preserved provenance."""
        all_chunks: List[Chunk] = []

        for document in documents:
            doc_id = document["id"]
            doc_metadata = document.get("metadata", {})
            raw_text = document["content"]

            text_splits = self.split_text(raw_text)
            for idx, text in enumerate(text_splits):
                if not text.strip():
                    continue
                
                chunk_id = f"{doc_id}::chunk-{idx}"
                chunk_metadata = {
                    **doc_metadata,
                    "chunk_index": idx,
                    "parent_id": doc_id,
                    "char_count": len(text),
                }

                all_chunks.append({
                    "id": chunk_id,
                    "content": text,
                    "metadata": chunk_metadata,
                })

        return all_chunks
