# Data Pipeline & Observability Agentic Skill

An enterprise-ready, generalized skill and code framework for designing, implementing, observing, and self-healing data ingestion & vector retrieval pipelines for AI/RAG systems.

---

## 📦 Package Structure

```text
skills/data_pipeline_observability/
├── SKILL.md              # Master Agent Runbook, Architecture Blueprint & Acceptance Checklist
├── README.md             # Developer Quickstart & Integration Guide
└── templates/            # Modular Generic Python Templates
    ├── __init__.py
    ├── base_pipeline.py      # Abstract Base Classes (Ingestion, Transform, Index, Orchestrate)
    ├── quality_gate.py       # Ephemeral Great Expectations 1.x & Declarative Quality Rules
    ├── freshness_monitor.py  # Temporal SLA & Staleness Drift Monitoring
    ├── chaos_injector.py     # 6-Scenario Controlled Data Corruption Suite
    ├── evaluator.py          # Hit Rate @ K, Lexical Token F1, LLM-as-a-Judge Scorer
    └── idempotent_repair.py  # Lineage Replay Engine & 3-State Comparative Audit
```

---

## 🚀 Quickstart Example

Here is how you can compose a resilient, observable pipeline in under 20 lines of code:

```python
import pandas as pd
from skills.data_pipeline_observability.templates import (
    DataQualityGate,
    QualityGateConfig,
    FreshnessMonitor,
    FreshnessConfig,
    ChaosDataInjector,
    CorruptionPlan,
)

# 1. Configure Quality Gate (GX 1.x)
quality_gate = DataQualityGate(
    QualityGateConfig(
        min_rows=5,
        max_rows=10_000,
        required_columns=["id", "title", "content"],
        unique_columns=["id"],
        min_length_rules={"content": 30},
        use_gx_engine=True,
    )
)

# 2. Configure Freshness SLA
freshness_monitor = FreshnessMonitor(
    FreshnessConfig(
        timestamp_column="published",
        max_staleness_days=180,
        max_stale_percentage_threshold=0.25,
    )
)

# 3. Validate clean dataset
df = pd.DataFrame([
    {"id": "doc_001", "title": "Paper Title", "content": "Comprehensive paper body with deep insights...", "published": "2024-01-01"},
    {"id": "doc_002", "title": "Second Study", "content": "Another complete study with experimental data...", "published": "2024-02-15"}
])

q_result = quality_gate.evaluate_dataframe(df, dataset_name="sample_docs")
f_result = freshness_monitor.evaluate(df)

print(f"Quality Gate Passed: {q_result.passed}")
print(f"Freshness SLA Passed: {f_result.is_fresh}")

# 4. Chaos Fault Injection & Resilience Testing
injector = ChaosDataInjector(CorruptionPlan(drop_ratio=0.5, blank_ratio=0.5))
corrupted_df, report = injector.corrupt(df, id_column="id", text_column="content")
corrupted_q_result = quality_gate.evaluate_dataframe(corrupted_df, dataset_name="corrupted_docs")

print(f"Corrupted Quality Gate Detected Failure: {not corrupted_q_result.passed}")
```

---

## 🛠️ Integration Patterns

### 1. Vector Store Ingestion (Chroma / Qdrant / Pinecone / pgvector)
Wrap your vector store indexing inside `BaseVectorIndexer` to ensure that failed batches from `DataQualityGate` are quarantined before polluting vector indexes.

### 2. CI/CD Pipeline Automation (GitHub Actions / GitLab CI)
Run `PipelineEvaluator` on test sets on every Pull Request to catch retrieval regressions before production release.

### 3. Automated Self-Healing (Idempotent Recovery)
Use `IdempotentRepairEngine` with immutable storage snapshots to auto-heal tainted indexes whenever silent data corruption is detected.

---

## 📋 License & Compatibility
- **Python Compatibility:** Python 3.11+
- **Key Dependencies:** `pandas`, `great-expectations >= 1.0.0`, `pydantic >= 2.0`, `sentence-transformers`
