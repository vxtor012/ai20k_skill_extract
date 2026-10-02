from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.types import Provider, ToolCall
from .schema import CaseEvalResult, EvalCase, ExpectedToolCall, SuiteMetrics


def normalize_value(value: Any) -> Any:
    """Normalize strings and collections for resilient invariant comparison."""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return sorted(normalize_value(item) for item in value)
    if isinstance(value, dict):
        return {k: normalize_value(v) for k, v in sorted(value.items())}
    return value


def compare_argument_subset(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> tuple[bool, list[str], int, int]:
    """
    Compare expected key-value subsets against actual tool execution arguments.
    Returns: (is_match, failure_messages, matched_keys_count, total_expected_keys)
    """
    failures: list[str] = []
    total = len(expected)
    correct = 0

    for key, exp_val in expected.items():
        act_val = actual.get(key)
        if isinstance(exp_val, list) and isinstance(act_val, list):
            ok = set(normalize_value(exp_val)).issubset(set(normalize_value(act_val)))
        else:
            ok = normalize_value(act_val) == normalize_value(exp_val)

        if ok:
            correct += 1
        else:
            failures.append(f"arg '{key}': expected {exp_val!r}, received {act_val!r}")

    return len(failures) == 0, failures, correct, total


def evaluate_single_case(
    case: EvalCase,
    actual_calls: list[ToolCall],
    actual_text: str | None,
) -> CaseEvalResult:
    """Grade actual model output against deterministic expectations."""
    call_dicts = [{"name": c.name, "args": c.args} for c in actual_calls]

    # Handle No-Tool baseline cases
    if case.expect_no_tool:
        passed = len(actual_calls) == 0
        return CaseEvalResult(
            case_id=case.id,
            passed=passed,
            routing_correct=passed,
            args_correct=passed,
            observed_mismatch=None if passed else "unexpected_tool_call",
            failure_type=None if passed else str(case.failure_type),
            failures=[] if passed else ["Expected NO tool calls, but tool was triggered"],
            actual_tool_calls=call_dicts,
            actual_text=actual_text,
        )

    failures: list[str] = []
    matched_actual_indices: set[int] = set()
    routing_correct = True
    args_correct = True

    # Check each expected tool call
    for exp in case.expected_calls:
        candidates = [
            (idx, c) for idx, c in enumerate(call_dicts)
            if c["name"] == exp.name and idx not in matched_actual_indices
        ]
        if not candidates:
            failures.append(f"Missing expected tool call: {exp.name}")
            routing_correct = False
            args_correct = False
            continue

        # Find best argument match among matching tool names
        best_idx = None
        best_failures = []
        best_score = -1

        for idx, cand in candidates:
            ok, arg_fails, matched_cnt, _ = compare_argument_subset(exp.args, cand.get("args", {}))
            if ok:
                best_idx = idx
                best_failures = []
                break
            elif matched_cnt > best_score:
                best_score = matched_cnt
                best_idx = idx
                best_failures = arg_fails

        if best_failures:
            args_correct = False
            failures.extend(best_failures)

        if best_idx is not None:
            matched_actual_indices.add(best_idx)

    # Check for extra/unsolicited tool calls
    extra_count = len(actual_calls) - len(matched_actual_indices)
    if extra_count > 0:
        failures.append(f"{extra_count} extra unexpected tool call(s) executed")
        routing_correct = False

    passed = len(failures) == 0
    observed_mismatch = None
    if not passed:
        if not routing_correct:
            observed_mismatch = "wrong_tool_or_count"
        elif not args_correct:
            observed_mismatch = "wrong_argument_values"
        else:
            observed_mismatch = "general_failure"

    return CaseEvalResult(
        case_id=case.id,
        passed=passed,
        routing_correct=routing_correct,
        args_correct=args_correct,
        observed_mismatch=observed_mismatch,
        failure_type=None if passed else str(case.failure_type),
        failures=failures,
        actual_tool_calls=call_dicts,
        actual_text=actual_text,
    )


class SuiteEvaluator:
    """Benchmark suite runner that calculates aggregate metrics and failure breakdowns."""

    def __init__(self, cases: list[EvalCase]) -> None:
        self.cases = cases

    def run(
        self,
        executor_fn: Any,
    ) -> tuple[SuiteMetrics, list[CaseEvalResult]]:
        results: list[CaseEvalResult] = []
        failure_dist: dict[str, int] = {}

        routing_pass_cnt = 0
        args_pass_cnt = 0
        extra_calls_cnt = 0
        total_passed = 0

        for case in self.cases:
            actual_calls, actual_text = executor_fn(case)
            res = evaluate_single_case(case, actual_calls, actual_text)
            results.append(res)

            if res.passed:
                total_passed += 1
            else:
                ft = res.failure_type or "unknown"
                failure_dist[ft] = failure_dist.get(ft, 0) + 1

            if res.routing_correct:
                routing_pass_cnt += 1
            else:
                extra_calls_cnt += 1
            if res.args_correct:
                args_pass_cnt += 1

        total = len(self.cases)
        metrics = SuiteMetrics(
            total_cases=total,
            passed_cases=total_passed,
            pass_rate=total_passed / total if total > 0 else 0.0,
            routing_correct=routing_pass_cnt,
            routing_accuracy=routing_pass_cnt / total if total > 0 else 0.0,
            args_correct=args_pass_cnt,
            args_accuracy=args_pass_cnt / total if total > 0 else 0.0,
            extra_calls_cases=extra_calls_cnt,
            extra_calls_rate=extra_calls_cnt / total if total > 0 else 0.0,
            failure_distribution=failure_dist,
        )
        return metrics, results
