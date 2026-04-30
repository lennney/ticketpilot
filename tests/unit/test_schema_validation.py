"""Tests for schema validation."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ticketpilot.schema.ticket import (
    RawTicket,
    NormalizedTicket,
    IntentClass,
    ClassificationResult,
    RiskFlag,
    RiskSeverity,
    RiskAssessment,
    TicketOutput,
)


class TestRawTicketSchema:
    """Tests for RawTicket schema validation."""

    def test_raw_ticket_valid(self):
        """Test RawTicket with valid fields passes validation."""
        ticket = RawTicket(
            original_text="测试文本",
            submitted_at=datetime.utcnow(),
            customer_id="CUST001",
        )
        assert ticket.original_text == "测试文本"
        assert ticket.customer_id == "CUST001"

    def test_raw_ticket_optional_customer_id(self):
        """Test RawTicket without customer_id defaults to None."""
        ticket = RawTicket(
            original_text="测试文本",
            submitted_at=datetime.utcnow(),
        )
        assert ticket.customer_id is None

    def test_raw_ticket_missing_required_field(self):
        """Test RawTicket with missing required field fails validation."""
        with pytest.raises(ValidationError):
            RawTicket(
                submitted_at=datetime.utcnow(),
            )


class TestNormalizedTicketSchema:
    """Tests for NormalizedTicket schema validation."""

    def test_normalized_ticket_valid(self):
        """Test NormalizedTicket with valid fields passes validation."""
        ticket = NormalizedTicket(
            text="测试文本",
            language="zh",
            order_numbers=["123456"],
            product_info=None,
            amount=None,
            cleaned_at=datetime.utcnow(),
        )
        assert ticket.text == "测试文本"
        assert ticket.order_numbers == ["123456"]

    def test_normalized_ticket_empty_order_numbers(self):
        """Test NormalizedTicket with empty order_numbers defaults to empty list."""
        ticket = NormalizedTicket(
            text="测试文本",
            language="zh",
            cleaned_at=datetime.utcnow(),
        )
        assert ticket.order_numbers == []


class TestIntentClassEnum:
    """Tests for IntentClass enum."""

    def test_all_8_values_present(self):
        """Test all 8 intent class values are available."""
        values = list(IntentClass)
        assert len(values) == 8
        assert IntentClass.REFUND in values
        assert IntentClass.RETURN_EXCHANGE in values
        assert IntentClass.ACCOUNT_ISSUE in values
        assert IntentClass.TECHNICAL_ISSUE in values
        assert IntentClass.PRODUCT_CONSULTING in values
        assert IntentClass.LOGISTICS in values
        assert IntentClass.COMPLAINT in values
        assert IntentClass.OTHER in values


class TestClassificationResultSchema:
    """Tests for ClassificationResult schema validation."""

    def test_classification_result_valid(self):
        """Test ClassificationResult with valid fields passes validation."""
        result = ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=datetime.utcnow(),
        )
        assert result.intent == IntentClass.REFUND
        assert result.confidence == 0.9


class TestRiskFlagEnum:
    """Tests for RiskFlag enum."""

    def test_all_8_values_present(self):
        """Test all 8 risk flag values are available."""
        values = list(RiskFlag)
        assert len(values) == 8
        assert RiskFlag.COMPLAINT_RISK in values
        assert RiskFlag.COMPENSATION_RISK in values
        assert RiskFlag.LEGAL_RISK in values
        assert RiskFlag.PRIVACY_RISK in values
        assert RiskFlag.ACCOUNT_SECURITY_RISK in values
        assert RiskFlag.POLICY_CONFLICT in values
        assert RiskFlag.INSUFFICIENT_EVIDENCE in values
        assert RiskFlag.LOW_CONFIDENCE in values


class TestRiskSeverityEnum:
    """Tests for RiskSeverity enum."""

    def test_all_3_values_present(self):
        """Test all 3 risk severity values are available."""
        values = list(RiskSeverity)
        assert len(values) == 3
        assert RiskSeverity.LOW in values
        assert RiskSeverity.MEDIUM in values
        assert RiskSeverity.HIGH in values


class TestRiskAssessmentSchema:
    """Tests for RiskAssessment schema validation."""

    def test_risk_assessment_valid(self):
        """Test RiskAssessment with valid fields passes validation."""
        assessment = RiskAssessment(
            flags={RiskFlag.COMPLAINT_RISK},
            severity=RiskSeverity.MEDIUM,
            must_human_review=True,
            assessed_at=datetime.utcnow(),
        )
        assert RiskFlag.COMPLAINT_RISK in assessment.flags
        assert assessment.severity == RiskSeverity.MEDIUM
        assert assessment.must_human_review is True

    def test_risk_assessment_empty_flags(self):
        """Test RiskAssessment with empty flags set."""
        assessment = RiskAssessment(
            flags=set(),
            severity=RiskSeverity.LOW,
            must_human_review=False,
            assessed_at=datetime.utcnow(),
        )
        assert len(assessment.flags) == 0
        assert assessment.must_human_review is False


class TestTicketOutputSchema:
    """Tests for TicketOutput schema validation."""

    def test_ticket_output_valid(self):
        """Test TicketOutput with all sub-schemas populated passes validation."""
        output = TicketOutput(
            ticket_id="test-123",
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
        assert output.ticket_id == "test-123"
        assert output.raw_ticket.original_text == "测试"

    def test_ticket_output_json_serialization(self):
        """Test TicketOutput serializes to JSON correctly."""
        output = TicketOutput(
            ticket_id="test-123",
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
        json_str = output.model_dump_json()
        assert "test-123" in json_str
        assert "测试" in json_str
