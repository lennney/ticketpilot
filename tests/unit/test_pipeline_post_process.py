"""Tests for pipeline post_process — confidence + degradation integration."""

import uuid
from datetime import datetime

import pytest

from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
from ticketpilot.degradation.router import DegradedResponse, ResponseStrategy
from ticketpilot.pipeline import post_process
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)
from ticketpilot.retrieval.schema.knowledge import DocType


class TestPostProcess:
    """Tests for pipeline.post_process()."""

    def _make_ticket_output(
        self,
        confidence: float = 0.8,
        evidence_count: int = 3,
    ) -> TicketOutput:
        """Create a TicketOutput for testing."""
        return TicketOutput(
            ticket_id=str(uuid.uuid4()),
            raw_ticket=RawTicket(
                original_text="退款申请",
                submitted_at=datetime.utcnow(),
            ),
            normalized_ticket=NormalizedTicket(
                text="退款申请",
                language="zh",
                order_numbers=[],
                product_info=None,
                amount=None,
                cleaned_at=datetime.utcnow(),
            ),
            classification=ClassificationResult(
                intent=IntentClass.REFUND,
                confidence=confidence,
                classified_at=datetime.utcnow(),
            ),
            risk_assessment=RiskAssessment(
                flags=set(),
                severity=RiskSeverity.LOW,
                must_human_review=False,
                assessed_at=datetime.utcnow(),
            ),
            output_at=datetime.utcnow(),
            evidence_candidates=[
                EvidenceCandidate(
                    chunk_id=uuid.uuid4(),
                    doc_id=uuid.uuid4(),
                    doc_type=DocType.FAQ,
                    source_id=uuid.uuid4(),
                    source_table="knowledge_chunks",
                    content=f"Evidence {i}",
                    score=0.85,
                    rank=i + 1,
                )
                for i in range(evidence_count)
            ],
        )

    def test_post_process_returns_tuple(self):
        """post_process returns (ConfidenceBreakdown, DegradedResponse)."""
        ticket = self._make_ticket_output()
        confidence, degraded = post_process(ticket)

        assert isinstance(confidence, ConfidenceBreakdown)
        assert isinstance(degraded, DegradedResponse)

    def test_post_process_high_confidence(self):
        """High classification + good evidence → AUTO_SEND."""
        ticket = self._make_ticket_output(confidence=0.95, evidence_count=4)
        confidence, degraded = post_process(ticket)

        assert confidence.level == ConfidenceLevel.HIGH
        assert degraded.strategy == ResponseStrategy.AUTO_SEND

    def test_post_process_low_confidence(self):
        """Low classification + no evidence → HUMAN_ESCALATION."""
        ticket = self._make_ticket_output(confidence=0.3, evidence_count=0)
        confidence, degraded = post_process(ticket)

        assert confidence.level == ConfidenceLevel.CRITICAL
        assert degraded.strategy == ResponseStrategy.HUMAN_ESCALATION
        assert degraded.answer is None

    def test_post_process_with_draft(self):
        """post_process works with a draft reply."""
        from ticketpilot.drafting.schemas import DraftReply

        ticket = self._make_ticket_output(confidence=0.8, evidence_count=2)
        draft = DraftReply(
            ticket_id=ticket.ticket_id,
            draft_text="根据退款政策[1]，7天内可无理由退款。",
            confidence=0.8,
        )
        confidence, degraded = post_process(ticket, draft)

        assert isinstance(confidence, ConfidenceBreakdown)
        assert degraded.answer is not None

    def test_post_process_without_draft(self):
        """post_process works without draft (confidence still computed)."""
        ticket = self._make_ticket_output(confidence=0.7, evidence_count=2)
        confidence, degraded = post_process(ticket)

        # citation_confidence defaults to 0.5 without draft
        assert confidence.citation_confidence == 0.5
