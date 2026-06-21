"""Unit tests for offline draft evaluation metrics."""

from __future__ import annotations

import pytest

from ticketpilot.evaluation.draft_metrics import (
    compute_citation_precision,
    compute_draft_evaluation_summary,
    compute_evidence_coverage,
    compute_human_review_trigger_correct,
)
from ticketpilot.evaluation.schemas import DraftEvaluationRow, DraftEvaluationSummary


class TestComputeCitationPrecision:
    """Tests for compute_citation_precision()."""

    def test_all_valid(self):
        row = DraftEvaluationRow(
            case_id="case-001",
            valid_citation_count=5,
            invalid_citation_count=0,
        )
        assert compute_citation_precision(row) == 1.0

    def test_some_invalid(self):
        row = DraftEvaluationRow(
            case_id="case-002",
            valid_citation_count=3,
            invalid_citation_count=2,
        )
        assert compute_citation_precision(row) == pytest.approx(0.6)

    def test_all_invalid(self):
        row = DraftEvaluationRow(
            case_id="case-003",
            valid_citation_count=0,
            invalid_citation_count=4,
        )
        assert compute_citation_precision(row) == 0.0

    def test_no_citations_returns_none(self):
        """No cited IDs should return None (not 0 or 1) to avoid misleading."""
        row = DraftEvaluationRow(
            case_id="case-004",
            valid_citation_count=0,
            invalid_citation_count=0,
        )
        assert compute_citation_precision(row) is None

    def test_single_valid(self):
        row = DraftEvaluationRow(
            case_id="case-005",
            valid_citation_count=1,
            invalid_citation_count=0,
        )
        assert compute_citation_precision(row) == 1.0


class TestComputeEvidenceCoverage:
    """Tests for compute_evidence_coverage()."""

    def test_full_coverage(self):
        row = DraftEvaluationRow(
            case_id="case-001",
            cited_evidence_count=4,
            available_evidence_count=4,
        )
        assert compute_evidence_coverage(row) == 1.0

    def test_partial_coverage(self):
        row = DraftEvaluationRow(
            case_id="case-002",
            cited_evidence_count=2,
            available_evidence_count=4,
        )
        assert compute_evidence_coverage(row) == pytest.approx(0.5)

    def test_no_coverage(self):
        row = DraftEvaluationRow(
            case_id="case-003",
            cited_evidence_count=0,
            available_evidence_count=4,
        )
        assert compute_evidence_coverage(row) == 0.0

    def test_no_available_evidence_returns_none(self):
        """No available evidence should return None (not 0) to avoid false claim."""
        row = DraftEvaluationRow(
            case_id="case-004",
            cited_evidence_count=0,
            available_evidence_count=0,
        )
        assert compute_evidence_coverage(row) is None

    def test_single_cited(self):
        row = DraftEvaluationRow(
            case_id="case-005",
            cited_evidence_count=1,
            available_evidence_count=3,
        )
        assert compute_evidence_coverage(row) == pytest.approx(1 / 3)


class TestComputeHumanReviewTriggerCorrect:
    """Tests for compute_human_review_trigger_correct()."""

    def test_both_true(self):
        row = DraftEvaluationRow(
            case_id="case-001",
            expected_human_review=True,
            actual_human_review=True,
        )
        assert compute_human_review_trigger_correct(row) is True

    def test_both_false(self):
        row = DraftEvaluationRow(
            case_id="case-002",
            expected_human_review=False,
            actual_human_review=False,
        )
        assert compute_human_review_trigger_correct(row) is True

    def test_false_positive(self):
        """Case should not trigger but pipeline forced human review."""
        row = DraftEvaluationRow(
            case_id="case-003",
            expected_human_review=False,
            actual_human_review=True,
        )
        assert compute_human_review_trigger_correct(row) is False

    def test_false_negative(self):
        """Case should trigger but pipeline did not force human review."""
        row = DraftEvaluationRow(
            case_id="case-004",
            expected_human_review=True,
            actual_human_review=False,
        )
        assert compute_human_review_trigger_correct(row) is False


