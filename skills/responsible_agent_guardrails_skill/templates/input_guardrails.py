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
