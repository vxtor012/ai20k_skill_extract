---
name: responsible-agent-guardrails
description: Implements a production-grade, defense-in-depth security boundary, guardrails, egress enforcement, HITL routing, and observability for autonomous LLM agents. Trigger when building secure AI pipelines, sanitizing LLM inputs/outputs, preventing prompt injections/data leaks, or configuring human-in-the-loop validation.
keywords:
  - guardrails
  - prompt-injection
  - pii-redaction
  - hitl
  - egress-gateway
  - defense-in-depth
  - responsible-ai
  - secret-detection
  - audit-logging
---

# Responsible Agent Guardrails & Governance Skill

## 1. Core Philosophy & Architectural Blueprint

Mọi hệ thống Agent tự trị khi vận hành trong môi trường thực tế đều phải tuân thủ nguyên lý **"Zero Trust for Model Context"**:
1. Dữ liệu từ người dùng hoặc hệ thống ngoài (RAG, Web scraping, Tools) là **Untrusted Data**, không bao giờ được coi là System Directives.
2. Dữ liệu sinh ra từ LLM là **Unverified Predictions**, bắt buộc phải qua kiểm duyệt trước khi hiển thị cho người dùng hoặc chuyển cho Tools thực thi.
3. Các hành động mang tính rủi ro cao (phá hủy dữ liệu, giao dịch tài chính, thay đổi quyền hạn) phải luôn được kiểm soát bởi Policy Engine và Human-in-the-loop (HITL).

```mermaid
flowchart TD
    In[User / System Input] --> RL[Layer 0: Rate Limiter]
    RL -->|Pass| IG[Layer 1: Input Guardrail]
    RL -->|Exceeded| Block429[Return 429 Rate Limit]
    
    IG -->|Sanitized & ALLOW| LLM[Layer 2: Agent LLM Core]
    IG -->|BLOCK| BlockInj[Return Safe Rejection]
    
    LLM --> OG[Layer 3: Output Guardrail]
    OG -->|Clean / Redacted| EG[Layer 4: Egress & Tool Gateway]
    OG -->|Unsafe & Blocked| BlockLeak[Return Filtered Response]
    
    EG -->|Allowed Sink| HR[Layer 5: HITL Risk Router]
    EG -->|Unauthorized Sink| BlockEgress[Block Egress Action]
    
    HR -->|Low Risk & High Conf| Out[Deliver to User / Execute Tool]
    HR -->|High Risk / Low Conf| Human[Escalate to Human Queue]
    
    Block429 -.-> Obs[Layer 6: Audit & Telemetry]
    BlockInj -.-> Obs
    BlockLeak -.-> Obs
    BlockEgress -.-> Obs
    Out -.-> Obs
    Human -.-> Obs
```

---

## 2. Step-by-Step Execution Guide for Agents

Khi được kích hoạt trên một repository hoặc hệ thống Agent mới, Agent phải thực hiện tuần tự theo quy trình 5 bước:

### Bước 1: Khảo sát & Định cấu hình Chính sách (Policy & Boundaries)
- Xác định danh sách các Tool/Action có mức độ rủi ro cao (`HIGH_RISK_ACTIONS`).
- Xác định danh sách các Domain/Endpoint được phép kết nối ra ngoài (`TRUSTED_EGRESS_HOSTS`).
- Định nghĩa ngưỡng rate-limiting (Requests per Window) và các định dạng PII/Secret đặc thù của dự án.

### Bước 2: Thiết lập Pipeline Input Sanitization
- Triển khai bộ chuẩn hóa Unicode (`NFKC`) và xóa sạch Zero-Width characters.
- Thiết lập bộ lọc phát hiện Prompt Injection (Direct, Indirect, Multilingual, Roleplay, Delimiter manipulations).

### Bước 3: Thiết lập Pipeline Output Sanitization
- Tích hợp bộ lọc PII đa tầng (Regex cấu trúc + Redaction).
- Tích hợp bộ phát hiện Secret dựa trên mẫu định danh + bộ tính toán **Shannon Entropy** ($\ge 3.8$).
- Bật cơ chế **De-obfuscation Engine** để xử lý các chuỗi ký tự bị cố tình chèn khoảng trắng/dấu phân tách nhằm bypass regex.

