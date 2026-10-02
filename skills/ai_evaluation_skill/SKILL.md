---
name: ai-eval-benchmarking
description: Autonomous framework and execution blueprint for evaluating, benchmarking, and gating AI/LLM/RAG systems using stratified golden datasets, lexical/semantic heuristics, LLM-as-a-Judge with bias detection, automated failure triage, and CI/CD quality gates.
triggers:
  - "evaluate llm"
  - "rag evaluation"
  - "ai evaluation"
  - "benchmark agent"
  - "golden dataset validation"
  - "llm as judge"
  - "faithfulness relevance completeness"
  - "regression test ai"
  - "context precision context recall"
  - "hallucination detection"
---

# AI & RAG Evaluation & Benchmarking System Blueprint

## 1. Core Philosophy & Architectural Blueprint

Evaluating generative AI and RAG pipelines requires treating evaluation as an empirical, reproducible science:
$$\text{Hypothesis} \longrightarrow \text{Experiment (Blind Inference)} \longrightarrow \text{Measure (Multi-Tier Metrics)} \longrightarrow \text{Diagnose (5-Whys)} \longrightarrow \text{Gate / Iterate}$$

### The Three Core Tenets:
1. **Strict Separation of Evaluation from Generation (Blind Inference):** Inference targets MUST NOT receive ground truth expected answers or pre-filtered gold contexts at inference time.
2. **Evidence Provenance & Stratification:** Evaluation sets must have verifiable provenance (verbatim citations from raw source corpus) and stratified coverage across difficulty levels (Easy, Medium, Hard, Adversarial/Edge cases).
3. **Multi-Tier Triangulation:** Combine deterministic token/lexical heuristics (fast, cheap, reproducible), rank-aware retrieval metrics (AP@K, Context Recall), LLM-as-a-Judge scoring with rubric alignment and bias detection, and automated root cause triage.

```mermaid
flowchart TD
    subgraph Data Layer
        Corpus[Source Corpus / Manifest] --> ProvenanceCheck[Provenance & Contract Validator]
        GoldenDS[Stratified Golden Dataset JSON] --> ProvenanceCheck
    end

    subgraph Inference Isolation
        ProvenanceCheck --> BlindInference[Blind Inference Runner\n(Agent/LLM receives Question ONLY)]
        BlindInference --> RawOutput[(Actual Answers + Retrieved Chunks)]
    end

    subgraph Evaluation Core
        RawOutput --> LexicalEval[Deterministic Metrics Engine\n- Faithfulness\n- Answer Relevance\n- Completeness]
        RawOutput --> RetrievalEval[Retrieval Diagnostics\n- Context Recall\n- Context Precision AP@K]
        RawOutput --> LLMJudge[LLM-as-a-Judge\n- Rubric-based Scoring\n- Bias Detection Engine]
    end

    subgraph Triage & CI/CD
        LexicalEval & RetrievalEval & LLMJudge --> Aggregator[Benchmark Aggregator]
        Aggregator --> Failures{Pass Rate & Thresholds}
        Failures -->|Failures Identified| Triage[Failure Analyzer & 5-Whys Triage]
        Triage --> RemPlan[Improvement Log & Action Plan]
        Aggregator --> RegressCheck[Regression Tester vs Baseline]
        RegressCheck --> QualityGate{CI/CD Quality Gate\n(Delta < 0.05)}
        QualityGate -->|Pass| Deploy[Release Approved]
        QualityGate -->|Fail| Block[Block Deployment]
    end
```

---

## 2. Standardized Metrics Taxonomy

| Dimension | Metric Name | Definition & Formula | Target / Good Range |
| :--- | :--- | :--- | :--- |
| **Retrieval** | `Context Recall` | $\frac{\|\text{Expected Tokens} \cap \bigcup \text{Retrieved Chunks}\|}{\|\text{Expected Tokens}\|}$ | $\ge 0.80$ |
| **Retrieval** | `Context Precision (AP@K)` | $\frac{1}{\text{Rel}} \sum_{k=1}^K \text{Precision@k} \times \text{rel}_k$ (Rank-aware) | $\ge 0.70$ |
| **Generation**| `Faithfulness` | $\frac{\|\text{Answer Tokens} \cap \text{Context Tokens}\|}{\|\text{Answer Tokens}\|}$ (Hallucination check) | $\ge 0.85$ (Min: 0.70) |
| **Generation**| `Answer Relevance` | $\frac{\|\text{Answer Tokens} \cap \text{Question Tokens}\|}{\|\text{Question Tokens}\|}$ (Query alignment) | $\ge 0.80$ |
| **Generation**| `Completeness` | $\frac{\|\text{Answer Tokens} \cap \text{Expected Tokens}\|}{\|\text{Expected Tokens}\|}$ (Coverage) | $\ge 0.75$ |
| **Judge** | `Rubric Alignment` | Multi-criteria score (1.0–5.0) normalized with reasoning | $\ge 4.0 / 5.0$ |

---

