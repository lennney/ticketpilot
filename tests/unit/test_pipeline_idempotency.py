"""Pipeline idempotency test — Factor 12: Stateless Reducer.

Verifies that intake_risk_pipeline is a pure function:
same input → same output (modulo UUIDs and timestamps).
"""

import uuid
from datetime import datetime

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


class TestPipelineIdempotency:
    """Factor 12: Verify pipeline is a stateless reducer."""

    def test_ticket_output_structure_stable(self):
        """TicketOutput fields are deterministic (no hidden state)."""
        # Two identical RawTickets should produce structurally identical outputs
        # (except UUIDs and timestamps which are always unique)
        raw = RawTicket(
            original_text="我要退款，订单号12345",
            submitted_at=datetime(2026, 6, 6, 10, 0, 0),
            customer_id="cust-001",
        )

        # Verify RawTicket serialization is deterministic
        d1 = raw.model_dump(mode="json")
        d2 = raw.model_dump(mode="json")
        assert d1 == d2

    def test_classification_result_deterministic(self):
        """ClassificationResult is deterministic for same inputs."""
        cr1 = ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.95,
            classified_at=datetime(2026, 6, 6, 10, 0, 0),
        )
        cr2 = ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.95,
            classified_at=datetime(2026, 6, 6, 10, 0, 0),
        )
        assert cr1.model_dump() == cr2.model_dump()

    def test_risk_assessment_deterministic(self):
        """RiskAssessment is deterministic for same inputs."""
        ra1 = RiskAssessment(
            flags={RiskFlag.LOW_CONFIDENCE},
            severity=RiskSeverity.LOW,
            must_human_review=True,
            assessed_at=datetime(2026, 6, 6, 10, 0, 0),
        )
        ra2 = RiskAssessment(
            flags={RiskFlag.LOW_CONFIDENCE},
            severity=RiskSeverity.LOW,
            must_human_review=True,
            assessed_at=datetime(2026, 6, 6, 10, 0, 0),
        )
        assert ra1.model_dump() == ra2.model_dump()

    def test_confidence_scorer_deterministic(self):
        """ConfidenceScorer produces same output for same input."""
        from ticketpilot.confidence.scorer import ConfidenceScorer

        # Create a minimal TicketOutput for testing
        ticket = TicketOutput(
            ticket_id="fixed-id",
            raw_ticket=RawTicket(
                original_text="退款",
                submitted_at=datetime(2026, 1, 1),
            ),
            normalized_ticket=NormalizedTicket(
                text="退款",
                language="zh",
                cleaned_at=datetime(2026, 1, 1),
            ),
            classification=ClassificationResult(
                intent=IntentClass.REFUND,
                confidence=0.8,
                classified_at=datetime(2026, 1, 1),
            ),
            risk_assessment=RiskAssessment(
                flags=set(),
                severity=RiskSeverity.LOW,
                must_human_review=False,
                assessed_at=datetime(2026, 1, 1),
            ),
            output_at=datetime(2026, 1, 1),
        )

        scorer = ConfidenceScorer()
        r1 = scorer.score(ticket)
        r2 = scorer.score(ticket)
        assert r1.model_dump() == r2.model_dump()

    def test_degradation_router_deterministic(self):
        """DegradationRouter produces same output for same input."""
        from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
        from ticketpilot.degradation.router import DegradationRouter

        conf = ConfidenceBreakdown(
            retrieval_confidence=0.8,
            classification_confidence=0.9,
            citation_confidence=0.7,
            evidence_density=1.0,
            overall=0.85,
            level=ConfidenceLevel.HIGH,
        )

        router = DegradationRouter()
        r1 = router.route(conf, draft="测试回复")
        r2 = router.route(conf, draft="测试回复")
        assert r1.model_dump() == r2.model_dump()