### Bước 4: Cấu hình Egress Control & HITL Router
- Bao bọc tất cả lời gọi mạng/tool bằng `is_egress_allowed()`. Chặn đứng nếu payload chứa secret hoặc đích đến không nằm trong allowlist.
- Xây dựng ma trận điều hướng HITL dựa trên: `action_type`, `risk_level`, và `confidence_score`.

### Bước 5: Kích hoạt Observability & Test Kháng cự (Adversarial Validation)
- Ghi toàn bộ trace vào file/bộ nhớ append-only structured audit log (bao gồm latency, payload hash, quyết định chặn).
- Chạy bộ kiểm thử Red-Team tự động (Prompt Injection, Unicode Jailbreak, Character Spacing Leak, High-risk Action Bypass) để nghiệm thu hệ thống.

---

## 3. Reusable Code Templates & Patterns

Toàn bộ code mẫu được chuẩn hóa bằng Python 3.10+ Type Hints, Generic, Configuration-Driven và hoàn toàn độc lập với domain nghiệp vụ.

### 3.1. Input Guardrail: Normalization & Injection Detector

```python
from __future__ import annotations
import re
import unicodedata
from enum import Enum
from typing import NamedTuple

class GuardrailDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"

class InputAnalysisResult(NamedTuple):
    decision: GuardrailDecision
    reason: str
    sanitized_text: str

class InputGuardrailEngine:
    """Zero-trust input sanitization and prompt injection detector."""

    ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff\u2060\u00ad"
    
    # Generic Prompt Injection Signatures
    DEFAULT_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)?\s*instructions?",
        r"(?i)disregard\s+(all\s+)?(previous|above|prior)?\s*(instructions?|rules?)",
        r"(?i)system\s+prompt",
        r"(?i)reveal\s+(your\s+)?(instructions?|prompt|system|configuration)",
        r"(?i)you\s+are\s+now\s+(a|an)?\s*\w+",
        r"(?i)act\s+as\s+(a\s+|an\s+)?(unrestricted|jailbroken|root|admin)",
        r"(?i)output\s+only\s+(the\s+)?(password|secret|key|token|system)",
        r"(?i)bỏ\s+qua\s+(mọi\s+)?hướng\s+dẫn",
        r"(?i)tiết\s+lộ\s+(mật\s+khẩu|system\s*prompt)",
    ]

    def __init__(self, custom_patterns: list[str] | None = None):
        self.patterns = [re.compile(p) for p in (custom_patterns or self.DEFAULT_PATTERNS)]

    def canonicalize(self, text: str) -> str:
        """Normalize Unicode to NFKC and strip invisible/zero-width characters."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        return normalized.translate(str.maketrans("", "", self.ZERO_WIDTH_CHARS))

    def evaluate(self, raw_input: str) -> InputAnalysisResult:
        clean_text = self.canonicalize(raw_input)
        for pattern in self.patterns:
            if pattern.search(clean_text):
                return InputAnalysisResult(
                    decision=GuardrailDecision.BLOCK,
                    reason=f"Pattern match: {pattern.pattern}",
                    sanitized_text=clean_text,
                )
        return InputAnalysisResult(
            decision=GuardrailDecision.ALLOW,
            reason="Input passed all security checks",
            sanitized_text=clean_text,
        )
```

### 3.2. Output Guardrail: PII, Entropy Secret & De-obfuscation Engine