## 3. Step-by-Step Execution Guide for Autonomous Agents

When triggered on any target repository containing an AI/LLM/RAG system, execute this deterministic workflow:

### Step 1: Environment & Dependency Audit
1. Inspect runtime environment (`python --version`, check virtualenv).
2. Verify core dependencies (`pytest`, `openai` or local model runner, `pydantic` or `dataclasses`).
3. Ensure API credentials or mock providers are configured in `.env`.

### Step 2: Golden Dataset & Corpus Provenance Verification
1. Locate corpus directory and dataset files (e.g., `golden_dataset.json`, `data/`, `docs/`).
2. Run `GoldenDatasetValidator` to enforce:
   - Schema versioning and non-empty mandatory fields.
   - Stratification quota: Easy ($\ge 25\%$), Medium ($\ge 35\%$), Hard ($\ge 25\%$), Adversarial ($\ge 15\%$).
   - Exact substring provenance matching against raw corpus files.

### Step 3: Blind Inference Execution
1. Wrap target system's entry point into an isolated callable: `inference_fn(question: str) -> (answer: str, retrieved_contexts: list[str])`.
2. Prohibit data leakage: NEVER pass `expected_answer` or `gold_context` to `inference_fn`.
3. Track per-sample latency and catch inference exceptions gracefully.

### Step 4: Metric Calculation & Judge Scoring
1. Compute deterministic generation metrics (`Faithfulness`, `Relevance`, `Completeness`).
2. Compute retrieval diagnostics if chunk history is provided (`Context Recall`, `Context Precision`).
3. If LLM judge is enabled, dispatch batched prompts with standard rubrics and run bias analysis (`detect_batch_biases`).

### Step 5: Failure Triage & Root Cause Analysis
1. Filter results failing threshold ($\text{score} < 0.50$ or $\text{faithfulness} < 0.70$).
2. Apply Failure Taxonomy:
   - $\text{Faithfulness} < 0.30 \implies \text{Hallucination}$
   - $\text{Relevance} < 0.30 \implies \text{Irrelevant / Misaligned}$
   - $\text{Completeness} < 0.30 \implies \text{Incomplete / Missing Context}$
   - $\text{All} < 0.50 \text{ with similar drop} \implies \text{Off-Topic / Intent Breakdown}$
3. Generate prioritized engineering remediation plan and Markdown Audit Table.

### Step 6: Regression Comparison & Quality Gate Check
1. Compare current summary against `baseline_results.json` (if available).
2. Enforce quality gate rules:
   - Hard block if `avg_faithfulness < 0.70` or `pass_rate < 0.80`.
   - Hard block if any key metric regresses by $> 0.05$ vs baseline.
3. Emit structured report JSON and Markdown summary.

---

## 4. Input & Output Contract

### Required Inputs:
- **`dataset_path`**: Path to JSON golden dataset.
- **`corpus_dir`**: Path to corpus containing reference Markdown/text files.
- **`target_callable`**: Python function or CLI endpoint to query the AI system.
- **`baseline_path`** *(Optional)*: Path to baseline evaluation run JSON.

### Standard Output Artifacts:
- **`evaluation_results.json`**: Granular record of every test case, scores, retrieved contexts, failure flags.
- **`benchmark_summary.json`**: Aggregate statistics, pass rate, difficulty breakdown.
- **`improvement_log.md`**: Triage table listing failed IDs, diagnosed root causes, and recommended fixes.

---

## 5. Edge Cases, Anti-Patterns & Best Practices

| Category | Anti-Pattern | Best Practice / Remedy |
| :--- | :--- | :--- |
| **Data Leakage** | Passing gold context into candidate agent during inference. | Enforce blind inference harness: agent receives query only. |
| **Biased Dataset** | 100% simple factual queries from a single document. | Enforce stratified distribution with multi-hop (Hard) & Adversarial traps. |
| **Ungrounded Metrics** | Relying solely on LLM-as-a-Judge without token/provenance cross-checks. | Triangulate: deterministic token overlap + rank-aware AP@K + LLM Judge. |
| **Judge Bias** | Judge favoring long answers or first candidate in comparison. | Run automated bias checks (leniency, severity, verbosity, positional). |
| **Unchecked Regressions**| Deploying prompt changes without running full benchmark suite. | Embed evaluation into CI/CD as an automated blocking quality gate. |

---

## 6. Acceptance & Quality Checklist for Agents

- [ ] All golden dataset samples verified for verbatim provenance against source corpus.
- [ ] Blind inference executed without ground truth leakage.
- [ ] All 4 core metric groups computed (Answer Quality, Retrieval Quality, Task Completion, System Latency).
- [ ] Every failed sample assigned an unambiguous Failure Taxonomy category and 5-Whys root cause.
- [ ] Prioritized remediation actions generated with clear engineering ownership.
- [ ] Regression delta calculated against baseline; quality gate pass/fail explicitly decided.
- [ ] Evaluation artifacts saved in standard machine-readable JSON and human-readable Markdown.
