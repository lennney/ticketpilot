"""Tests for main pipeline module."""

import uuid
from datetime import datetime
from unittest.mock import patch

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    IntentClass,
    RawTicket,
    RiskFlag,
    RiskSeverity,
)


def _make_non_empty_evidence():
    """Return non-empty evidence to prevent INSUFFICIENT_EVIDENCE from being added."""
    candidates = [
        EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid.uuid4(),
            source_table="knowledge_faq",
            content="退款政策说明",
            score=0.95,
            rank=1,
        )
    ]
    trace = RetrievalTrace(query="test", query_embedding=[0.0] * 384, top_k=10)
    return candidates, trace


class TestIntakeRiskPipeline:
    """Tests for intake_risk_pipeline function."""

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_complete_processing(self, mock_retrieve):
        """Test complete pipeline processing."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="我申请退款，订单号123456",
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.ticket_id is not None
        assert result.raw_ticket == raw_ticket
        assert result.normalized_ticket is not None
        assert result.classification is not None
        assert result.risk_assessment is not None
        assert result.output_at is not None

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_with_minimal_input(self, mock_retrieve):
        """Test pipeline with minimal input."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="",
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.classification.intent == IntentClass.OTHER
        assert result.risk_assessment.flags == {RiskFlag.LOW_CONFIDENCE}

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_preserves_original(self, mock_retrieve):
        """Test pipeline preserves original input."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        original_text = "账号被盗了，有人盗刷了我的订单"
        raw_ticket = RawTicket(
            original_text=original_text,
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.raw_ticket.original_text == original_text

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_deterministic_same_input_same_output(self, mock_retrieve):
        """Test same input produces same output."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="我要投诉你们，态度太差了",
            submitted_at=datetime.utcnow(),
        )

        result1 = intake_risk_pipeline(raw_ticket)
        result2 = intake_risk_pipeline(raw_ticket)

        assert result1.classification.intent == result2.classification.intent
        assert result1.risk_assessment.severity == result2.risk_assessment.severity
        assert result1.risk_assessment.flags == result2.risk_assessment.flags

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_refund_case(self, mock_retrieve):
        """Test pipeline with refund case."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="我申请退款，订单号123456",
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.classification.intent == IntentClass.REFUND
        assert result.risk_assessment.severity == RiskSeverity.LOW

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_complaint_case(self, mock_retrieve):
        """Test pipeline with complaint case."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="我要投诉你们，态度太差了",
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.classification.intent == IntentClass.COMPLAINT
        assert RiskFlag.COMPLAINT_RISK in result.risk_assessment.flags

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_pipeline_account_security_case(self, mock_retrieve):
        """Test pipeline with account security case."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        raw_ticket = RawTicket(
            original_text="账号被盗了，有人盗刷了我的订单",
            submitted_at=datetime.utcnow(),
        )
        result = intake_risk_pipeline(raw_ticket)

        assert result.classification.intent == IntentClass.ACCOUNT_ISSUE
        assert RiskFlag.ACCOUNT_SECURITY_RISK in result.risk_assessment.flags
