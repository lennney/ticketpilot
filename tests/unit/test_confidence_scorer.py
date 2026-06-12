"""Tests for ConfidenceScorer — multi-dimensional confidence scoring."""

import uuid
from datetime import datetime


from ticketpilot.confidence.scorer import (
    ConfidenceBreakdown,
    ConfidenceLevel,
    ConfidenceScorer,
    WEIGHTS,
)
from ticketpilot.drafting.schemas import Citation, DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskSeverity,
    TicketOutput,
)


class TestConfidenceScorer:
    """Tests for ConfidenceScorer.score()."""

    def _make_ticket_output(
        self,
        intent: IntentClass = IntentClass.REFUND,
        confidence: float = 0.9,
        evidence_count: int = 3,
    ) -> TicketOutput:
        """Helper to create TicketOutput with given parameters."""
        raw = RawTicket(
            original_text="测试工单内容",
            submitted_at=datetime.utcnow(),
        )
        normalized = NormalizedTicket(
            text="测试工单内容",
            language="zh",
            order_numbers=[],
            product_info=None,
            amount=None,
            cleaned_at=datetime.utcnow(),
        )
        classification = ClassificationResult(
            intent=intent,
            confidence=confidence,
            classified_at=datetime.utcnow(),
        )
        risk = RiskAssessment(
            flags=set(),
            severity=RiskSeverity.LOW,
            must_human_review=False,
            assessed_at=datetime.utcnow(),
        )
        evidence = [
            EvidenceCandidate(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                source_id=uuid.uuid4(),
                source_table="knowledge_chunks",
                content=f"Evidence {i}",
                score=0.8 + i * 0.05,
                rank=i + 1,
            )
            for i in range(evidence_count)
        ]
        return TicketOutput(
            ticket_id=str(uuid.uuid4()),
            raw_ticket=raw,
            normalized_ticket=normalized,
            classification=classification,
            risk_assessment=risk,
            output_at=datetime.utcnow(),
            evidence_candidates=evidence,
        )

    def test_high_confidence_scenario(self):
        """High classification confidence + good evidence → HIGH."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.95, evidence_count=4)
        result = scorer.score(ticket)

        assert isinstance(result, ConfidenceBreakdown)
        assert result.classification_confidence == 0.95
        assert result.evidence_density == 1.0  # 4/3 capped at 1.0
        assert result.overall > 0.8
        assert result.level == ConfidenceLevel.HIGH

    def test_low_confidence_scenario(self):
        """Low classification + no evidence → CRITICAL."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.3, evidence_count=0)
        result = scorer.score(ticket)

        assert result.classification_confidence == 0.3
        assert result.evidence_density == 0.0
        assert result.overall < 0.4
        assert result.level == ConfidenceLevel.CRITICAL

    def test_medium_confidence_scenario(self):
        """Medium classification + some evidence → MEDIUM."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.7, evidence_count=2)
        result = scorer.score(ticket)

        assert result.level == ConfidenceLevel.MEDIUM

    def test_citation_confidence_with_draft(self):
        """Citation confidence computed from draft citations."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.8, evidence_count=2)

        draft = DraftReply(
            ticket_id=str(uuid.uuid4()),
            draft_text="测试回复[1]",
            citations=[
                Citation(
                    chunk_id=uuid.uuid4(),
                    doc_id=uuid.uuid4(),
                    doc_type=DocType.FAQ,
                    source_table="knowledge_chunks",
                    source_id=uuid.uuid4(),
                    evidence_excerpt="test",
                    claim_supported=True,
                ),
            ],
            confidence=0.8,
        )
        result = scorer.score(ticket, draft)
        assert result.citation_confidence == 1.0  # 1/1 supported

    def test_citation_confidence_no_draft(self):
        """Without draft, citation confidence defaults to 0.5."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output()
        result = scorer.score(ticket)
        assert result.citation_confidence == 0.5

    def test_citation_confidence_no_citations(self):
        """Draft with no citations → citation_confidence = 0.0."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output()
        draft = DraftReply(
            ticket_id=str(uuid.uuid4()),
            draft_text="测试回复",
            citations=[],
            confidence=0.8,
        )
        result = scorer.score(ticket, draft)
        assert result.citation_confidence == 0.0

    def test_weights_sum_to_one(self):
        """Weights should sum to 1.0."""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_overall_is_weighted_combination(self):
        """Overall score matches manual weighted calculation."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.8, evidence_count=2)
        result = scorer.score(ticket)

        expected = (
            WEIGHTS["retrieval"] * result.retrieval_confidence
            + WEIGHTS["classification"] * result.classification_confidence
            + WEIGHTS["citation"] * result.citation_confidence
            + WEIGHTS["evidence_density"] * result.evidence_density
        )
        assert abs(result.overall - round(expected, 4)) < 0.001

    def test_all_dimensions_in_range(self):
        """All dimension scores are between 0 and 1."""
        scorer = ConfidenceScorer()
        ticket = self._make_ticket_output(confidence=0.5, evidence_count=1)
        result = scorer.score(ticket)

        for dim in ["retrieval_confidence", "classification_confidence", "citation_confidence", "evidence_density", "overall"]:
            val = getattr(result, dim)
            assert 0 <= val <= 1, f"{dim} = {val} out of range"
