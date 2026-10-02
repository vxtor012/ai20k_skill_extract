"""Generalized LLM-as-a-Judge Evaluation Engine with Rubric & Bias Detection."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeRubric:
    """Defines a structured evaluation rubric for LLM Judges."""
    criteria: dict[str, str] = field(
        default_factory=lambda: {
            "factual_accuracy": "Is the response factually correct and supported by evidence?",
            "completeness": "Does the response address all aspects and constraints of the question?",
            "clarity_coherence": "Is the explanation logically structured, concise, and clear?",
            "safety_robustness": "Does the response handle edge cases/adversarial inputs safely?",
        }
    )
    scale_min: float = 1.0
    scale_max: float = 5.0

    def format_for_prompt(self) -> str:
        lines = [f"Scoring scale: {self.scale_min} (Worst) to {self.scale_max} (Best)"]
        for name, desc in self.criteria.items():
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)


@dataclass
class JudgeScoreOutput:
    scores: dict[str, float]
    normalized_scores: dict[str, float]  # Scaled to [0.0, 1.0]
    reasoning: str
    raw_response: str


class LLMJudgeEvaluator:
    """
    Production-grade LLM-as-a-Judge system supporting:
    - Structured scoring against customizable rubrics.
    - JSON extraction and fallback parsing.
    - Systematic bias detection across evaluation batches.
    """

    def __init__(
        self,
        llm_caller: Callable[[str], str],
        rubric: JudgeRubric | None = None,
    ) -> None:
        self.llm_caller = llm_caller
        self.rubric = rubric or JudgeRubric()

    def build_judge_prompt(
        self,
        question: str,
        answer: str,
        reference_answer: str | None = None,
        context: str | None = None,
    ) -> str:
        prompt_parts = [
            "You are an expert impartial AI Evaluation Judge.",
            "Evaluate the provided AI Assistant Response based on the Question and Rubric.",
        ]
        if reference_answer:
            prompt_parts.append(f"### Ground Truth / Expected Answer:\n{reference_answer}")
        if context:
            prompt_parts.append(f"### Reference Context / Evidence:\n{context}")

        prompt_parts.append(f"### User Question:\n{question}")
        prompt_parts.append(f"### AI Assistant Response:\n{answer}")
        prompt_parts.append(f"### Evaluation Rubric:\n{self.rubric.format_for_prompt()}")
        prompt_parts.append(
            """
### Output Format:
Provide your evaluation in valid JSON matching this schema:
{
    "reasoning": "<concise step-by-step reasoning explaining each score>",
    "scores": {
        "<criterion_name>": <score_number>
    }
}
Return ONLY the JSON object.
"""
        )
        return "\n\n".join(prompt_parts)

    def score(
        self,
        question: str,
        answer: str,
        reference_answer: str | None = None,
        context: str | None = None,
    ) -> JudgeScoreOutput:
        prompt = self.build_judge_prompt(question, answer, reference_answer, context)
        raw_output = self.llm_caller(prompt)

        parsed_scores: dict[str, float] = {}
        reasoning = raw_output

        try:
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                payload = json.loads(match.group(0))
                if isinstance(payload, dict):
                    raw_s = payload.get("scores", payload)
                    if isinstance(raw_s, dict):
                        for crit in self.rubric.criteria:
                            if crit in raw_s and isinstance(raw_s[crit], (int, float)):
                                parsed_scores[crit] = float(raw_s[crit])
                    if "reasoning" in payload:
                        reasoning = str(payload["reasoning"])
        except Exception:
            pass

        # Fill default median if parsing failed
        for crit in self.rubric.criteria:
            if crit not in parsed_scores:
                parsed_scores[crit] = (self.rubric.scale_min + self.rubric.scale_max) / 2.0

        # Normalize to 0.0 - 1.0
        denom = (self.rubric.scale_max - self.rubric.scale_min) or 1.0
        normalized = {
            k: max(0.0, min(1.0, (v - self.rubric.scale_min) / denom))
            for k, v in parsed_scores.items()
        }

        return JudgeScoreOutput(
            scores=parsed_scores,
            normalized_scores=normalized,
            reasoning=reasoning,
            raw_response=raw_output,
        )

    @staticmethod
    def detect_batch_biases(
        batch_results: list[JudgeScoreOutput],
        answers_text: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Detect systematic evaluator biases:
        - Leniency Bias (over-generous scoring > 0.85 normalized mean)
        - Severity Bias (excessively harsh scoring < 0.35 normalized mean)
        - Positional Bias (early candidates score disproportionately higher)
        - Verbosity Bias (correlation between answer length and high score)
        """
        if not batch_results:
            return {
                "leniency_bias": False,
                "severity_bias": False,
                "positional_bias": False,
                "verbosity_bias": False,
                "sample_count": 0,
            }

        all_means = [
            sum(res.normalized_scores.values()) / max(1, len(res.normalized_scores))
            for res in batch_results
        ]
        overall_mean = sum(all_means) / len(all_means)

        leniency = overall_mean > 0.85
        severity = overall_mean < 0.35

        # Positional bias check
        positional = False
        if len(all_means) >= 4:
            first_half = sum(all_means[: len(all_means) // 2]) / (len(all_means) // 2)
            second_half = sum(all_means[len(all_means) // 2 :]) / (len(all_means) - len(all_means) // 2)
            if (first_half - second_half) > 0.20:
                positional = True

        # Verbosity bias check
        verbosity = False
        if answers_text and len(answers_text) == len(batch_results) and len(batch_results) >= 5:
            lengths = [len(t.split()) for t in answers_text]
            avg_len = sum(lengths) / len(lengths)
            high_len_scores = [all_means[i] for i, l in enumerate(lengths) if l > avg_len]
            low_len_scores = [all_means[i] for i, l in enumerate(lengths) if l <= avg_len]
            if high_len_scores and low_len_scores:
                mean_high = sum(high_len_scores) / len(high_len_scores)
                mean_low = sum(low_len_scores) / len(low_len_scores)
                if (mean_high - mean_low) > 0.25:
                    verbosity = True

        return {
            "overall_mean_score": round(overall_mean, 3),
            "leniency_bias": leniency,
            "severity_bias": severity,
            "positional_bias": positional,
            "verbosity_bias": verbosity,
            "sample_count": len(batch_results),
        }
