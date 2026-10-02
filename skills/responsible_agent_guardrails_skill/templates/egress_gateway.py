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
