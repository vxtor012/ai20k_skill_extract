from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .types import AgentRun, ModelResponse, Provider, ToolCall, ToolResult


class GenericToolOrchestrator:
    """
    Generalized agentic tool-calling loop.
    Handles autonomous multi-round tool execution, structured output parsing,
    human-in-the-loop clarification pausing, and defensive error containment.
    """

    def __init__(
        self,
        provider: Provider,
        *,
        system_prompt: str,
        tool_declarations: list[dict[str, Any]] | None = None,
        tool_registry: dict[str, Callable[..., Any]] | None = None,
        model: str | None = None,
        max_tool_rounds: int = 5,
        temperature: float = 0.0,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.tool_declarations = tool_declarations or []
        self.tool_registry = tool_registry or {}
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.temperature = temperature

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """Dynamically register a tool execution handler."""
        self.tool_registry[name] = func

    def execute_tool_call(self, call: ToolCall) -> ToolResult:
        """Safely execute a tool with defensive exception containment."""
        func = self.tool_registry.get(call.name)
        if not func:
            return ToolResult(
                tool=call.name,
                args=call.args,
                error=f"Unknown tool '{call.name}' - not registered in local execution registry",
            )
        try:
            result = func(**call.args)
            # Check for clarification / user pause flag
            if isinstance(result, dict) and result.get("awaiting_user"):
                return ToolResult(
                    tool=call.name,
                    args=call.args,
                    result=result,
                    is_clarification=True,
                    awaiting_user=True,
                    question=result.get("question") or call.args.get("question"),
                )
            return ToolResult(tool=call.name, args=call.args, result=result)
        except Exception as exc:
            return ToolResult(
                tool=call.name,
                args=call.args,
                error=f"{type(exc).__name__}: {str(exc)}",
            )

    def run_turn(
        self,
        conversation_history: list[dict[str, str]],
        *,
        tool_choice: Any | None = None,
    ) -> AgentRun:
        """
        Execute multi-round tool calling loop for a single conversation turn.
        Returns when the model finishes with text or pauses for clarification.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            *conversation_history,
        ]
        rounds: list[dict[str, Any]] = []
        all_tool_events: list[ToolResult] = []

        for round_idx in range(1, self.max_tool_rounds + 1):
            response: ModelResponse = self.provider.complete(
                messages,
                self.tool_declarations,
                model=self.model,
                temperature=self.temperature,
                tool_choice=tool_choice,
            )

            calls = response.tool_calls
            round_record: dict[str, Any] = {
                "round": round_idx,
                "assistant_text": response.text,
                "tool_calls": [{"name": c.name, "args": c.args} for c in calls],
                "tool_results": [],
            }

            # If model produced no tool calls, it has completed its answer
            if not calls:
                rounds.append(round_record)
                return AgentRun(
                    status="answered",
                    assistant_text=response.text or "",
                    rounds=rounds,
                    tool_events=all_tool_events,
                )

            # Record model tool call intent in message stream
            call_summary = [{"name": c.name, "args": c.args} for c in calls]
            messages.append({
                "role": "assistant",
                "content": (response.text or "Executing tool actions.")
                + f"\n\nTOOL_CALLS_JSON:\n{json.dumps(call_summary, ensure_ascii=False, indent=2)}",
            })

            round_events: list[dict[str, Any]] = []
            for call in calls:
                event = self.execute_tool_call(call)
                all_tool_events.append(event)
                event_dict = {
                    "tool": event.tool,
                    "args": event.args,
                    "result": event.result,
                    "error": event.error,
                }
                round_record["tool_results"].append(event_dict)

                if event.awaiting_user:
                    rounds.append(round_record)
                    return AgentRun(
                        status="waiting_for_user",
                        assistant_text=event.question or "Please provide the requested missing information.",
                        rounds=rounds,
                        tool_events=all_tool_events,
                    )
                round_events.append(event_dict)

            rounds.append(round_record)
            # Inject tool results back to the conversation
            messages.append({
                "role": "user",
                "content": (
                    "TOOL_RESULTS_JSON:\n"
                    f"{json.dumps(round_events, ensure_ascii=False, indent=2, default=str)}\n\n"
                    "Use only the verified tool results above to answer or determine if further actions are required."
                ),
            })

        return AgentRun(
            status="max_tool_rounds",
            assistant_text=f"Execution reached maximum limit of {self.max_tool_rounds} rounds without concluding.",
            rounds=rounds,
            tool_events=all_tool_events,
        )
