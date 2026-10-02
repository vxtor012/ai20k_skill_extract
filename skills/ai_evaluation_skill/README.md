# AI & RAG Evaluation Skill

A generalized, production-ready framework for evaluating, benchmarking, and gating AI/LLM/RAG systems.

---

## 🌟 Capabilities

- **Stratified Dataset & Provenance Validation:** Enforces schema contracts, difficulty distributions (Easy, Medium, Hard, Adversarial), and exact source corpus provenance.
- **Blind Inference Harness:** Evaluates agents cleanly without data leakage.
- **Multi-Tier Metrics Engine:**
  - *Generation:* Faithfulness, Answer Relevance, Answer Completeness.
  - *Retrieval:* Context Recall, Rank-Aware Context Precision (AP@K), Lexical Reranker baseline.
- **LLM-as-a-Judge with Bias Detection:** Structured rubrics, JSON enforcement, and automatic detection of leniency, severity, positional, and verbosity biases.
- **Automated Failure Analysis:** Taxonomy categorization, 5-Whys root cause diagnosis, and Markdown improvement tracking.
- **CI/CD Quality Gate:** Automated baseline vs candidate regression checking (flags metric drops > 0.05).

---

## 📁 Skill Structure

```text
skills/ai_evaluation_skill/
├── SKILL.md              # Autonomous Agent Runbook, Architecture Blueprint & Checklists
├── README.md             # Developer integration guide & quickstart examples
└── templates/            # Generic Python evaluation modules
    ├── __init__.py
    ├── models.py         # Data models (QAPair, EvalResult, BenchmarkSummary, etc.)
    ├── dataset_validator.py # Provenance and schema validator
    ├── evaluator_core.py # Core heuristic & rank-aware metrics
    ├── llm_judge.py      # LLM-as-a-Judge & bias detection
    ├── benchmark_runner.py # Evaluation harness & regression tester
    └── failure_analyzer.py # 5-Whys diagnosis & Markdown tracker generator
```

---

## 🚀 Quick Start Example

```python
from pathlib import Path
from skills.ai_evaluation_skill.templates import (
    GoldenDatasetValidator,
    GenericRAGEvaluator,
    GenericBenchmarkRunner,
    GenericFailureAnalyzer,
    StratificationContract,
)

# 1. Validate Golden Dataset & Corpus Provenance
validator = GoldenDatasetValidator(corpus_root="data/corpus")
qa_pairs = validator.validate_dataset_file(
    "golden_dataset.json",
    contract=StratificationContract(min_easy=5, min_medium=7, min_hard=5, min_adversarial=3),
)

# 2. Define inference wrapper (Blind Inference)
def my_agent_inference(question: str) -> tuple[str, list[str]]:
    # Call your RAG / LLM agent
    answer = "..."
    retrieved_chunks = ["..."]
    return answer, retrieved_chunks

# 3. Run Benchmark Suite
evaluator = GenericRAGEvaluator(pass_threshold=0.5)
runner = GenericBenchmarkRunner(evaluator=evaluator)
results = runner.run_benchmark(qa_pairs, my_agent_inference)

# 4. Generate Summary & Check CI/CD Quality Gate
summary = runner.generate_summary(results)
print(f"Pass Rate: {summary.pass_rate:.1%}")
print(f"Avg Faithfulness: {summary.avg_faithfulness:.3f}")

is_passed, violations = runner.check_quality_gate(
    summary, min_pass_rate=0.80, min_faithfulness=0.70
)
if not is_passed:
    print(f"❌ Quality gate blocked: {violations}")

# 5. Triage Failures & Output Markdown Improvement Log
failures = [r for r in results if not r.passed]
analyzer = GenericFailureAnalyzer()
log_markdown = analyzer.generate_improvement_log_markdown(failures)
Path("improvement_log.md").write_text(log_markdown, encoding="utf-8")
print(f"Logged {len(failures)} failures to improvement_log.md")
```

---

## 🛠️ Integration with CI/CD Pipelines

To run this evaluation as a mandatory GitHub Actions quality gate before merging pull requests:

```yaml
name: AI Evaluation Quality Gate
on: [pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Dependencies
        run: pip install -r requirements.txt
      - name: Run AI Benchmark Suite
        run: |
          python -m pytest tests/test_evaluation.py --strict-markers
```
