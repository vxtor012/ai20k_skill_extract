from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Callable, Type


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    parameters_schema: dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute tool logic and return serializable output."""
        pass

    def to_declaration(self) -> dict[str, Any]:
        """Convert tool definition to standard tool declaration schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }


class ToolRegistry:
    """Central registry managing tool declarations and execution handlers."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._functions: dict[str, Callable[..., Any]] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        self._functions[tool.name] = tool.execute

    def register_function(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
        schema: dict[str, Any] | None = None,
    ) -> None:
        self._functions[name] = func
        if schema:
            self._tools[name] = _FunctionToolAdapter(name, description, schema, func)

    def get_declarations(self) -> list[dict[str, Any]]:
        return [tool.to_declaration() for tool in self._tools.values()]

    def get_executor(self, name: str) -> Callable[..., Any] | None:
        return self._functions.get(name)

    @property
    def handlers(self) -> dict[str, Callable[..., Any]]:
        return self._functions


class _FunctionToolAdapter(BaseTool):
    def __init__(self, name: str, description: str, schema: dict[str, Any], func: Callable[..., Any]) -> None:
        self.name = name
        self.description = description
        self.parameters_schema = schema
        self._func = func

    def execute(self, **kwargs: Any) -> Any:
        return self._func(**kwargs)