```python
from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class OutputFilterResult:
    is_safe: bool
    redacted_content: str
    violations: list[str] = field(default_factory=list)

class OutputGuardrailEngine:
    """Multi-layer output inspection: PII, Regex Secrets, Entropy, and De-obfuscation."""

    PII_REGEX_RULES: Dict[str, str] = {
        "EMAIL": r"[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}",
        "PHONE_NUMBER": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "API_OR_SECRET_KEY": r"\b(?:sk|pk|api|key|token|sec)[-_][a-zA-Z0-9_-]{8,}\b",
        "PRIVATE_KEY_HEADER": r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
    }

    def __init__(self, entropy_threshold: float = 3.8, min_entropy_len: int = 12):
        self.entropy_threshold = entropy_threshold
        self.min_entropy_len = min_entropy_len
        self.compiled_rules = {k: re.compile(v, re.IGNORECASE) for k, v in self.PII_REGEX_RULES.items()}
        # Detect spaced-out token obfuscation: e.g. "s - k - s e c r e t"
        self.obfuscation_pattern = re.compile(
            r"(?<![a-zA-Z0-9])(?:[a-zA-Z0-9][\s\-_.\\/]+){5,}[a-zA-Z0-9](?![a-zA-Z0-9])"
        )

    @staticmethod
    def calculate_shannon_entropy(data: str) -> float:
        """Calculate Shannon entropy (bits per character) to detect high-randomness secrets."""
        if not data:
            return 0.0
        counts = Counter(data)
        length = len(data)
        return -sum((c / length) * math.log2(c / length) for c in counts.values())

    def filter(self, text: str) -> OutputFilterResult:
        if not text:
            return OutputFilterResult(is_safe=True, redacted_content="")

        violations = []
        redacted = text

        # 1. Structural Pattern & PII Filtering
        for name, pattern in self.compiled_rules.items():
            matches = pattern.findall(redacted)
            if matches:
                violations.append(f"Detected {name} ({len(matches)} instance(s))")
                redacted = pattern.sub("[REDACTED]", redacted)

        # 2. De-obfuscation & Anti-Evasion Detection
        for match in self.obfuscation_pattern.finditer(text):
            raw_fragment = match.group(0)
            collapsed = re.sub(r"[\s\-_.\\/]+", "", raw_fragment).casefold()
            
            # Check high entropy on collapsed string or signature prefixes
            if len(collapsed) >= self.min_entropy_len and self.calculate_shannon_entropy(collapsed) >= self.entropy_threshold:
                violations.append("Detected high-entropy obfuscated token")
                redacted = redacted.replace(raw_fragment, "[REDACTED_SECRET]")

        return OutputFilterResult(
            is_safe=len(violations) == 0,
            redacted_content=redacted,
            violations=violations,
        )
```

### 3.3. Egress Gateway & Policy-as-Code Enforcer

```python
from __future__ import annotations
from urllib.parse import urlparse
from typing import Set

class EgressPolicyGateway:
    """Enforces strict network egress boundaries and data leakage prevention."""

    def __init__(self, allowed_hosts: Set[str]):
        self.allowed_hosts = allowed_hosts

    def is_request_permitted(self, target_url: str, payload_str: str) -> tuple[bool, str]:
        try:
            parsed = urlparse(target_url)
            if parsed.scheme != "https":
                return False, "Non-HTTPS egress destination is strictly forbidden."
            if parsed.hostname not in self.allowed_hosts:
                return False, f"Destination host '{parsed.hostname}' is not in trusted allowlist."
        except Exception as e:
            return False, f"Malformed target URL: {e}"

        # Sensitive keyword / leaked credential check
        forbidden_indicators = ["BEGIN PRIVATE KEY", "bearer ", "sk-", "password="]
        if any(ind.lower() in payload_str.lower() for ind in forbidden_indicators):
            return False, "Payload contains unauthorized sensitive credentials or tokens."

        return True, "Egress authorized."
```

### 3.4. Human-In-The-Loop (HITL) Confidence & Risk Router

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Set

class DecisionAction(str, Enum):
    AUTO_EXECUTE = "AUTO_EXECUTE"
    QUEUE_REVIEW = "QUEUE_REVIEW"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"

@dataclass(frozen=True)
class HITLDecision:
    action: DecisionAction
    requires_human: bool
    priority: str
    rationale: str

