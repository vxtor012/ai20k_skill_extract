from __future__ import annotations

import re


class InjectionDetector:
    """Detect and sanitize prompt injections, pseudo-system role triggers, and forged outputs."""

    # Common injection patterns in user inputs or retrieved external contents
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
        re.compile(r"developer\s*:\s*override", re.IGNORECASE),
        re.compile(r"\[SYSTEM_PROMPT\]", re.IGNORECASE),
        re.compile(r"<\s*script\s*>", re.IGNORECASE),
        re.compile(r"TOOL_RESULTS_JSON\s*:", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """Sanitize text retrieved from external or untrusted sources to prevent prompt injection."""
        sanitized = text
        for pattern in cls.INJECTION_PATTERNS:
            sanitized = pattern.sub("[SANITIZED_INSTRUCTION_REMOVED]", sanitized)
        return sanitized

    @classmethod
    def is_suspicious(cls, text: str) -> bool:
        """Check if incoming prompt contains high-risk jailbreak/injection tokens."""
        return any(pattern.search(text) for pattern in cls.INJECTION_PATTERNS)
