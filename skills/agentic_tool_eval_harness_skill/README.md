# Agentic Tool Evaluation Harness Skill

## 1. Overview & Architectural Philosophy

The **Agentic Tool Evaluation Harness** is a generalized, production-ready framework for building, testing, securing, and iteratively improving tool-calling AI agents. It abstracts vendor APIs, provides autonomous multi-turn tool calling with human-in-the-loop clarification pausing, computes deterministic routing and argument metrics, and enforces dual-layer guardrails (prompt boundary + runtime defensive validation).

```
 ┌────────────────────────────────────────────────────────┐
 │                   User / Client Turn                   │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │           Dual-Layer Input & Injection Sanitizer       │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │         Generic Tool Orchestrator (Multi-Round)         │
 │   ┌──────────────┐     ┌──────────────┐     ┌────────┐ │
 │   │ LLM Provider │ ──► │ Tool Dispatch│ ──► │Clarify?│ │
 │   └──────────────┘     └──────────────┘     └────┬───┘ │
 └──────────────────────────┬───────────────────────┼─────┘
                            │ (Complete)            │ (Awaiting)
                            ▼                       ▼
 ┌───────────────────────────────────┐    ┌───────────────┐
 │ Final Structured/Text Response    │    │ User Interrupt│
 └───────────────────────────────────┘    └───────────────┘
```

---

## 2. Directory Layout

```text
skills/agentic_tool_eval_harness_skill/
├── SKILL.md                  # Comprehensive AI Agent Runbook & Execution Guide
├── README.md                 # Developer integration guide & architecture reference
└── templates/                # Modular generic implementation files
    ├── core/                 # Orchestrator, Types, Checksums, and Version Loggers
    │   ├── types.py          # Generic Dataclasses & Protocols
    │   ├── agent.py          # Multi-round autonomous tool loop & dispatcher
    │   └── versioning.py     # SHA-256 artifact hashing & CSV experiment tracking
    ├── providers/            # Vendor-agnostic LLM Adapters
    │   ├── base.py           # Tool schema converters (OpenAI, Anthropic)
    │   ├── openai_adapter.py # OpenAI / Compatible adapter (Ollama, OpenRouter)
    │   ├── anthropic_adapter.py # Anthropic Claude adapter
    │   └── gemini_adapter.py # Google Gemini adapter
    ├── evaluation/           # Deterministic benchmark engine
    │   ├── schema.py         # Evaluation case & metrics schemas
    │   └── evaluator.py      # Subset matchers, failure categorizer & suite runner
    ├── guardrails/           # Multi-layered safety & boundary defenses
    │   ├── safety.py         # Dual-layer data scrubber & confirmation enforcer
    │   └── injection.py      # Prompt injection & delimiter sanitizer
    └── tools/                # Extensible tool registry & templates
        ├── base.py           # BaseTool ABC & ToolRegistry
        └── examples/
            ├── read_only.py  # Generic search/query tool template
            └── stateful_action.py # Mutating action tool with confirmation enforcement
```

---

## 3. Quickstart Example

### Initializing the Orchestrator & Tools

```python
from skills.agentic_tool_eval_harness_skill.templates.core import GenericToolOrchestrator
from skills.agentic_tool_eval_harness_skill.templates.providers import make_provider
from skills.agentic_tool_eval_harness_skill.templates.tools import ToolRegistry, GenericSearchTool, GenericActionTool

# 1. Initialize Provider
provider = make_provider("openai", model="gpt-4o-mini")

# 2. Register Tools
registry = ToolRegistry()
search_tool = GenericSearchTool(data_source=[
    {"title": "VPN Guide", "content": "Set gateway to vpn.example.com", "category": "network"}
])
registry.register(search_tool)
registry.register(GenericActionTool())

# 3. Initialize Orchestrator
orchestrator = GenericToolOrchestrator(
    provider=provider,
    system_prompt="You are a technical support agent. Use declared tools to assist users.",
    tool_declarations=registry.get_declarations(),
    tool_registry=registry.handlers,
    max_tool_rounds=5,
)

# 4. Execute a Turn
history = [{"role": "user", "content": "How do I configure the VPN gateway?"}]
run_result = orchestrator.run_turn(history)

print("Status:", run_result.status)
print("Reply:", run_result.assistant_text)
```

---

## 4. Running Systematic Evaluation

```python
from skills.agentic_tool_eval_harness_skill.templates.evaluation import (
    SuiteEvaluator, EvalCase, ExpectedToolCall, FailureType
)

# Define test cases
cases = [
    EvalCase(
        id="case_01_search",
        phase="core",
        failure_type=FailureType.WRONG_TOOL,
        input="How do I connect to VPN?",
        expected_calls=[ExpectedToolCall(name="search_knowledge_base", args={"query": "vpn"})],
    )
]

def run_case(case: EvalCase):
    history = [{"role": "user", "content": case.input or ""}]
    res = orchestrator.run_turn(history)
    calls = [
        ToolCall(name=evt.tool, args=evt.args) for evt in res.tool_events
    ]
    return calls, res.assistant_text

evaluator = SuiteEvaluator(cases)
metrics, results = evaluator.run(run_case)

print(f"Pass Rate: {metrics.pass_rate:.2%}")
print(f"Routing Accuracy: {metrics.routing_accuracy:.2%}")
print(f"Args Accuracy: {metrics.args_accuracy:.2%}")
```

---

## 5. Security & Boundary Guardrails

1. **Explicit Confirmation for State Mutations**: Never execute write operations (`create_ticket`, `delete_record`, `transfer_funds`) without `confirmed=True` verified against the exact current payload.
2. **Data Minimization & Boundary Isolation**: Never forward internal identifiers (e.g. employee IDs, asset IDs, internal hostnames, tokens) to external search engines or untrusted endpoints.
3. **Prompt Injection Neutralization**: All retrieved untrusted content is sanitized via `InjectionDetector.sanitize_untrusted_text()`.
