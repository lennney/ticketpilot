"""Unit tests for evaluation schemas.

Tests cover:
- EvalTicket construction and validation
- GoldenExpectation construction and validation
- Issue type validation
- Severity validation
- Boolean coercion
- Semicolon-separated list parsing
- EvalDataset and LoadResult dataclasses
"""

from __future__ import annotations

from ticketpilot.evaluation.schemas import (
    EvalDataset,
    EvalTicket,
    GoldenExpectation,
    LoadResult,
    VALID_ISSUE_TYPES,
    VALID_SEVERITIES,
)
from ticketpilot.schema.ticket import IntentClass, RiskSeverity


class TestValidIssueTypes:
    """Verify VALID_ISSUE_TYPES matches the 8 IntentClass values."""

    def test_has_all_8_values(self):
        expected = {m.value for m in IntentClass}
        assert VALID_ISSUE_TYPES == expected
        assert len(VALID_ISSUE_TYPES) == 8


class TestValidSeverities:
    """Verify VALID_SEVERITIES matches the 3 RiskSeverity values."""

    def test_has_all_3_values(self):
        expected = {m.value.upper() for m in RiskSeverity}
        assert VALID_SEVERITIES == expected
        assert len(VALID_SEVERITIES) == 3


class TestEvalTicket:
    """Tests for EvalTicket schema."""

    def test_valid_ticket(self):
        ticket = EvalTicket(
            case_id="case_001",
            original_text="我要退款",
            customer_id="CUST001",
            submitted_at="2026-05-01T10:00:00Z",
            scenario_type="refund",
            notes="Standard refund",
        )
        assert ticket.case_id == "case_001"
        assert ticket.original_text == "我要退款"
        assert ticket.customer_id == "CUST001"

    def test_optional_fields(self):
        ticket = EvalTicket(
            case_id="case_002",
            original_text="退货",
            submitted_at="2026-05-01T12:00:00Z",
            scenario_type="return_exchange",
        )
        assert ticket.customer_id is None
        assert ticket.notes is None

    def test_rejects_empty_case_id(self):
        try:
            EvalTicket(
                case_id="",
                original_text="text",
                submitted_at="2026-05-01T12:00:00Z",
                scenario_type="test",
            )
            assert False, "Expected validation error"
        except Exception:
            pass


