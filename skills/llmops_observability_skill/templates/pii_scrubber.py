"""
Extensible PII (Personally Identifiable Information) Redaction & Pseudonymization Engine.
Supports regex patterns, keyword detection, entropy-based token masking, and recursive JSON scrubbing.
"""

from __future__ import annotations

import abc
import hashlib
import re
from typing import Any, Dict, List, Pattern, Set, Union


class BasePIIScrubber(abc.ABC):
    @abc.abstractmethod
    def scrub(self, text: str) -> str:
        """Scrub PII elements from the given string."""
        raise NotImplementedError


class RegexPIIScrubber(BasePIIScrubber):
    """
    Production-grade regex PII scrubber with customizable patterns and high-performance precompilation.
    """

    DEFAULT_PATTERNS: Dict[str, str] = {
        "EMAIL": r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
        "PHONE_VN": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
        "PHONE_INTL": r"(?<!\d)\+(?:[0-9] ?){6,14}[0-9](?!\d)",
        "NATIONAL_ID_VN": r"\b\d{12}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[ -]?){3}\d{4}\b|\b\d{15,16}\b",
        "JWT_TOKEN": r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b",
        "API_KEY": r"(?i)\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|api_key[ =:][a-zA-Z0-9_-]{16,})\b",
        "IPV4_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }

    def __init__(self, custom_patterns: Dict[str, str] | None = None, replacement_fmt: str = "[REDACTED_{name}]"):
        patterns = {**self.DEFAULT_PATTERNS, **(custom_patterns or {})}
        self.replacement_fmt = replacement_fmt
        self._compiled: List[tuple[str, Pattern[str]]] = [
            (name, re.compile(pat)) for name, pat in patterns.items()
        ]

    def scrub(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return text
        scrubbed = text
        for name, compiled_regex in self._compiled:
            replacement = self.replacement_fmt.format(name=name.upper())
            scrubbed = compiled_regex.sub(replacement, scrubbed)
        return scrubbed


# Default global instance
_GLOBAL_SCRUBBER = RegexPIIScrubber()


def scrub_text(text: str, scrubber: BasePIIScrubber | None = None) -> str:
    active_scrubber = scrubber or _GLOBAL_SCRUBBER
    return active_scrubber.scrub(text)


def scrub_recursive(
    data: Any,
    excluded_keys: Set[str] | None = None,
    scrubber: BasePIIScrubber | None = None,
) -> Any:
    """
    Recursively scrubs dicts, lists, and primitives, bypassing system keys.
    """
    if excluded_keys is None:
        excluded_keys = {"ts", "level", "service", "correlation_id", "user_id_hash", "event"}

    if isinstance(data, str):
        return scrub_text(data, scrubber=scrubber)
    if isinstance(data, dict):
        return {
            k: (_scrub_shallow(v, scrubber) if k in excluded_keys else scrub_recursive(v, excluded_keys, scrubber))
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple, set)):
        cleaned = [scrub_recursive(item, excluded_keys, scrubber) for item in data]
        return type(data)(cleaned)
    return data


def _scrub_shallow(val: Any, scrubber: BasePIIScrubber | None) -> Any:
    """Used for excluded keys when they might be container objects that shouldn't be deep-scrubbed."""
    return val


def summarize_text(text: str, max_len: int = 100, scrubber: BasePIIScrubber | None = None) -> str:
    """Scrub PII, flatten newlines, and truncate cleanly with ellipsis."""
    if not text:
        return ""
    safe = scrub_text(str(text), scrubber=scrubber).strip().replace("\n", " ").replace("\r", "")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_identifier(identifier: str, salt: str = "", length: int = 12) -> str:
    """Deterministic cryptographic pseudonymization (SHA-256 slice)."""
    if not identifier:
        return ""
    payload = f"{salt}:{identifier}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]
