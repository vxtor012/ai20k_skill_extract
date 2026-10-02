from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Set

class DecisionAction(str, Enum):
    AUTO_EXECUTE = "AUTO_EXECUTE"
    QUEUE_REVIEW = "QUEUE_REVIEW"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"

@dataclass(frozen=True)
class HITLDecision:
    action: DecisionAction
    requires_human: bool
    priority: str
    rationale: str

class HITLConfidenceRouter:
    """Routes agent execution paths based on operational risk and confidence levels."""

    def __init__(
        self,
        high_risk_actions: Set[str],
        high_confidence_thresh: float = 0.90,
        medium_confidence_thresh: float = 0.70,
    ):
        self.high_risk_actions = high_risk_actions
        self.high_confidence_thresh = high_confidence_thresh
        self.medium_confidence_thresh = medium_confidence_thresh

    def route(self, action_name: str, confidence_score: float) -> HITLDecision:
        # Rule 1: High-risk actions unconditionally require human escalation
        if action_name in self.high_risk_actions:
            return HITLDecision(
                action=DecisionAction.ESCALATE_HUMAN,
                requires_human=True,
                priority="HIGH",
                rationale=f"Action '{action_name}' is classified as High Risk.",
            )

        # Rule 2: Low confidence requires immediate escalation
        if confidence_score < self.medium_confidence_thresh:
            return HITLDecision(
                action=DecisionAction.ESCALATE_HUMAN,
                requires_human=True,
                priority="HIGH",
                rationale=f"Confidence score {confidence_score:.2f} is below minimum threshold.",
            )

        # Rule 3: Medium confidence queued for asynchronous review
        if confidence_score < self.high_confidence_thresh:
            return HITLDecision(
                action=DecisionAction.QUEUE_REVIEW,
                requires_human=True,
                priority="NORMAL",
                rationale=f"Confidence score {confidence_score:.2f} requires supervisory validation.",
            )

        # Rule 4: High confidence auto-execution
        return HITLDecision(
            action=DecisionAction.AUTO_EXECUTE,
            requires_human=False,
            priority="LOW",
            rationale="High confidence with standard risk profile.",
        )
