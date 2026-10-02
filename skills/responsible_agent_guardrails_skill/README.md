# Responsible Agent Guardrails Skill Package

Thư mục này chứa toàn bộ tài liệu kỹ thuật, mô hình tham chiếu kiến trúc và bộ mã nguồn mẫu tổng quát hóa (Generalized Production-Ready Templates) cho hệ thống **Guardrails, Egress Control, Human-In-The-Loop (HITL) và Responsible AI**.

---

## 📁 Cấu trúc Thư mục

```text
responsible_agent_guardrails_skill/
├── SKILL.md                              # Tài liệu Agent Skill chuẩn hóa (YAML frontmatter + Blueprint + Templates)
├── AUDIT_AND_ARCHITECTURAL_ANALYSIS.md   # Báo cáo phân tích Codebase Audit & Mô hình tham chiếu
├── README.md                             # Hướng dẫn tích hợp nhanh
└── templates/                            # Các module Python tổng quát hóa có thể tái sử dụng ngay
    ├── __init__.py
    ├── input_guardrails.py               # Chuẩn hóa Unicode + Nhận diện Prompt Injection đa ngôn ngữ
    ├── output_guardrails.py              # Lọc PII + Quét Shannon Entropy + De-obfuscation Engine
    ├── egress_gateway.py                 # Kiểm soát cổng ra mạng/tool + Allowlist + Data Loss Prevention
    ├── hitl_router.py                    # Ma trận rủi ro & Điều hướng phê duyệt con người (Confidence Router)
    └── observability.py                  # Ghi nhật ký kiểm toán Append-only & Cảnh báo bất thường
```

---

## 🚀 Cách Tích hợp vào Dự án Bất kỳ

```python
from templates.input_guardrails import InputGuardrailEngine, GuardrailDecision
from templates.output_guardrails import OutputGuardrailEngine
from templates.egress_gateway import EgressPolicyGateway
from templates.hitl_router import HITLConfidenceRouter
from templates.observability import ForensicAuditLogger

# 1. Khởi tạo các tầng phòng thủ
input_engine = InputGuardrailEngine()
output_engine = OutputGuardrailEngine(entropy_threshold=3.8)
egress_gw = EgressPolicyGateway(allowed_hosts={"api.yourdomain.com"})
hitl_router = HITLConfidenceRouter(high_risk_actions={"delete_user", "transfer_fund"})
audit_logger = ForensicAuditLogger()

# 2. Xử lý Input
input_res = input_engine.evaluate(user_raw_input)
if input_res.decision == GuardrailDecision.BLOCK:
    return "Yêu cầu bị từ chối do vi phạm chính sách an toàn."

# 3. Chạy LLM Inference ...
llm_response = run_llm_inference(input_res.sanitized_text)

# 4. Xử lý Output & Làm sạch dữ liệu
output_res = output_engine.filter(llm_response)

# 5. Đánh giá rủi ro & Điều phối HITL
decision = hitl_router.route(action_name="general_query", confidence_score=0.95)
if decision.requires_human:
    queue_for_human_approval(output_res.redacted_content)
else:
    send_to_user(output_res.redacted_content)
```