class TestComputeDraftEvaluationSummary:
    """Tests for compute_draft_evaluation_summary()."""

    def _row(
        self,
        case_id: str,
        valid: int = 1,
        invalid: int = 0,
        avail: int = 1,
        unsupported: int = 0,
        forbidden: int = 0,
        guard: bool = True,
        cit_pass: bool = True,
        fallback: bool = False,
        expected_hr: bool = False,
        actual_hr: bool = False,
        confidence: float | None = 0.8,
        guard_failure_types: list[str] | None = None,
    ) -> DraftEvaluationRow:
        return DraftEvaluationRow(
            case_id=case_id,
            valid_citation_count=valid,
            invalid_citation_count=invalid,
            available_evidence_count=avail,
            cited_evidence_count=valid + invalid,
            unsupported_claim_count=unsupported,
            forbidden_promise_count=forbidden,
            guard_passed=guard,
            guard_failure_types=guard_failure_types or [],
            citation_validation_passed=cit_pass,
            safe_fallback_used=fallback,
            expected_human_review=expected_hr,
            actual_human_review=actual_hr,
            confidence=confidence,
        )

    def test_empty_rows(self):
        summary = compute_draft_evaluation_summary([])
        assert summary.total_cases == 0

    def test_single_case_all_valid(self):
        rows = [self._row("case-001")]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.total_cases == 1
        assert summary.citation_precision_avg == 1.0
        assert summary.evidence_coverage_avg == 1.0
        assert summary.unsupported_claim_rate == 0.0
        assert summary.forbidden_promise_rate == 0.0
        assert summary.citation_validation_pass_rate == 1.0
        assert summary.claim_guard_pass_rate == 1.0
        assert summary.average_confidence == 0.8

    def test_unsupported_claim_rate(self):
        rows = [
            self._row("case-001", unsupported=0),
            self._row("case-002", unsupported=1),
            self._row("case-003", unsupported=0),
            self._row("case-004", unsupported=2),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.unsupported_claim_rate == pytest.approx(0.5)

    def test_forbidden_promise_rate(self):
        rows = [
            self._row("case-001", forbidden=0),
            self._row("case-002", forbidden=1),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.forbidden_promise_rate == pytest.approx(0.5)

    def test_safe_fallback_rate(self):
        rows = [
            self._row("case-001", fallback=False),
            self._row("case-002", fallback=True),
            self._row("case-003", fallback=False),
            self._row("case-004", fallback=True),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.safe_fallback_rate == pytest.approx(0.5)

    def test_citation_precision_avg_ignores_none(self):
        """Precision None cases should be excluded from average."""
        # case-001: precision 1.0 (1/1), case-002: precision None (0/0)
        rows = [
            self._row("case-001", valid=1, invalid=0),
            self._row("case-002", valid=0, invalid=0),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.citation_precision_avg == 1.0

    def test_evidence_coverage_avg_ignores_none(self):
        """Coverage None cases should be excluded from average."""
        rows = [
            self._row("case-001", valid=1, invalid=0, avail=2),
            self._row("case-002", valid=0, invalid=0, avail=0),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.evidence_coverage_avg == 0.5

    def test_human_review_trigger_accuracy(self):
        rows = [
            self._row(
                "case-001",
                expected_hr=True,
                actual_hr=True,
                guard=False,
                cit_pass=False,
            ),
            self._row(
                "case-002",
                expected_hr=True,
                actual_hr=False,
                guard=False,
                cit_pass=False,
            ),
            self._row(
                "case-003",
                expected_hr=False,
                actual_hr=False,
                guard=True,
                cit_pass=True,
            ),
            self._row(
                "case-004",
                expected_hr=True,
                actual_hr=True,
                guard=False,
                cit_pass=False,
            ),
        ]
        summary = compute_draft_evaluation_summary(rows)
        # Trigger cases: case-001, case-002, case-004 (case-003 has no trigger)
        # case-001: correct, case-002: incorrect, case-004: correct
        # Trigger accuracy: 2/3
        assert summary.human_review_trigger_accuracy == pytest.approx(2 / 3)

    def test_human_review_trigger_accuracy_no_trigger_cases(self):
        """When no cases have trigger conditions, accuracy is None."""
        rows = [
            self._row(
                "case-001",
                expected_hr=False,
                actual_hr=False,
                guard=True,
                cit_pass=True,
            ),
            self._row(
                "case-002",
                expected_hr=False,
                actual_hr=False,
                guard=True,
                cit_pass=True,
            ),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.human_review_trigger_accuracy is None

    def test_citation_validation_pass_rate(self):
        rows = [
            self._row("case-001", cit_pass=True),
            self._row("case-002", cit_pass=False),
            self._row("case-003", cit_pass=True),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.citation_validation_pass_rate == pytest.approx(2 / 3)

    def test_claim_guard_pass_rate(self):
        rows = [
            self._row("case-001", guard=True),
            self._row("case-002", guard=False),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.claim_guard_pass_rate == pytest.approx(0.5)

    def test_average_confidence_ignores_none(self):
        rows = [
            self._row("case-001", confidence=0.9),
            self._row("case-002", confidence=None),
            self._row("case-003", confidence=0.7),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.average_confidence == pytest.approx(0.8)

    def test_average_confidence_all_none(self):
        rows = [
            self._row("case-001", confidence=None),
            self._row("case-002", confidence=None),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.average_confidence is None

    def test_deterministic_ordering(self):
        rows = [
            self._row("case-002", unsupported=1),
            self._row("case-001"),
            self._row("case-003", unsupported=1),
        ]
        summary = compute_draft_evaluation_summary(rows)
        # Ordering of cases should not affect aggregated rates
        assert summary.total_cases == 3
        assert summary.unsupported_claim_rate == pytest.approx(2 / 3)


class TestGuardFailureTypes:
    """Tests for guard_failure_types tracking and per-failure-type pass rates."""

    def test_guard_failure_types_field(self):
        """Verify guard_failure_types is present in row."""
        row = DraftEvaluationRow(
            case_id="case-001",
            guard_passed=False,
            guard_failure_types=["UNSUPPORTED_POLICY_CLAIM", "FORBIDDEN_PROMISE"],
        )
        assert row.guard_failure_types == [
            "UNSUPPORTED_POLICY_CLAIM",
            "FORBIDDEN_PROMISE",
        ]

    def test_per_failure_type_pass_rate(self):
        """Verify summary includes per-failure-type pass rates."""
        rows = [
            DraftEvaluationRow(
                case_id="case-001",
                guard_passed=False,
                guard_failure_types=["UNSUPPORTED_POLICY_CLAIM"],
            ),
            DraftEvaluationRow(
                case_id="case-002",
                guard_passed=False,
                guard_failure_types=["UNSUPPORTED_POLICY_CLAIM", "FORBIDDEN_PROMISE"],
            ),
            DraftEvaluationRow(
                case_id="case-003",
                guard_passed=True,
                guard_failure_types=[],
            ),
            DraftEvaluationRow(
                case_id="case-004",
                guard_passed=True,
                guard_failure_types=[],
            ),
        ]
        summary = compute_draft_evaluation_summary(rows)
        # UNSUPPORTED_POLICY_CLAIM: 2 failures out of 4 → pass rate = 2/4 = 0.5
        assert summary.per_failure_type_pass_rates[
            "UNSUPPORTED_POLICY_CLAIM"
        ] == pytest.approx(0.5)
        # FORBIDDEN_PROMISE: 1 failure out of 4 → pass rate = 3/4 = 0.75
        assert summary.per_failure_type_pass_rates[
            "FORBIDDEN_PROMISE"
        ] == pytest.approx(0.75)

    def test_per_failure_type_empty_when_no_failures(self):
        """Empty dict when all guard_passed=True and no failure types."""
        rows = [
            DraftEvaluationRow(case_id="case-001", guard_passed=True),
            DraftEvaluationRow(case_id="case-002", guard_passed=True),
        ]
        summary = compute_draft_evaluation_summary(rows)
        assert summary.per_failure_type_pass_rates == {}


class TestDraftEvaluationRowSerialization:
    """Tests that DraftEvaluationRow serializes to dict/JSON correctly."""

    def test_model_dump_includes_all_fields(self):
        row = DraftEvaluationRow(
            case_id="case-001",
            provider_name="fake",
            model_name="draft-v1",
            cited_evidence_count=3,
            available_evidence_count=5,
            valid_citation_count=2,
            invalid_citation_count=1,
            unsupported_claim_count=1,
            forbidden_promise_count=0,
            guard_passed=True,
            citation_validation_passed=True,
            safe_fallback_used=False,
            expected_human_review=True,
            actual_human_review=True,
            confidence=0.85,
        )
        data = row.model_dump()
        assert data["case_id"] == "case-001"
        assert data["provider_name"] == "fake"
        assert data["model_name"] == "draft-v1"
        assert data["cited_evidence_count"] == 3
        assert data["available_evidence_count"] == 5
        assert data["valid_citation_count"] == 2
        assert data["invalid_citation_count"] == 1
        assert data["unsupported_claim_count"] == 1
        assert data["forbidden_promise_count"] == 0
        assert data["guard_passed"] is True
        assert data["guard_failure_types"] == []
        assert data["citation_validation_passed"] is True
        assert data["safe_fallback_used"] is False
        assert data["expected_human_review"] is True
        assert data["actual_human_review"] is True
        assert data["confidence"] == 0.85

    def test_confidence_none_serializes(self):
        row = DraftEvaluationRow(
            case_id="case-002",
            confidence=None,
        )
        data = row.model_dump()
        assert data["confidence"] is None

    def test_json_roundtrip(self):
        row = DraftEvaluationRow(
            case_id="case-003",
            cited_evidence_count=2,
            available_evidence_count=3,
            guard_passed=False,
            citation_validation_passed=False,
            expected_human_review=True,
            actual_human_review=False,
        )
        json_str = row.model_dump_json()
        restored = DraftEvaluationRow.model_validate_json(json_str)
        assert restored.case_id == "case-003"
        assert restored.guard_passed is False
        assert restored.citation_validation_passed is False
        assert restored.expected_human_review is True
        assert restored.actual_human_review is False


class TestDraftEvaluationSummaryDefaults:
    """Tests for DraftEvaluationSummary default values."""

    def test_empty_summary_has_defaults(self):
        summary = DraftEvaluationSummary()
        assert summary.total_cases == 0
        assert summary.unsupported_claim_rate == 0.0
        assert summary.forbidden_promise_rate == 0.0
        assert summary.safe_fallback_rate == 0.0
        assert summary.citation_validation_pass_rate == 0.0
        assert summary.claim_guard_pass_rate == 0.0
        assert summary.per_failure_type_pass_rates == {}
        assert summary.citation_precision_avg is None
        assert summary.evidence_coverage_avg is None
        assert summary.human_review_trigger_accuracy is None
        assert summary.average_confidence is None
