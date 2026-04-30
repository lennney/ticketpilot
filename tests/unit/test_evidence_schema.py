"""Tests for EvidenceCandidate schema and TicketOutput extension."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

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


class TestEvidenceCandidateSchema:
    """Tests for EvidenceCandidate Pydantic model validation."""

    def test_valid_candidate_constructs(self):
        """EvidenceCandidate with valid fields passes validation."""
        candidate = EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid.uuid4(),
            source_table="knowledge_faq",
            content="退款政策说明",
            score=0.95,
            rank=1,
        )
        assert candidate.content == "退款政策说明"
        assert candidate.doc_type == DocType.FAQ
        assert candidate.score == 0.95
        assert candidate.rank == 1
        assert candidate.title is None

    def test_title_is_optional_and_defaults_to_none(self):
        """EvidenceCandidate title defaults to None when not provided."""
        candidate = EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.POLICY,
            source_id=uuid.uuid4(),
            source_table="knowledge_policy",
            content="退货政策条款",
            score=0.88,
            rank=2,
        )
        assert candidate.title is None

    def test_title_can_be_set(self):
        """EvidenceCandidate title can be explicitly set."""
        candidate = EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid.uuid4(),
            source_table="knowledge_faq",
            content="如何申请退款",
            score=0.92,
            rank=1,
            title="退款FAQ第3条",
        )
        assert candidate.title == "退款FAQ第3条"

    def test_invalid_doc_type_rejected(self):
        """EvidenceCandidate rejects invalid doc_type with ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceCandidate(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type="INVALID_TYPE",
                source_id=uuid.uuid4(),
                source_table="knowledge_faq",
                content="test",
                score=0.5,
                rank=1,
            )

    def test_rank_zero_rejected(self):
        """EvidenceCandidate rejects rank=0 with ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceCandidate(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                source_id=uuid.uuid4(),
                source_table="knowledge_faq",
                content="test",
                score=0.5,
                rank=0,
            )

    def test_rank_negative_rejected(self):
        """EvidenceCandidate rejects negative rank with ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceCandidate(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                source_id=uuid.uuid4(),
                source_table="knowledge_faq",
                content="test",
                score=0.5,
                rank=-1,
            )

    def test_all_three_doc_types_accepted(self):
        """EvidenceCandidate accepts all three DocType enum values."""
        for doc_type in (DocType.FAQ, DocType.POLICY, DocType.CASE):
            candidate = EvidenceCandidate(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=doc_type,
                source_id=uuid.uuid4(),
                source_table="knowledge_faq",
                content="test",
                score=0.8,
                rank=1,
            )
            assert candidate.doc_type == doc_type

    def test_missing_required_fields_rejected(self):
        """EvidenceCandidate rejects construction when required fields are missing."""
        with pytest.raises(ValidationError):
            EvidenceCandidate(
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                content="test",
                score=0.5,
                rank=1,
            )


class TestTicketOutputExtension:
    """Tests for TicketOutput with new evidence fields."""

    def test_ticket_output_defaults_empty_evidence(self):
        """TicketOutput constructs with default empty evidence_candidates and None trace."""
        output = TicketOutput(
            ticket_id="test-456",
            raw_ticket=RawTicket(
                original_text="测试",
                submitted_at=datetime.utcnow(),
            ),
            normalized_ticket=NormalizedTicket(
                text="测试",
                language="zh",
                cleaned_at=datetime.utcnow(),
            ),
            classification=ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=0.5,
                classified_at=datetime.utcnow(),
            ),
            risk_assessment=RiskAssessment(
                flags=set(),
                severity=RiskSeverity.LOW,
                must_human_review=False,
                assessed_at=datetime.utcnow(),
            ),
            output_at=datetime.utcnow(),
        )
        assert output.evidence_candidates == []
        assert output.retrieval_trace is None

    def test_ticket_output_with_evidence_populated(self):
        """TicketOutput accepts evidence_candidates and retrieval_trace."""
        from ticketpilot.retrieval.traces import RetrievalTrace

        candidate = EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.POLICY,
            source_id=uuid.uuid4(),
            source_table="knowledge_policy",
            content="退货政策条款",
            score=0.88,
            rank=1,
        )
        trace = RetrievalTrace(query="退款")

        output = TicketOutput(
            ticket_id="test-789",
            raw_ticket=RawTicket(
                original_text="退款请求",
                submitted_at=datetime.utcnow(),
            ),
            normalized_ticket=NormalizedTicket(
                text="退款请求",
                language="zh",
                cleaned_at=datetime.utcnow(),
            ),
            classification=ClassificationResult(
                intent=IntentClass.REFUND,
                confidence=0.9,
                classified_at=datetime.utcnow(),
            ),
            risk_assessment=RiskAssessment(
                flags={RiskFlag.COMPLAINT_RISK},
                severity=RiskSeverity.MEDIUM,
                must_human_review=True,
                assessed_at=datetime.utcnow(),
            ),
            output_at=datetime.utcnow(),
            evidence_candidates=[candidate],
            retrieval_trace=trace,
        )
        assert len(output.evidence_candidates) == 1
        assert output.evidence_candidates[0].doc_type == DocType.POLICY
        assert output.retrieval_trace is not None
        assert output.retrieval_trace.query == "退款"

    def test_ticket_output_backward_compatible(self):
        """TicketOutput from existing code (no evidence fields) still works."""
        output = TicketOutput(
            ticket_id="test-000",
            raw_ticket=RawTicket(
                original_text="测试",
                submitted_at=datetime.utcnow(),
            ),
            normalized_ticket=NormalizedTicket(
                text="测试",
                language="zh",
                cleaned_at=datetime.utcnow(),
            ),
            classification=ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=0.5,
                classified_at=datetime.utcnow(),
            ),
            risk_assessment=RiskAssessment(
                flags={RiskFlag.LOW_CONFIDENCE},
                severity=RiskSeverity.LOW,
                must_human_review=True,
                assessed_at=datetime.utcnow(),
            ),
            output_at=datetime.utcnow(),
        )
        assert output.evidence_candidates == []
        assert output.retrieval_trace is None
