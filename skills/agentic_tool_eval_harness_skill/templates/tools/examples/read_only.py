from __future__ import annotations

from typing import Any
from ..base import BaseTool


class GenericSearchTool(BaseTool):
    """
    Generalized Read-Only Search/Query Tool.
    Demonstrates parameter schema definition, enum filtering, defensive pagination,
    and structured error handling.
    """

    name = "search_knowledge_base"
    description = (
        "Search indexed documents, technical guides, or operational records. "
        "Returns up to 'limit' relevant items matching the query."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Clean search phrase or query keywords",
            },
            "category": {
                "type": "string",
                "enum": ["all", "network", "system", "security", "billing", "policy"],
                "default": "all",
                "description": "Category domain filter",
            },
            "limit": {
                "type": "integer",
                "default": 3,
                "description": "Maximum number of results to retrieve (1-10)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, data_source: list[dict[str, Any]] | None = None) -> None:
        self.data_source = data_source or []

    def execute(self, query: str, category: str = "all", limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        limit = min(max(1, limit), 10)
        q_lower = query.lower().strip()
        matched = []

        for item in self.data_source:
            if category != "all" and item.get("category") != category:
                continue
            content = str(item.get("content", "")).lower()
            title = str(item.get("title", "")).lower()
            if q_lower in content or q_lower in title:
                matched.append(item)
            if len(matched) >= limit:
                break

        return {
            "query": query,
            "category": category,
            "total_found": len(matched),
            "results": matched,
        }
