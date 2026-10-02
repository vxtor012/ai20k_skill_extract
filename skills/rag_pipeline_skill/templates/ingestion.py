"""
Universal Document Ingestion & Normalization Module.

Handles automated extraction, conversion from multi-format files (PDF, DOCX, HTML, Markdown, JSON)
into standardized markdown documents with canonical metadata schemas.
"""

import json
from pathlib import Path
from typing import List, Optional
from .contracts import Document, DocumentMetadata


class UniversalDocumentParser:
    """Extracts raw text and converts multiple document formats into normalized Document models."""

    @staticmethod
    def parse_file(file_path: Path) -> Document:
        """Parses an individual file into a standard Document dict."""
        suffix = file_path.suffix.lower()
        content = ""
        doc_type = file_path.parent.name if file_path.parent.name else "general"

        if suffix in [".md", ".txt"]:
            content = file_path.read_text(encoding="utf-8")
        elif suffix == ".json":
            data = json.loads(file_path.read_text(encoding="utf-8"))
            content = data.get("content_markdown") or data.get("content") or json.dumps(data, ensure_ascii=False)
            doc_type = data.get("doc_type", doc_type)
        elif suffix == ".pdf":
            try:
                from markitdown import MarkItDown
                md_converter = MarkItDown()
                result = md_converter.convert(str(file_path))
                content = result.text_content
            except ImportError:
                # Fallback to pypdf / pdfplumber if markitdown is absent
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                content = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in [".docx", ".doc"]:
            try:
                from markitdown import MarkItDown
                md_converter = MarkItDown()
                result = md_converter.convert(str(file_path))
                content = result.text_content
            except ImportError:
                import docx
                doc = docx.Document(str(file_path))
                content = "\n\n".join(p.text for p in doc.paragraphs)
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        cleaned_content = UniversalDocumentParser.clean_markdown(content)
        
        doc_id = file_path.stem
        metadata: DocumentMetadata = {
            "source": file_path.name,
            "title": file_path.stem.replace("_", " ").replace("-", " ").title(),
            "doc_type": doc_type,
            "url": None,
        }

        return {
            "id": doc_id,
            "content": cleaned_content,
            "metadata": metadata,
        }

    @staticmethod
    def clean_markdown(text: str) -> str:
        """Sanitizes text, standardizes newlines and removes excessive whitespace artifacts."""
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned = "\n".join(lines).strip()
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned


def load_and_standardize_directory(
    raw_dir: Path,
    output_standardized_dir: Optional[Path] = None,
    supported_extensions: Optional[List[str]] = None,
) -> List[Document]:
    """Loads all supported documents in raw_dir, normalizes them, and optionally caches them."""
    if supported_extensions is None:
        supported_extensions = [".pdf", ".docx", ".doc", ".html", ".txt", ".json", ".md"]

    documents: List[Document] = []
    for ext in supported_extensions:
        for file_path in raw_dir.rglob(f"*{ext}"):
            if file_path.name.startswith("."):
                continue
            doc = UniversalDocumentParser.parse_file(file_path)
            if doc["content"].strip():
                documents.append(doc)
                if output_standardized_dir:
                    rel_path = file_path.relative_to(raw_dir)
                    out_path = (output_standardized_dir / rel_path).with_suffix(".md")
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(doc["content"], encoding="utf-8")

    return documents
