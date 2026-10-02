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