class HITLConfidenceRouter:
    """Routes agent execution paths based on operational risk and confidence levels."""

    def __init__(
        self,
        high_risk_actions: Set[str],
        high_confidence_thresh: float = 0.90,
        medium_confidence_thresh: float = 0.70,
    ):
        self.high_risk_actions = high_risk_actions
        self.high_confidence_thresh = high_confidence_thresh
        self.medium_confidence_thresh = medium_confidence_thresh

    def route(self, action_name: str, confidence_score: float) -> HITLDecision:
        # Rule 1: High-risk actions unconditionally require human escalation
        if action_name in self.high_risk_actions:
            return HITLDecision(
                action=DecisionAction.ESCALATE_HUMAN,
                requires_human=True,
                priority="HIGH",
                rationale=f"Action '{action_name}' is classified as High Risk.",
            )

        # Rule 2: Low confidence requires immediate escalation
        if confidence_score < self.medium_confidence_thresh:
            return HITLDecision(
                action=DecisionAction.ESCALATE_HUMAN,
                requires_human=True,
                priority="HIGH",
                rationale=f"Confidence score {confidence_score:.2f} is below minimum threshold.",
            )

        # Rule 3: Medium confidence queued for asynchronous review
        if confidence_score < self.high_confidence_thresh:
            return HITLDecision(
                action=DecisionAction.QUEUE_REVIEW,
                requires_human=True,
                priority="NORMAL",
                rationale=f"Confidence score {confidence_score:.2f} requires supervisory validation.",
            )

        # Rule 4: High confidence auto-execution
        return HITLDecision(
            action=DecisionAction.AUTO_EXECUTE,
            requires_human=False,
            priority="LOW",
            rationale="High confidence with standard risk profile.",
        )
```

---

## 4. Edge Cases, Anti-patterns & Best Practices

### Các Cạm bẫy Kỹ thuật Phổ biến (Anti-Patterns)
1. **Relying solely on Regex for Injections:** Kẻ tấn công có thể dùng kỹ thuật mã hóa (Base64, Rot13), đa ngôn ngữ, hoặc tách từ (`I-g-n-o-r-e`). *Khắc phục:* Luôn kết hợp chuẩn hóa Unicode + De-obfuscation + LLM Evaluation nếu cần.
2. **Boolean Trap in Guardrail Interfaces:** Trả về `bool` (ví dụ `is_valid`) dễ dẫn đến lỗi đảo ngược logic giữa các tầng (layer này hiểu `True` là cho qua, layer khác hiểu `True` là phát hiện mã độc). *Khắc phục:* Sử dụng Explicit Enums (`GuardrailDecision.ALLOW` / `GuardrailDecision.BLOCK`).
3. **Fail-Open Egress Policies:** Khi có lỗi phân tích URL hoặc dịch vụ Guardrail gặp sự cố (timeout/exception), mặc định cho phép gửi request. *Khắc phục:* Luôn bọc trong khối `try-except` và thiết lập tư thế **Fail-Closed (Từ chối mặc định)**.
4. **Hardcoded Secrets & Heuristics:** Hardcode chuỗi secret cụ thể vào logic guardrail. Khi secret xoay vòng (rotation), hệ thống phòng thủ sẽ bị vô hiệu. *Khắc phục:* Quét theo cấu trúc Entropy và Pattern tổng quát.

---

## 5. Tiêu chí Nghiệm thu Kỹ thuật (Technical Acceptance Checklist)

Trước khi đánh dấu hoàn thành tích hợp Guardrails vào bất kỳ Agent Pipeline nào:

- [ ] **Unicode Invariance:** Input chứa ký tự ẩn (`\u200b`), ký tự ghép Unicode đều được normalize về canonical form trước khi phân tích.
- [ ] **Strict Input Blocking:** Các prompt injection mẫu (Direct overrides, Roleplay attacks) bị chặn với status `BLOCK` và không bao giờ chạm tới Model Reasoning Context.
- [ ] **PII & Credential Scrubbing:** Output của model không được chứa số điện thoại, email, private key header, hoặc token ngẫu nhiên dạng entropy cao; tất cả phải được thay thế bằng `[REDACTED]`.
- [ ] **De-obfuscation Resilience:** Các chuỗi secret bị chèn dấu phân tách (spaces, hyphens, dots) vẫn bị phát hiện và làm sạch.
- [ ] **Egress Whitelisting:** Agent không thể gửi HTTP request tới bất kỳ domain nào ngoài `allowed_hosts`.
- [ ] **Deterministic HITL Routing:** Các hành động nằm trong danh mục rủi ro cao hoặc có confidence $< 0.70$ bắt buộc phải sinh ra quyết định `ESCALATE_HUMAN`.
- [ ] **Forensic Audit Readiness:** Mọi tương tác (input, output đã lọc, layer quyết định, execution latency) đều được ghi nhận vào file audit log cấu trúc JSON/JSONL.
