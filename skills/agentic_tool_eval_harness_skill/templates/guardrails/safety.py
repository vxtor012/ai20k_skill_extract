from __future__ import annotations

import re
from typing import Any


class SafetyViolationError(RuntimeError):
    """Raised when an operation violates security or privacy boundaries."""
    pass


class DualLayerSafetyValidator:
    """
    Dual-layer defense system:
    Layer 1: Schema/Declaration boundary validation
    Layer 2: Runtime input/output sanitizer and confirmation enforcement
    """

    # Disallowed internal parameters in outbound external search/calls
    RESTRICTED_EXTERNAL_KEYS = {
        "employee_id",
        "asset_id",
        "serial_number",
        "password",
        "secret",
        "token",
        "api_key",
        "ssn",
        "internal_ip",
    }

    # Sensitive credential patterns
    CREDENTIAL_REGEX = re.compile(
        r"(bearer\s+[a-zA-Z0-9_\-\.]{20,}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{32,}|password\s*[:=]\s*\S+)",
        re.IGNORECASE,
    )

    @classmethod
    def sanitize_outbound_payload(cls, payload: dict[str, Any], allowed_keys: set[str] | None = None) -> dict[str, Any]:
        """
        Ensure internal identifiers, secrets or non-whitelisted parameters
        never leak across external boundaries.
        """
        sanitized = {}
        for k, v in payload.items():
            if k.lower() in cls.RESTRICTED_EXTERNAL_KEYS:
                continue
            if allowed_keys is not None and k not in allowed_keys:
                continue
            if isinstance(v, str):
                if cls.CREDENTIAL_REGEX.search(v):
                    raise SafetyViolationError(f"Potential credential/token detected in parameter '{k}'")
            sanitized[k] = v
        return sanitized

    @staticmethod
    def verify_action_confirmation(
        confirmed: bool,
        required_summary: str,
        current_context_summary: str | None = None,
    ) -> bool:
        """
        Enforce state-altering action safety.
        A prior confirmation is strictly INVALID if the action payload has been altered.
        """
        if not confirmed:
            return False
        if current_context_summary and required_summary != current_context_summary:
            return False
        return True
