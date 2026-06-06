"""Degradation strategy router for TicketPilot.

Routes responses based on confidence level:
- HIGH (>0.8): auto-send
- MEDIUM (0.6-0.8): auto-send with disclaimer
- LOW (0.4-0.6): human review required
- CRITICAL (<0.4): escalate to human, no draft generated
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel


class ResponseStrategy(str, Enum):
    """Response strategy based on confidence tier."""
    AUTO_SEND = "auto_send"                    # HIGH: auto-send
    AUTO_SEND_CAUTIOUS = "auto_send_cautious"  # MEDIUM: auto-send + disclaimer
    HUMAN_REVIEW = "human_review"              # LOW: human review before send
    HUMAN_ESCALATION = "human_escalation"      # CRITICAL: escalate to human


class DegradedResponse(BaseModel):
    """Response after degradation routing."""

    strategy: ResponseStrategy = Field(description="Chosen response strategy")
    answer: Optional[str] = Field(default=None, description="Draft answer (None for escalation)")
    confidence: ConfidenceBreakdown = Field(description="Confidence breakdown")
    disclaimer: Optional[str] = Field(default=None, description="Disclaimer text if applicable")
    escalation_reason: Optional[str] = Field(default=None, description="Why escalated to human")
    human_handoff_context: Optional[dict] = Field(default=None, description="Context for warm handoff")


# Standard disclaimer for medium-confidence auto-sends
DEFAULT_DISCLAIMER = "以上回答基于知识库检索，仅供参考。如需进一步帮助，请转接人工客服。"


class DegradationRouter:
    """Routes responses to appropriate strategy based on confidence.

    Usage:
        router = DegradationRouter()
        result = router.route(confidence_breakdown, draft_text)
        if result.strategy == ResponseStrategy.AUTO_SEND:
            send(result.answer)
        elif result.strategy == ResponseStrategy.HUMAN_REVIEW:
            queue_for_review(result.answer, result.confidence)
    """

    def route(
        self,
        confidence: ConfidenceBreakdown,
        draft: Optional[str] = None,
    ) -> DegradedResponse:
        """Route to appropriate strategy based on confidence level.

        Args:
            confidence: ConfidenceBreakdown from ConfidenceScorer.
            draft: Optional draft answer text.

        Returns:
            DegradedResponse with strategy, answer, and metadata.
        """
        if confidence.level == ConfidenceLevel.HIGH:
            return DegradedResponse(
                strategy=ResponseStrategy.AUTO_SEND,
                answer=draft,
                confidence=confidence,
            )

        elif confidence.level == ConfidenceLevel.MEDIUM:
            return DegradedResponse(
                strategy=ResponseStrategy.AUTO_SEND_CAUTIOUS,
                answer=draft,
                confidence=confidence,
                disclaimer=DEFAULT_DISCLAIMER,
            )

        elif confidence.level == ConfidenceLevel.LOW:
            return DegradedResponse(
                strategy=ResponseStrategy.HUMAN_REVIEW,
                answer=draft,
                confidence=confidence,
                escalation_reason=f"低置信度 (overall={confidence.overall:.2f})，需人工审核",
            )

        else:  # CRITICAL
            return DegradedResponse(
                strategy=ResponseStrategy.HUMAN_ESCALATION,
                answer=None,
                confidence=confidence,
                escalation_reason=f"极低置信度 (overall={confidence.overall:.2f})，自动回复不可靠",
                human_handoff_context={
                    "confidence_breakdown": confidence.model_dump(),
                    "attempted_draft": draft,
                    "reason": "critical_confidence",
                },
            )
