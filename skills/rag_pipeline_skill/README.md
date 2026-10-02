# Enterprise RAG Pipeline Skill — Integration Guide

A generalized, modular, and production-ready Agent Skill for building, optimizing, and evaluating enterprise-grade **Retrieval-Augmented Generation (RAG)** systems across any document domain.

---

## 🚀 Key Architectural Capabilities

- **Universal Document Parsing:** Automatically ingest and normalize PDF, DOCX, HTML, Markdown, and JSON into clean markdown with persistent metadata.
- **Configurable Chunking with Provenance:** Preserve parent-child hierarchy, deterministic chunk IDs (`{parent_id}::chunk-{idx}`), and full provenance tracking.
- **Multi-Provider Embeddings:** Seamlessly switch between local models (`SentenceTransformers`/`BGE-M3`) and cloud APIs (`OpenAI`, `Google Gemini`, `Ollama`).
- **Hybrid Retrieval & Reciprocal Rank Fusion (RRF):** Combine Dense Semantic Vectors with Sparse Lexical BM25, fused via single-pass RRF ($k=60$).
- **Adaptive Fallback & OOD Detection:** Calibrate dense cosine similarity thresholds to detect Out-of-Distribution queries and trigger structural fallback mechanisms without crashing.
- **Lost-in-the-Middle Mitigation:** Context reordering algorithm $[c_0, c_2, \dots, c_3, c_1]$ maximizing LLM context retention.
- **Citation-Grounded Generation:** Enforce strict evidence attribution with verifiable citations and safe refusal mechanisms.
- **RAG Triad & Quantitative Evaluation:** Multi-metric evaluation (Faithfulness, Answer Relevance, Context Recall, Context Precision) and automated A/B testing benchmark.

---

## 📁 Skill Package Layout

```text
skills/rag_pipeline_skill/
├── SKILL.md              # Complete Agent Execution Blueprint, Invariants & Checklist
├── README.md             # Developer Quickstart & Integration Documentation
└── templates/            # Generic, reusable Python modules
    ├── __init__.py       # Package exports
    ├── config.py         # Configuration dataclasses (Environment/YAML-driven)
    ├── contracts.py      # Typed schemas & runtime invariant validators
    ├── ingestion.py      # Multi-format parser & markdown converter
    ├── chunking.py       # Hierarchical chunker with lineage tracking
    ├── embedding.py      # Unified embedding interface with batching
    ├── vector_store.py   # ChromaDB / Vector Store adapter
    ├── retrieval.py      # Hybrid Retrieval, RRF fusion & adaptive fallback
    ├── generation.py     # Grounded prompt builder & multi-LLM dispatcher
    └── evaluation.py     # RAG Triad metrics & A/B benchmark suite
```

---

## 🛠️ Quickstart Integration

### 1. Import and Configure

```python
from skills.rag_pipeline_skill.templates import (
    PipelineConfig,
    load_and_standardize_directory,
    DocumentChunker,
    UniversalEmbeddingEngine,
    ChromaVectorStore,
    BM25LexicalIndex,
    HybridRetrievalPipeline,
    GroundedGenerator,
)
from pathlib import Path

# Load settings from environment or defaults
config = PipelineConfig.from_env()

# 1. Ingestion & Preprocessing
raw_docs_dir = Path("data/raw")
standardized_docs = load_and_standardize_directory(raw_docs_dir)

# 2. Chunking
chunker = DocumentChunker(chunk_size=config.chunking.chunk_size, chunk_overlap=config.chunking.chunk_overlap)
chunks = chunker.chunk_documents(standardized_docs)

# 3. Embedding & Vector Indexing
embed_engine = UniversalEmbeddingEngine(provider=config.embedding.provider, model_name=config.embedding.model_name)
vectors = embed_engine.embed_texts([c["content"] for c in chunks])

vector_store = ChromaVectorStore(persist_dir=config.vector_store.persist_directory)
vector_store.upsert_chunks(chunks, vectors)

# 4. Sparse Indexing & Hybrid Retrieval Setup
bm25_index = BM25LexicalIndex(chunks)

pipeline = HybridRetrievalPipeline(
    dense_search_fn=lambda q, k: vector_store.search(embed_engine.embed_query(q), top_k=k),
    lexical_search_fn=lambda q, k: bm25_index.search(q, top_k=k),
    dense_score_threshold=config.retrieval.dense_score_threshold,
)

# 5. Grounded Generation
generator = GroundedGenerator(provider=config.generation.provider)
result = generator.generate("Chính sách hoàn tiền như thế nào?", retriever_fn=pipeline.retrieve)

print("Answer:", result["answer"])
print("Sources Used:", [s["id"] for s in result["sources"]])
```

---

## 🧪 Testing & Verification

Run contract validation tests to verify that your data pipelines strictly satisfy schema requirements:

```bash
pytest tests/ -q
```