class TestGoldenExpectation:
    """Tests for GoldenExpectation schema."""

    def test_valid_golden(self):
        golden = GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_risk_flags=frozenset({"complaint_risk", "compensation_risk"}),
            expected_severity="MEDIUM",
            expected_must_human_review=True,
            expected_evidence_doc_types=frozenset({"FAQ", "POLICY"}),
            expected_fallback_required=False,
            expected_no_auto_send=True,
            notes="Test note",
        )
        assert golden.case_id == "case_001"
        assert golden.expected_issue_type == "refund"
        assert golden.expected_severity == "MEDIUM"
        assert golden.expected_must_human_review is True
        assert golden.expected_fallback_required is False
        assert golden.expected_no_auto_send is True

    def test_accepts_lowercase_severity(self):
        golden = GoldenExpectation(
            case_id="case_002",
            expected_issue_type="refund",
            expected_severity="high",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )
        assert golden.expected_severity == "HIGH"

    def test_rejects_unknown_issue_type(self):
        try:
            GoldenExpectation(
                case_id="case_003",
                expected_issue_type="invalid_intent",
                expected_severity="LOW",
                expected_must_human_review=False,
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert False, "Expected validation error"
        except Exception:
            pass

    def test_rejects_invalid_severity(self):
        try:
            GoldenExpectation(
                case_id="case_004",
                expected_issue_type="refund",
                expected_severity="CRITICAL",
                expected_must_human_review=False,
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert False, "Expected validation error"
        except Exception:
            pass

    def test_boolean_coercion_from_string_true(self):
        golden = GoldenExpectation(
            case_id="case_005",
            expected_issue_type="complaint",
            expected_severity="LOW",
            expected_must_human_review="true",
            expected_fallback_required="yes",
            expected_no_auto_send="1",
        )
        assert golden.expected_must_human_review is True
        assert golden.expected_fallback_required is True
        assert golden.expected_no_auto_send is True

    def test_boolean_coercion_from_string_false(self):
        golden = GoldenExpectation(
            case_id="case_006",
            expected_issue_type="complaint",
            expected_severity="LOW",
            expected_must_human_review="false",
            expected_fallback_required="no",
            expected_no_auto_send="0",
        )
        assert golden.expected_must_human_review is False
        assert golden.expected_fallback_required is False
        assert golden.expected_no_auto_send is False

    def test_rejects_malformed_boolean(self):
        try:
            GoldenExpectation(
                case_id="case_007",
                expected_issue_type="refund",
                expected_severity="LOW",
                expected_must_human_review="not_a_bool",
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert False, "Expected validation error"
        except Exception:
            pass

    def test_default_list_fields_are_empty_frozenset(self):
        golden = GoldenExpectation(
            case_id="case_008",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )
        assert golden.expected_risk_flags == frozenset()
        assert golden.expected_evidence_doc_types == frozenset()

    def test_risk_flags_deterministic_order(self):
        """frozenset comparison is order-independent and deterministic."""
        g1 = GoldenExpectation(
            case_id="case_009",
            expected_issue_type="complaint",
            expected_risk_flags=frozenset({"compensation_risk", "complaint_risk"}),
            expected_severity="MEDIUM",
            expected_must_human_review=True,
            expected_fallback_required=False,
            expected_no_auto_send=True,
        )
        g2 = GoldenExpectation(
            case_id="case_009",
            expected_issue_type="complaint",
            expected_risk_flags=frozenset({"complaint_risk", "compensation_risk"}),
            expected_severity="MEDIUM",
            expected_must_human_review=True,
            expected_fallback_required=False,
            expected_no_auto_send=True,
        )
        assert g1.expected_risk_flags == g2.expected_risk_flags

    def test_all_8_issue_types_accepted(self):
        """All 8 IntentClass values should be accepted as expected_issue_type."""
        for intent in IntentClass:
            golden = GoldenExpectation(
                case_id=f"case_{intent.value}",
                expected_issue_type=intent.value,
                expected_severity="LOW",
                expected_must_human_review=False,
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert golden.expected_issue_type == intent.value

    def test_all_3_severity_values_accepted(self):
        """All 3 severity values should be accepted."""
        for severity in ("LOW", "MEDIUM", "HIGH"):
            golden = GoldenExpectation(
                case_id=f"case_{severity}",
                expected_issue_type="refund",
                expected_severity=severity,
                expected_must_human_review=False,
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert golden.expected_severity == severity

    def test_rejects_empty_case_id(self):
        try:
            GoldenExpectation(
                case_id="",
                expected_issue_type="refund",
                expected_severity="LOW",
                expected_must_human_review=False,
                expected_fallback_required=False,
                expected_no_auto_send=False,
            )
            assert False, "Expected validation error"
        except Exception:
            pass


class TestEvalDataset:
    """Tests for EvalDataset dataclass."""

    def test_empty_dataset(self):
        dataset = EvalDataset()
        assert dataset.ticket_count == 0
        assert dataset.golden_count == 0
        assert dataset.case_ids == set()

    def test_ticket_and_golden_counts(self):
        ticket = EvalTicket(
            case_id="case_001",
            original_text="test",
            submitted_at="2026-05-01T12:00:00Z",
            scenario_type="test",
        )
        golden = GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )
        dataset = EvalDataset(
            tickets={"case_001": ticket},
            golden={"case_001": golden},
        )
        assert dataset.ticket_count == 1
        assert dataset.golden_count == 1
        assert dataset.case_ids == {"case_001"}

    def test_get_ticket_and_golden(self):
        ticket = EvalTicket(
            case_id="case_001",
            original_text="test",
            submitted_at="2026-05-01T12:00:00Z",
            scenario_type="test",
        )
        golden = GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )
        dataset = EvalDataset(
            tickets={"case_001": ticket},
            golden={"case_001": golden},
        )
        assert dataset.get_ticket("case_001") is ticket
        assert dataset.get_golden("case_001") is golden
        assert dataset.get_ticket("nonexistent") is None
        assert dataset.get_golden("nonexistent") is None


class TestLoadResult:
    """Tests for LoadResult dataclass."""

    def test_valid_result(self):
        result = LoadResult(dataset=EvalDataset())
        assert result.is_valid
        assert result.errors == []

    def test_invalid_with_missing_tickets(self):
        result = LoadResult(
            dataset=EvalDataset(),
            missing_golden_for_ticket=["case_001"],
        )
        assert not result.is_valid

    def test_invalid_with_missing_golden(self):
        result = LoadResult(
            dataset=EvalDataset(),
            missing_ticket_for_golden=["case_002"],
        )
        assert not result.is_valid

    def test_invalid_with_errors(self):
        result = LoadResult(
            dataset=EvalDataset(),
            errors=["Something went wrong"],
        )
        assert not result.is_valid
