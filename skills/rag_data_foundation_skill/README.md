# RAG Data Foundation & Vector Knowledge Pipeline Skill

Enterprise-grade, domain-agnostic skill package for building, testing, and scaling **Retrieval-Augmented Generation (RAG)** systems, **Vector Stores**, and **Agentic Knowledge Retrieval** workflows.

---

## 📂 Package Architecture

```text
skills/rag_data_foundation_skill/
├── SKILL.md              # Core Agent Skill Specification & Execution Runbook
├── README.md             # Developer integration guide & quickstart
└── templates/            # Production-grade generic implementation modules
    ├── __init__.py       # Package exports & public API
    ├── config.py         # Type-safe configuration schemas (Chunker, Embedder, Store, Pipeline)
    ├── models.py         # Standard entity dataclasses (Document, Chunk, QueryResult, BenchmarkQuery)
    ├── chunking.py       # Segmentation algorithms (FixedSize, Sentence, RecursiveHierarchical, Comparator)
    ├── embeddings.py     # Pluggable vectorizers (Mock, Local SentenceTransformers, OpenAI, Gemini) & Cosine math
    ├── store.py          # Vector store engines (InMemoryVectorStore, ChromaVectorStore) with metadata filtering & CRUD
    ├── agent.py          # KnowledgeBaseAgent & RAGPromptBuilder with citation tracking
    ├── pipeline.py       # Unified RAGPipeline orchestrator
    └── evaluation.py     # Quantitative retrieval benchmarking (Hit Rate@K, MRR@K, Latency)
```

---

## 🚀 Quickstart: 5-Minute Setup

### 1. Ingestion, Chunking & Semantic Search

```python
from skills.rag_data_foundation_skill.templates import (
    Document,
    RAGPipeline,
    PipelineConfig,
    ChunkerConfig,
    EmbedderConfig,
    StoreConfig,
)

# 1. Initialize Pipeline with desired configuration
config = PipelineConfig(
    chunker=ChunkerConfig(strategy="recursive", chunk_size=300, chunk_overlap=30),
    embedder=EmbedderConfig(provider="mock"),  # Switch to "openai", "gemini", or "local"
    store=StoreConfig(backend="memory", collection_name="knowledge_base"),
)
pipeline = RAGPipeline(config=config)

# 2. Ingest raw documents with rich metadata
docs = [
    Document(
        id="doc_py_01",
        content="Python is a high-level programming language emphasizing code readability and simplicity.",
        metadata={"category": "programming", "lang": "en"},
    ),
    Document(
        id="doc_ml_01",
        content="Machine learning enables systems to learn from data patterns and make predictions.",
        metadata={"category": "ai", "lang": "en"},
    ),
]
num_chunks = pipeline.ingest_documents(docs)
print(f"Ingested {len(docs)} documents -> {num_chunks} vector chunks.")

# 3. Perform semantic search with structured metadata filtering
results = pipeline.query(
    question="What language focuses on readability?",
    top_k=2,
    metadata_filter={"category": "programming"},
)
for r in results:
    print(f"[Score: {r.score:.3f}] {r.content} (Source: {r.metadata.get('doc_id')})")

# 4. Generate grounded answer via Agent
response = pipeline.answer(
    question="What is Python known for?",
    top_k=2,
    return_context=True,
)
print("\nAgent Answer:", response["answer"])
```

---

## 📊 Benchmark & Evaluate Retrieval Quality

Evaluate whether your chunking and embedding configuration retrieves ground-truth documents accurately:

```python
from skills.rag_data_foundation_skill.templates import (
    BenchmarkQuery,
    RetrievalEvaluator,
)

evaluator = RetrievalEvaluator(store=pipeline.store)

benchmarks = [
    BenchmarkQuery(
        query_id="q1",
        query_text="programming readability language",
        expected_doc_ids=["doc_py_01"],
    ),
    BenchmarkQuery(
        query_id="q2",
        query_text="learning from data and predictions",
        expected_doc_ids=["doc_ml_01"],
    ),
]

metrics = evaluator.run_benchmark(benchmarks, top_k=3, strategy_name="Recursive_Chunking_Mock")
print(f"Hit Rate@3: {metrics.hit_rate_at_k * 100:.1f}%")
print(f"MRR@3:      {metrics.mrr_at_k:.3f}")
print(f"Avg Latency: {metrics.avg_latency_ms:.2f} ms")
```

---

## ⚙️ Environment Variables Reference

When integrating real cloud or local models, set the following environment variables:

```bash
# Embedder Provider Selection: "mock" | "local" | "openai" | "gemini"
EMBEDDING_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Google Gemini Configuration
GEMINI_API_KEY=AIzaSy...
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

# Local SentenceTransformers Configuration
LOCAL_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

---

## 🧩 Extending the Templates

### Adding a Custom Chunker
Inherit from `BaseChunker` and implement the `chunk` method:

```python
from skills.rag_data_foundation_skill.templates import BaseChunker

class MarkdownHeaderChunker(BaseChunker):
    def chunk(self, text: str) -> list[str]:
        # Custom logic splitting by markdown headers '#', '##', etc.
        import re
        sections = re.split(r'\n(?=#{1,3}\s)', text)
        return [s.strip() for s in sections if s.strip()]
```

### Adding a Custom Vector Store Adapter
Inherit from `BaseVectorStore` and implement the abstract methods (`add_documents`, `search`, `search_with_filter`, `delete_document`, `get_collection_size`).

---

## 🧪 Testing

Run automated tests against the templates:

```bash
python -m unittest discover -s skills/rag_data_foundation_skill/templates
```
