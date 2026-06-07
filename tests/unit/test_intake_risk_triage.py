"""Main smoke test for intake-risk-triage vertical slice."""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    IntentClass,
    RiskFlag,
    RiskSeverity,
)
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.retrieval.traces import RetrievalTrace


def _make_non_empty_evidence():
    """Return non-empty evidence to prevent INSUFFICIENT_EVIDENCE from being added.

    Golden case unit tests should not depend on live DB availability.
    Mocking retrieve_evidence isolates intent + risk assessment behavior.
    """
    from ticketpilot.retrieval.schema.knowledge import DocType

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


class TestGoldenCases:
    """Test all golden cases from the specification."""

    @patch("ticketpilot.pipeline.retrieve_evidence")
    @pytest.mark.parametrize(
        "input_text,expected_intent,expected_flags,expected_severity",
        [
            (
                "我申请退款，订单号123456",
                IntentClass.REFUND,
                set(),
                RiskSeverity.LOW,
            ),
            (
                "我要投诉你们，态度太差了",
                IntentClass.COMPLAINT,
                {RiskFlag.COMPLAINT_RISK},
                RiskSeverity.LOW,
            ),
            (
                "账号被盗了，有人盗刷了我的订单",
                IntentClass.ACCOUNT_ISSUE,
                {RiskFlag.ACCOUNT_SECURITY_RISK},
                RiskSeverity.MEDIUM,
            ),
            (
                "请联系我律师，准备起诉你们",
                IntentClass.OTHER,
                {RiskFlag.LEGAL_RISK, RiskFlag.LOW_CONFIDENCE},
                RiskSeverity.HIGH,
            ),
            (
                "我只是问一下，这个产品怎么用",
                IntentClass.PRODUCT_CONSULTING,
                set(),
                RiskSeverity.LOW,
            ),
            (
                "我要求3倍赔偿，你们违约了",
                IntentClass.OTHER,
                {RiskFlag.COMPENSATION_RISK, RiskFlag.POLICY_CONFLICT, RiskFlag.LOW_CONFIDENCE},
                RiskSeverity.MEDIUM,
            ),
            (
                "东西坏了",
                IntentClass.OTHER,
                {RiskFlag.INSUFFICIENT_EVIDENCE, RiskFlag.LOW_CONFIDENCE},
                RiskSeverity.LOW,
            ),
            (
                "",
                IntentClass.OTHER,
                {RiskFlag.LOW_CONFIDENCE},
                RiskSeverity.LOW,
            ),
        ],
    )
    def test_golden_cases(
        self, mock_retrieve, input_text, expected_intent, expected_flags, expected_severity
    ):
        """Test all golden cases must pass."""
        mock_retrieve.return_value = _make_non_empty_evidence()

        from ticketpilot.schema.ticket import RawTicket

        raw_ticket = RawTicket(
            original_text=input_text,
            submitted_at=datetime.utcnow(),
            customer_id=None,
        )

        result = intake_risk_pipeline(raw_ticket)

        assert result.classification.intent == expected_intent, (
            f"Intent mismatch: expected {expected_intent}, got {result.classification.intent}"
        )
        assert result.risk_assessment.flags == expected_flags, (
            f"Flags mismatch: expected {expected_flags}, got {result.risk_assessment.flags}"
        )
        assert result.risk_assessment.severity == expected_severity, (
            f"Severity mismatch: expected {expected_severity}, got {result.risk_assessment.severity}"
        )


class TestPipelineBasics:
    """Basic pipeline tests."""

    def test_pipeline_returns_ticket_output(self):
        """Test pipeline returns TicketOutput type."""
        from ticketpilot.schema.ticket import RawTicket

        raw_ticket = RawTicket(
            original_text="测试文本",
            submitted_at=datetime.utcnow(),
            customer_id="CUST001",
        )

        result = intake_risk_pipeline(raw_ticket)

        assert result.ticket_id is not None
        assert result.raw_ticket == raw_ticket
        assert result.output_at is not None

    def test_pipeline_preserves_original_text(self):
        """Test pipeline preserves original input text."""
        from ticketpilot.schema.ticket import RawTicket

        original_text = "我申请退款，订单号123456"
        raw_ticket = RawTicket(
            original_text=original_text,
            submitted_at=datetime.utcnow(),
        )

        result = intake_risk_pipeline(raw_ticket)

        assert result.raw_ticket.original_text == original_text

    def test_pipeline_deterministic_output(self):
        """Test same input produces same output."""
        from ticketpilot.schema.ticket import RawTicket

        raw_ticket = RawTicket(
            original_text="账号被盗了，有人盗刷了我的订单",
            submitted_at=datetime.utcnow(),
        )

        result1 = intake_risk_pipeline(raw_ticket)
        result2 = intake_risk_pipeline(raw_ticket)

        # Intent and severity should be identical
        assert result1.classification.intent == result2.classification.intent
        assert result1.risk_assessment.severity == result2.risk_assessment.severity
        assert result1.risk_assessment.flags == result2.risk_assessment.flags
