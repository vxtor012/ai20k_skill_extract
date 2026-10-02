# AI Agent Skills

Tập hợp các skill được trích xuất từ các bài lab trong khóa học AI in action. Mỗi skill là một gói độc lập, có hướng dẫn chuyên sâu trong `SKILL.md` và các module mẫu trong thư mục `templates/`.

## Các skill

| Skill | Phạm vi | Tài liệu |
| --- | --- | --- |
| AI & RAG Evaluation | Kiểm định dataset, đánh giá chất lượng câu trả lời và truy xuất, phân tích lỗi, so sánh baseline và thiết lập quality gate cho CI/CD. | [README](skills/ai_evaluation_skill/README.md) · [SKILL.md](skills/ai_evaluation_skill/SKILL.md) |
| LLMOps Observability | Thiết lập structured logging có lọc PII, distributed tracing, quản lý phiên bản và rollback prompt, theo dõi SLO/error budget, và phân tích sự cố theo chuỗi metrics, logs, traces. | [README](skills/llmops_observability_skill/README.md) · [SKILL.md](skills/llmops_observability_skill/SKILL.md) |
| Responsible Agent Guardrails | Phòng thủ nhiều lớp cho agent: kiểm tra input/output, kiểm soát egress và tool, chuyển tiếp yêu cầu rủi ro cao tới người duyệt (HITL), ghi audit log. | [README](skills/responsible_agent_guardrails_skill/README.md) · [SKILL.md](skills/responsible_agent_guardrails_skill/SKILL.md) |

## Cấu trúc

```text
skills/
├── ai_evaluation_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Module mẫu cho validation, metrics, benchmark và phân tích lỗi
├── llmops_observability_skill/
│   ├── README.md
│   ├── SKILL.md
│   └── templates/       # Module mẫu cho logging, tracing, prompt, SLO và phân tích sự cố
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

Các template là mã tham khảo, không tự cấu hình hoặc bảo đảm an toàn cho một hệ thống cụ thể. Hãy kiểm tra giả định, ngưỡng, dependency và phạm vi kiểm thử của từng module trước khi sử dụng.

## Yêu cầu

Các template được viết bằng Python. Yêu cầu phiên bản Python và dependency cụ thể (nếu có) cần được xác nhận trong tài liệu hoặc mã nguồn của từng skill; repository hiện không khai báo một cấu hình cài đặt chung ở cấp gốc.
