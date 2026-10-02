"""
Enterprise Prompt Management, Versioning, Rollback & Fallback Resolver.
Decouples prompt engineering from application deployments with multi-tier fallback architecture.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PromptResolutionResult:
    name: str
    label: str
    version: str
    text: str
    source: str  # e.g., 'registry', 'local_cache', 'in_code_fallback'
    managed_prompt: Any = None
    fetch_error: Optional[str] = None


class PromptManager:
    """
    Manages prompt resolution, multi-tier fallback, dynamic rendering, and label promotion/rollback.
    """

    def __init__(
        self,
        default_label: str = "production",
        fallback_templates: Optional[Dict[str, str]] = None,
    ):
        self.default_label = default_label
        self.fallback_templates = fallback_templates or {}

    def resolve(
        self,
        prompt_name: str,
        variables: Dict[str, Any],
        client: Any = None,
        label: Optional[str] = None,
        version: Optional[int] = None,
        cache_ttl_seconds: int = 300,
    ) -> PromptResolutionResult:
        """
        Resolves prompt from registry with graceful degradation to local fallback template.
        """
        target_label = label or self.default_label
        resolved_text = ""
        resolved_version = "v1-fallback"
        source = "in_code_fallback"
        managed = None
        fetch_err = None

        # Tier 1: Remote Registry Resolution (e.g. Langfuse / PromptLayer / Arize)
        if client is not None and hasattr(client, "get_prompt"):
            try:
                managed = client.get_prompt(
                    prompt_name,
                    label=target_label if version is None else None,
                    version=version,
                    cache_ttl_seconds=cache_ttl_seconds,
                )
                resolved_text = managed.compile(**variables)
                resolved_version = str(getattr(managed, "version", "v_unknown"))
                source = "registry"
            except Exception as exc:
                fetch_err = f"{type(exc).__name__}: {exc}"

        # Tier 2: In-code fallback template
        if not resolved_text:
            template = self.fallback_templates.get(prompt_name, "{question}")
            try:
                # Custom safe renderer supporting {{var}} or {var}
                rendered = template
                for k, v in variables.items():
                    rendered = rendered.replace(f"{{{{{k}}}}}", str(v)).replace(f"{{{k}}}", str(v))
                resolved_text = rendered
                source = "in_code_fallback"
            except Exception as exc:
                resolved_text = str(variables.get("message", variables.get("question", "")))
                fetch_err = f"RenderError: {exc}"

        return PromptResolutionResult(
            name=prompt_name,
            label=target_label,
            version=resolved_version,
            text=resolved_text,
            source=source,
            managed_prompt=managed,
            fetch_error=fetch_err,
        )

    def promote_label(self, client: Any, prompt_name: str, version: int, target_label: str = "production") -> bool:
        """
        Promotes a specific prompt version to a target label (e.g. candidate -> production).
        """
        if not client or not hasattr(client, "update_prompt"):
            return False
        try:
            client.update_prompt(name=prompt_name, version=version, new_labels=[target_label])
            return True
        except Exception:
            return False

    def rollback_label(self, client: Any, prompt_name: str, target_version: int, current_label: str = "production") -> bool:
        """
        Rollbacks a production label to a known stable past version.
        """
        return self.promote_label(client, prompt_name=prompt_name, version=target_version, target_label=current_label)
