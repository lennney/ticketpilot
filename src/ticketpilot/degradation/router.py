"""Degradation strategy router for TicketPilot.

Routes responses based on confidence level AND draft quality (dual-gate):
- HIGH (>0.8) + good quality: auto-send
- MEDIUM (0.6-0.8) + good quality: auto-send with disclaimer
- LOW (0.4-0.6): human review required
- CRITICAL (<0.4): escalate to human, no draft generated
- Any confidence + bad quality: fallback to human review
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
from ticketpilot.quality.scorer import DraftQualityResult


class ResponseStrategy(str, Enum):
    """Response strategy based on confidence tier."""

    AUTO_SEND = "auto_send"  # HIGH: auto-send
    AUTO_SEND_CAUTIOUS = "auto_send_cautious"  # MEDIUM: auto-send + disclaimer
    HUMAN_REVIEW = "human_review"  # LOW: human review before send
    HUMAN_ESCALATION = "human_escalation"  # CRITICAL: escalate to human


class DegradedResponse(BaseModel):
    """Response after degradation routing."""

    strategy: ResponseStrategy = Field(description="Chosen response strategy")
    answer: Optional[str] = Field(
        default=None, description="Draft answer (None for escalation)"
    )
    confidence: ConfidenceBreakdown = Field(description="Confidence breakdown")
    quality: Optional[DraftQualityResult] = Field(
        default=None, description="Draft quality result"
    )
    disclaimer: Optional[str] = Field(
        default=None, description="Disclaimer text if applicable"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Why escalated to human"
    )
    human_handoff_context: Optional[dict] = Field(
        default=None, description="Context for warm handoff"
    )


# Standard disclaimer for medium-confidence auto-sends
DEFAULT_DISCLAIMER = (
    "以上回答基于知识库检索，仅供参考。如需进一步帮助，请转接人工客服。"
)


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
        quality: Optional[DraftQualityResult] = None,
    ) -> DegradedResponse:
        """Route to appropriate strategy based on confidence level and draft quality.

        Args:
            confidence: ConfidenceBreakdown from ConfidenceScorer.
            draft: Optional draft answer text.
            quality: Optional DraftQualityResult from DraftQualityScorer.

        Returns:
            DegradedResponse with strategy, answer, and metadata.
        """
        # CRITICAL: always escalate
        if confidence.level == ConfidenceLevel.CRITICAL:
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

        # LOW: always human review
        if confidence.level == ConfidenceLevel.LOW:
            return DegradedResponse(
                strategy=ResponseStrategy.HUMAN_REVIEW,
                answer=draft,
                confidence=confidence,
                quality=quality,
                escalation_reason=f"低置信度 (overall={confidence.overall:.2f})，需人工审核",
            )

        # HIGH: check quality gate
        if confidence.level == ConfidenceLevel.HIGH:
            if quality is None or quality.eligible_for_auto_send:
                return DegradedResponse(
                    strategy=ResponseStrategy.AUTO_SEND,
                    answer=draft,
                    confidence=confidence,
                    quality=quality,
                )
            else:
                # High confidence but quality failed → human review
                return DegradedResponse(
                    strategy=ResponseStrategy.HUMAN_REVIEW,
                    answer=draft,
                    confidence=confidence,
                    quality=quality,
                    escalation_reason=f"置信度高但草稿质量不足 (score={quality.overall_score:.2f}, failures={quality.failures})",
                )

        # MEDIUM: check quality gate (lower threshold)
        if confidence.level == ConfidenceLevel.MEDIUM:
            if quality is None or quality.eligible_for_cautious_send:
                return DegradedResponse(
                    strategy=ResponseStrategy.AUTO_SEND_CAUTIOUS,
                    answer=draft,
                    confidence=confidence,
                    quality=quality,
                    disclaimer=DEFAULT_DISCLAIMER,
                )
            else:
                return DegradedResponse(
                    strategy=ResponseStrategy.HUMAN_REVIEW,
                    answer=draft,
                    confidence=confidence,
                    quality=quality,
                    escalation_reason=f"中置信度且草稿质量不足 (score={quality.overall_score:.2f})",
                )

        # Fallback (should never reach here)
        return DegradedResponse(
            strategy=ResponseStrategy.HUMAN_REVIEW,
            answer=draft,
            confidence=confidence,
            quality=quality,
            escalation_reason="未预期的置信度等级",
        )
