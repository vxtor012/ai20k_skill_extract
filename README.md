# AI Agent Skills

Tập hợp các skill được trích xuất từ các bài lab trong khóa học AI in action. Mỗi skill là một gói độc lập, có hướng dẫn chuyên sâu trong `SKILL.md` và các module mẫu trong thư mục `templates/`.

## Các skill

| Skill | Phạm vi | Tài liệu |
| --- | --- | --- |
| Agentic Tool Evaluation Harness | Agent gọi công cụ: orchestration nhiều lượt, provider adapters, routing/tham số tool và runtime confirmation. Không dùng để chấm chất lượng câu trả lời tổng quát. | [README](skills/agentic_tool_eval_harness_skill/README.md) · [SKILL.md](skills/agentic_tool_eval_harness_skill/SKILL.md) |
| AI & RAG Evaluation | Dataset, blind inference, chất lượng câu trả lời/truy xuất, failure analysis và regression gates. Không sở hữu logic dispatch tool hoặc độ tin cậy ingestion. | [README](skills/ai_evaluation_skill/README.md) · [SKILL.md](skills/ai_evaluation_skill/SKILL.md) |
| Data Pipeline Observability | Độ tin cậy từ ingestion đến index: lineage, data quality, freshness, chaos testing và replay/repair. Không phải observability cho request, logs hay traces của ứng dụng. | [README](skills/data_pipeline_observability/README.md) · [SKILL.md](skills/data_pipeline_observability/SKILL.md) |
| LLMOps Observability | Telemetry runtime cho LLM/RAG: structured logs, traces, prompt versioning, SLO và incident triage. Không thay thế policy engine hay data-pipeline quality gates. | [README](skills/llmops_observability_skill/README.md) · [SKILL.md](skills/llmops_observability_skill/SKILL.md) |
| RAG Data Foundation | Các building blocks có thể tái sử dụng: chunking, embeddings, vector store và dense retrieval cơ bản. Dùng RAG Pipeline cho tích hợp đầu-cuối/hybrid nâng cao. | [README](skills/rag_data_foundation_skill/README.md) · [SKILL.md](skills/rag_data_foundation_skill/SKILL.md) |
| RAG Pipeline | Tích hợp RAG đầu-cuối: đa định dạng, hybrid retrieval/RRF, OOD fallback, citation-grounded generation và benchmark. Dùng Data Foundation cho component độc lập. | [README](skills/rag_pipeline_skill/README.md) · [SKILL.md](skills/rag_pipeline_skill/SKILL.md) |
| Responsible Agent Guardrails | Ranh giới bảo mật/policy chung: input/output checks, egress, HITL và audit. Agent Harness chỉ giữ kiểm soát cụ thể khi thực thi tool. | [README](skills/responsible_agent_guardrails_skill/README.md) · [SKILL.md](skills/responsible_agent_guardrails_skill/SKILL.md) |

## Cấu trúc

```text
skills/
├── agentic_tool_eval_harness_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Orchestrator, provider adapters, evaluation, guardrails và tool registry
├── ai_evaluation_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Module mẫu cho validation, metrics, benchmark và phân tích lỗi
├── data_pipeline_observability/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Quality gate, freshness SLA, chaos injection, evaluator và idempotent repair
├── llmops_observability_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Module mẫu cho logging, tracing, prompt, SLO và phân tích sự cố
├── rag_data_foundation_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Chunking, embeddings, vector store, pipeline RAG và benchmark truy xuất
├── rag_pipeline_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Ingest, chunking, hybrid retrieval, generation có citation và đánh giá RAG Triad
└── responsible_agent_guardrails_skill/
    ├── README.md
    ├── SKILL.md
    └── templates/       # Module mẫu cho guardrails, egress, HITL và observability
```

## Bắt đầu

1. Chọn skill phù hợp với công việc cần làm.
2. Đọc `SKILL.md` để xem nguyên tắc, quy trình và yêu cầu áp dụng.
3. Xem README riêng của skill để biết cấu trúc và ví dụ tích hợp.
4. Điều chỉnh các template theo chính sách, dữ liệu, model và hạ tầng của dự án trước khi đưa vào môi trường thực tế.

## Chọn skill

- Đánh giá câu trả lời hoặc RAG: **AI & RAG Evaluation**. Đánh giá lựa chọn tool, số lần gọi và arguments: **Agentic Tool Evaluation Harness**.
- Xây dựng component chunk/embed/vector độc lập: **RAG Data Foundation**. Xây dựng pipeline RAG tích hợp, hybrid hoặc có fallback: **RAG Pipeline**.
- Điều tra chất lượng dữ liệu từ nguồn đến vector index: **Data Pipeline Observability**. Điều tra telemetry của request/model trong production: **LLMOps Observability**.
- Thiết kế chính sách an toàn, kiểm soát egress hoặc HITL cho agent: **Responsible Agent Guardrails**.

Các skill có thể phối hợp nhưng không thay thế lẫn nhau. Chọn skill theo lớp đang thay đổi; chỉ nạp skill liên quan khi cần phần việc thuộc phạm vi của nó.

Các template là mã tham khảo, không tự cấu hình hoặc bảo đảm an toàn cho một hệ thống cụ thể. Hãy kiểm tra giả định, ngưỡng, dependency và phạm vi kiểm thử của từng module trước khi sử dụng.

## Yêu cầu

Các template được viết bằng Python. Yêu cầu phiên bản Python và dependency cụ thể (nếu có) cần được xác nhận trong tài liệu hoặc mã nguồn của từng skill; repository hiện không khai báo một cấu hình cài đặt chung ở cấp gốc.
