from __future__ import annotations

import uuid
from typing import Any
from ..base import BaseTool


class GenericActionTool(BaseTool):
    """
    Generalized Mutating Action Tool with explicit confirmation enforcement.
    Guards against unsolicited side-effects and prevents unconfirmed database mutations.
    """

    name = "create_system_record"
    description = (
        "Create an official system record, incident ticket, or state mutation. "
        "REQUIRES 'confirmed=True' obtained explicitly from the user turn."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short descriptive title of the action or incident",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "default": "medium",
                "description": "Severity or execution priority",
            },
            "target_id": {
                "type": "string",
                "description": "Verified target resource identifier (do NOT hallucinate)",
            },
            "confirmed": {
                "type": "boolean",
                "default": False,
                "description": "Must be True ONLY when user explicitly confirmed the final payload",
            },
        },
        "required": ["title", "target_id", "confirmed"],
    }

    def execute(
        self,
        title: str,
        target_id: str,
        confirmed: bool = False,
        priority: str = "medium",
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not confirmed:
            return {
                "status": "rejected",
                "awaiting_user": True,
                "reason": "explicit_confirmation_required",
                "question": f"Please confirm creation of record '{title}' for target '{target_id}' with priority '{priority}'.",
            }

        record_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        return {
            "status": "created",
            "record_id": record_id,
            "title": title,
            "target_id": target_id,
            "priority": priority,
            "message": f"Successfully created record {record_id}",
        }
