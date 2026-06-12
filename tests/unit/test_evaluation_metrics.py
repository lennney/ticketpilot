"""Unit tests for evaluation metric computation.

Tests cover:
- compute_risk_flag_metrics: precision, recall, F1, exact-match edge cases
- compute_evidence_doc_type_recall: expected docs matched, missing, empty
- compute_case_metrics: all 7 metric categories, mismatch recording
- validate_predictions: missing/extra case_id detection
- compute_evaluation_summary: aggregate metrics, failed_cases
- Determinism: repeated calls produce identical results
"""

from __future__ import annotations

import copy

import pytest

from ticketpilot.evaluation.schemas import (
    EvalPrediction,
    GoldenExpectation,
)
from ticketpilot.evaluation.metrics import (
    compute_case_metrics,
    compute_evaluation_summary,
    compute_evidence_doc_type_recall,
    compute_risk_flag_metrics,
    validate_predictions,
)


# ===================================================================
# Helpers
# ===================================================================


def _make_golden(
    case_id: str = "case_001",
    expected_issue_type: str = "refund",
    expected_risk_flags: frozenset[str] = frozenset(),
    expected_severity: str = "LOW",
    expected_must_human_review: bool = False,
    expected_evidence_doc_types: frozenset[str] = frozenset({"FAQ"}),
    expected_fallback_required: bool = False,
    expected_no_auto_send: bool = False,
) -> GoldenExpectation:
    return GoldenExpectation(
        case_id=case_id,
        expected_issue_type=expected_issue_type,
        expected_risk_flags=expected_risk_flags,
        expected_severity=expected_severity,
        expected_must_human_review=expected_must_human_review,
        expected_evidence_doc_types=expected_evidence_doc_types,
        expected_fallback_required=expected_fallback_required,
        expected_no_auto_send=expected_no_auto_send,
    )


def _make_prediction(
    case_id: str = "case_001",
    predicted_issue_type: str = "refund",
    predicted_risk_flags: frozenset[str] = frozenset(),
    predicted_severity: str = "LOW",
    predicted_must_human_review: bool = False,
    predicted_evidence_doc_types: frozenset[str] = frozenset({"FAQ"}),
    predicted_fallback_required: bool = False,
    predicted_no_auto_send: bool = False,
) -> EvalPrediction:
    return EvalPrediction(
        case_id=case_id,
        predicted_issue_type=predicted_issue_type,
        predicted_risk_flags=predicted_risk_flags,
        predicted_severity=predicted_severity,
        predicted_must_human_review=predicted_must_human_review,
        predicted_evidence_doc_types=predicted_evidence_doc_types,
        predicted_fallback_required=predicted_fallback_required,
        predicted_no_auto_send=predicted_no_auto_send,
    )


# ===================================================================
# compute_risk_flag_metrics
# ===================================================================


class TestComputeRiskFlagMetrics:
    """Tests for compute_risk_flag_metrics()."""

    def test_exact_match(self):
        """All flags match exactly."""
        flags = frozenset({"complaint_risk", "compensation_risk"})
        metrics = compute_risk_flag_metrics(flags, flags)
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0
        assert metrics.exact_match is True

    def test_missing_flag(self):
        """One expected flag missing from prediction."""
        predicted = frozenset({"complaint_risk"})
        expected = frozenset({"complaint_risk", "compensation_risk"})
        metrics = compute_risk_flag_metrics(predicted, expected)
        assert metrics.precision == 1.0  # no FP
        assert metrics.recall == 0.5  # 1/2 found
        assert metrics.f1 == pytest.approx(2.0 / 3.0)  # 2*1*0.5 / 1.5
        assert metrics.exact_match is False

    def test_extra_flag(self):
        """Extra unexpected flag in prediction."""
        predicted = frozenset({"complaint_risk", "compensation_risk", "legal_risk"})
        expected = frozenset({"complaint_risk", "compensation_risk"})
        metrics = compute_risk_flag_metrics(predicted, expected)
        assert metrics.precision == pytest.approx(2.0 / 3.0)  # 2/3 correct
        assert metrics.recall == 1.0  # all expected found
        assert metrics.f1 == pytest.approx(0.8)  # 2*(2/3)*1 / (5/3)
        assert metrics.exact_match is False

    def test_empty_both(self):
        """Both predicted and expected are empty."""
        metrics = compute_risk_flag_metrics(frozenset(), frozenset())
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0
        assert metrics.exact_match is True

    def test_empty_expected_non_empty_predicted(self):
        """No flags expected but some predicted."""
        predicted = frozenset({"complaint_risk"})
        metrics = compute_risk_flag_metrics(predicted, frozenset())
        assert metrics.precision == 0.0  # all predicted were wrong
        assert metrics.recall == 1.0  # nothing to recall
        assert metrics.f1 == 0.0
        assert metrics.exact_match is False

    def test_empty_predicted_non_empty_expected(self):
        """Flags expected but none predicted."""
        expected = frozenset({"complaint_risk"})
        metrics = compute_risk_flag_metrics(frozenset(), expected)
        assert metrics.precision == 1.0  # no FP
        assert metrics.recall == 0.0  # missed all
        assert metrics.f1 == 0.0
        assert metrics.exact_match is False

    def test_no_overlap(self):
        """Predicted and expected have no common flags."""
        predicted = frozenset({"legal_risk"})
        expected = frozenset({"complaint_risk"})
        metrics = compute_risk_flag_metrics(predicted, expected)
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1 == 0.0
        assert metrics.exact_match is False


# ===================================================================
# compute_evidence_doc_type_recall
# ===================================================================


class TestComputeEvidenceDocTypeRecall:
    """Tests for compute_evidence_doc_type_recall()."""

    def test_all_expected_matched(self):
        recall = compute_evidence_doc_type_recall(
            frozenset({"FAQ", "POLICY", "CASE"}),
            frozenset({"FAQ", "POLICY"}),
        )
        assert recall == 1.0

    def test_some_matched(self):
        recall = compute_evidence_doc_type_recall(
            frozenset({"FAQ"}),
            frozenset({"FAQ", "POLICY"}),
        )
        assert recall == 0.5

    def test_none_matched(self):
        recall = compute_evidence_doc_type_recall(
            frozenset(),
            frozenset({"FAQ", "POLICY"}),
        )
        assert recall == 0.0

    def test_empty_expected(self):
        """Empty expected doc types yields perfect recall."""
        recall = compute_evidence_doc_type_recall(
            frozenset(),
            frozenset(),
        )
        assert recall == 1.0

    def test_empty_expected_with_predicted(self):
        """Extra predicted doc types with empty expected is fine."""
        recall = compute_evidence_doc_type_recall(
            frozenset({"FAQ"}),
            frozenset(),
        )
        assert recall == 1.0


# ===================================================================
# compute_case_metrics
# ===================================================================


class TestComputeCaseMetrics:
    """Tests for compute_case_metrics()."""

    def test_perfect_prediction(self):
        """All metrics should be 1.0/True with no mismatches."""
        golden = _make_golden()
        prediction = _make_prediction()
        result = compute_case_metrics(prediction, golden)
        assert result.case_id == "case_001"
        assert result.metrics.intent_accuracy is True
        assert result.metrics.severity_accuracy is True
        assert result.metrics.must_human_review_accuracy is True
        assert result.metrics.risk_flag_metrics.precision == 1.0
        assert result.metrics.risk_flag_metrics.recall == 1.0
        assert result.metrics.risk_flag_metrics.f1 == 1.0
        assert result.metrics.risk_flag_metrics.exact_match is True
        assert result.metrics.evidence_doc_type_recall == 1.0
        assert result.metrics.fallback_correctness is True
        assert result.metrics.no_auto_send_compliance is True
        assert result.mismatches == []

    def test_wrong_issue_type(self):
        golden = _make_golden(expected_issue_type="refund")
        prediction = _make_prediction(predicted_issue_type="complaint")
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.intent_accuracy is False
        assert len(result.mismatches) == 1
        assert result.mismatches[0].metric == "intent_accuracy"
        assert result.mismatches[0].expected == "refund"
        assert result.mismatches[0].predicted == "complaint"

    def test_wrong_severity(self):
        golden = _make_golden(expected_severity="LOW")
        prediction = _make_prediction(predicted_severity="HIGH")
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.severity_accuracy is False
        assert any(m.metric == "severity_accuracy" for m in result.mismatches)

    def test_wrong_must_human_review(self):
        golden = _make_golden(expected_must_human_review=True)
        prediction = _make_prediction(predicted_must_human_review=False)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.must_human_review_accuracy is False
        assert any(m.metric == "must_human_review_accuracy" for m in result.mismatches)

    def test_risk_flag_exact_match(self):
        flags = frozenset({"complaint_risk", "compensation_risk"})
        golden = _make_golden(expected_risk_flags=flags)
        prediction = _make_prediction(predicted_risk_flags=flags)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.risk_flag_metrics.exact_match is True
        assert not any(m.metric == "risk_flags" for m in result.mismatches)

    def test_risk_flag_missing(self):
        golden = _make_golden(
            expected_risk_flags=frozenset({"complaint_risk", "compensation_risk"})
        )
        prediction = _make_prediction(
            predicted_risk_flags=frozenset({"complaint_risk"})
        )
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.risk_flag_metrics.exact_match is False
        assert result.metrics.risk_flag_metrics.recall == 0.5
        assert any(m.metric == "risk_flags" for m in result.mismatches)

    def test_risk_flag_extra(self):
        golden = _make_golden(
            expected_risk_flags=frozenset({"complaint_risk"})
        )
        prediction = _make_prediction(
            predicted_risk_flags=frozenset({"complaint_risk", "extra_risk"})
        )
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.risk_flag_metrics.exact_match is False
        assert result.metrics.risk_flag_metrics.precision < 1.0
        assert any(m.metric == "risk_flags" for m in result.mismatches)

    def test_evidence_doc_type_all_matched(self):
        golden = _make_golden(
            expected_evidence_doc_types=frozenset({"FAQ", "POLICY"})
        )
        prediction = _make_prediction(
            predicted_evidence_doc_types=frozenset({"FAQ", "POLICY", "CASE"})
        )
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.evidence_doc_type_recall == 1.0

    def test_evidence_doc_type_missing(self):
        golden = _make_golden(
            expected_evidence_doc_types=frozenset({"FAQ", "POLICY"})
        )
        prediction = _make_prediction(
            predicted_evidence_doc_types=frozenset({"FAQ"})
        )
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.evidence_doc_type_recall == 0.5
        assert any(m.metric == "evidence_doc_type_recall" for m in result.mismatches)

    def test_evidence_doc_type_empty_expected(self):
        golden = _make_golden(expected_evidence_doc_types=frozenset())
        prediction = _make_prediction(predicted_evidence_doc_types=frozenset())
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.evidence_doc_type_recall == 1.0

    def test_fallback_correctness_true(self):
        golden = _make_golden(expected_fallback_required=True)
        prediction = _make_prediction(predicted_fallback_required=True)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.fallback_correctness is True

    def test_fallback_correctness_false(self):
        golden = _make_golden(expected_fallback_required=True)
        prediction = _make_prediction(predicted_fallback_required=False)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.fallback_correctness is False
        assert any(m.metric == "fallback_correctness" for m in result.mismatches)

    def test_no_auto_send_compliance_true(self):
        golden = _make_golden(expected_no_auto_send=True)
        prediction = _make_prediction(predicted_no_auto_send=True)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.no_auto_send_compliance is True

    def test_no_auto_send_compliance_false(self):
        golden = _make_golden(expected_no_auto_send=True)
        prediction = _make_prediction(predicted_no_auto_send=False)
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.no_auto_send_compliance is False
        assert any(m.metric == "no_auto_send_compliance" for m in result.mismatches)

    def test_multiple_mismatches_recorded(self):
        """Multiple mismatches are all recorded."""
        golden = _make_golden(
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=True,
        )
        prediction = _make_prediction(
            predicted_issue_type="complaint",
            predicted_severity="HIGH",
            predicted_must_human_review=False,
        )
        result = compute_case_metrics(prediction, golden)
        assert result.metrics.intent_accuracy is False
        assert result.metrics.severity_accuracy is False
        assert result.metrics.must_human_review_accuracy is False
        mismatch_metrics = {m.metric for m in result.mismatches}
        assert "intent_accuracy" in mismatch_metrics
        assert "severity_accuracy" in mismatch_metrics
        assert "must_human_review_accuracy" in mismatch_metrics


# ===================================================================
# validate_predictions
# ===================================================================


class TestValidatePredictions:
    """Tests for validate_predictions()."""

    def test_valid_match(self):
        preds = {"case_001": _make_prediction("case_001")}
        golds = {"case_001": _make_golden("case_001")}
        errors = validate_predictions(preds, golds)
        assert errors == []

    def test_missing_prediction(self):
        preds: dict[str, EvalPrediction] = {}
        golds = {"case_001": _make_golden("case_001")}
        errors = validate_predictions(preds, golds)
        assert len(errors) == 1
        assert "Missing prediction" in errors[0]
        assert "case_001" in errors[0]

    def test_missing_golden(self):
        preds = {"case_001": _make_prediction("case_001")}
        golds: dict[str, GoldenExpectation] = {}
        errors = validate_predictions(preds, golds)
        assert len(errors) == 1
        assert "Prediction without golden" in errors[0]
        assert "case_001" in errors[0]

    def test_both_mismatches(self):
        preds = {"case_pred": _make_prediction("case_pred")}
        golds = {"case_gold": _make_golden("case_gold")}
        errors = validate_predictions(preds, golds)
        assert len(errors) == 2
        assert any("Missing prediction" in e and "case_gold" in e for e in errors)
        assert any("Prediction without golden" in e and "case_pred" in e for e in errors)

    def test_errors_in_deterministic_order(self):
        """Error messages are sorted by case_id for determinism."""
        preds = {
            "case_b": _make_prediction("case_b"),
            "case_d": _make_prediction("case_d"),
        }
        golds = {
            "case_a": _make_golden("case_a"),
            "case_c": _make_golden("case_c"),
        }
        errors = validate_predictions(preds, golds)
        # case_a is missing prediction, case_b lacks golden, case_c missing prediction, case_d lacks golden
        assert len(errors) == 4


# ===================================================================
# compute_evaluation_summary
# ===================================================================


class TestComputeEvaluationSummary:
    """Tests for compute_evaluation_summary()."""

    def test_perfect_all_cases(self):
        """All predictions match perfectly -> all aggregates 1.0."""
        golds = {
            "case_001": _make_golden("case_001"),
            "case_002": _make_golden(
                "case_002",
                expected_issue_type="complaint",
                expected_risk_flags=frozenset({"complaint_risk"}),
                expected_severity="MEDIUM",
                expected_must_human_review=True,
                expected_evidence_doc_types=frozenset({"FAQ", "POLICY"}),
                expected_fallback_required=False,
                expected_no_auto_send=True,
            ),
        }
        preds = {
            "case_001": _make_prediction("case_001"),
            "case_002": _make_prediction(
                "case_002",
                predicted_issue_type="complaint",
                predicted_risk_flags=frozenset({"complaint_risk"}),
                predicted_severity="MEDIUM",
                predicted_must_human_review=True,
                predicted_evidence_doc_types=frozenset({"FAQ", "POLICY"}),
                predicted_fallback_required=False,
                predicted_no_auto_send=True,
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.total_cases == 2
        assert summary.aggregate_intent_accuracy == 1.0
        assert summary.aggregate_severity_accuracy == 1.0
        assert summary.aggregate_must_human_review_accuracy == 1.0
        assert summary.aggregate_risk_flag_precision == 1.0
        assert summary.aggregate_risk_flag_recall == 1.0
        assert summary.aggregate_risk_flag_f1 == 1.0
        assert summary.aggregate_evidence_doc_type_recall == 1.0
        assert summary.aggregate_fallback_correctness == 1.0
        assert summary.aggregate_no_auto_send_compliance == 1.0
        assert summary.failed_cases == []

    def test_some_failures(self):
        """Mix of correct and incorrect predictions."""
        golds = {
            "case_001": _make_golden("case_001"),
            "case_002": _make_golden(
                "case_002",
                expected_issue_type="complaint",
                expected_severity="MEDIUM",
            ),
        }
        preds = {
            "case_001": _make_prediction("case_001"),
            "case_002": _make_prediction(
                "case_002",
                predicted_issue_type="refund",  # wrong
                predicted_severity="LOW",  # wrong
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.total_cases == 2
        assert summary.aggregate_intent_accuracy == 0.5
        assert summary.aggregate_severity_accuracy == 0.5
        assert len(summary.failed_cases) == 2

    def test_micro_averaged_risk_flags(self):
        """Micro-averaged risk flag metrics across cases."""
        golds = {
            "case_001": _make_golden(
                "case_001",
                expected_risk_flags=frozenset({"complaint_risk", "compensation_risk"}),
            ),
            "case_002": _make_golden(
                "case_002",
                expected_risk_flags=frozenset({"legal_risk"}),
            ),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_risk_flags=frozenset({"complaint_risk"}),
            ),
            "case_002": _make_prediction(
                "case_002",
                predicted_risk_flags=frozenset({"legal_risk", "complaint_risk"}),
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        # TP=2 (complaint_risk + legal_risk), FP=1 (extra complaint_risk in case_002), FN=1 (missing compensation_risk)
        assert summary.aggregate_risk_flag_precision == pytest.approx(2.0 / 3.0)
        assert summary.aggregate_risk_flag_recall == pytest.approx(2.0 / 3.0)
        assert summary.aggregate_risk_flag_f1 == pytest.approx(2.0 / 3.0)

    def test_empty_no_cases(self):
        """Empty predictions and golden."""
        summary = compute_evaluation_summary({}, {})
        assert summary.total_cases == 0
        assert summary.results == {}
        assert summary.failed_cases == []

    def test_failed_cases_list(self):
        """Mismatches from all cases aggregated into failed_cases."""
        golds = {
            "case_001": _make_golden("case_001", expected_issue_type="refund"),
            "case_002": _make_golden("case_002", expected_issue_type="complaint"),
        }
        preds = {
            "case_001": _make_prediction("case_001", predicted_issue_type="complaint"),
            "case_002": _make_prediction(
                "case_002", predicted_issue_type="refund"
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert len(summary.failed_cases) == 2
        assert all(f.case_id in {"case_001", "case_002"} for f in summary.failed_cases)
        assert all(f.metric == "intent_accuracy" for f in summary.failed_cases)


# ===================================================================
# Validation failures
# ===================================================================


class TestValidationFailures:
    """Tests for validation failure scenarios."""

    def test_missing_prediction_raises(self):
        golds = {"case_001": _make_golden("case_001")}
        with pytest.raises(ValueError, match="Missing prediction"):
            compute_evaluation_summary({}, golds)

    def test_prediction_without_golden_raises(self):
        preds = {"case_001": _make_prediction("case_001")}
        golds: dict[str, GoldenExpectation] = {}
        with pytest.raises(ValueError, match="Prediction without golden"):
            compute_evaluation_summary(preds, golds)


# ===================================================================
# Determinism
# ===================================================================


class TestDeterminism:
    """Metric computation is deterministic across repeated calls."""

    def test_risk_flag_metrics_deterministic(self):
        flags_a = frozenset({"compensation_risk", "complaint_risk"})
        flags_b = frozenset({"complaint_risk"})
        r1 = compute_risk_flag_metrics(flags_a, flags_b)
        r2 = compute_risk_flag_metrics(flags_a, flags_b)
        assert r1 == r2

    def test_case_metrics_deterministic(self):
        golden = _make_golden()
        prediction = _make_prediction()
        r1 = compute_case_metrics(prediction, golden)
        r2 = compute_case_metrics(prediction, golden)
        assert r1 == r2

    def test_summary_deterministic(self):
        golds = {
            "case_001": _make_golden("case_001"),
            "case_002": _make_golden(
                "case_002",
                expected_issue_type="complaint",
                expected_risk_flags=frozenset({"complaint_risk"}),
                expected_severity="MEDIUM",
            ),
        }
        preds = {
            "case_001": _make_prediction("case_001"),
            "case_002": _make_prediction(
                "case_002",
                predicted_issue_type="refund",
                predicted_severity="MEDIUM",
                predicted_risk_flags=frozenset({"complaint_risk"}),
            ),
        }
        r1 = compute_evaluation_summary(preds, golds)
        r2 = compute_evaluation_summary(preds, golds)
        assert r1 == r2

    def test_deep_copy_preserves(self):
        """Computing same inputs twice gives identical results."""
        golden = _make_golden()
        prediction = _make_prediction()
        r1 = compute_case_metrics(prediction, golden)
        # Deep copy and compute again
        golden2 = copy.deepcopy(golden)
        pred2 = copy.deepcopy(prediction)
        r2 = compute_case_metrics(pred2, golden2)
        assert r1 == r2


# ===================================================================
# Quality gate metrics
# ===================================================================


class TestQualityGateMetrics:
    """Tests for quality_gate_accuracy and quality_intercept_rate."""

    def test_quality_gate_accuracy_all_match(self):
        """All quality predictions match golden no_auto_send."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=False),
            "case_002": _make_golden("case_002", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction("case_001", predicted_no_auto_send=False),
            "case_002": _make_prediction("case_002", predicted_no_auto_send=True),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.quality_gate_accuracy == 1.0

    def test_quality_gate_accuracy_partial_match(self):
        """Some quality predictions match golden no_auto_send."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=False),
            "case_002": _make_golden("case_002", expected_no_auto_send=True),
            "case_003": _make_golden("case_003", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction("case_001", predicted_no_auto_send=False),
            "case_002": _make_prediction("case_002", predicted_no_auto_send=False),  # wrong
            "case_003": _make_prediction("case_003", predicted_no_auto_send=True),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.quality_gate_accuracy == pytest.approx(2.0 / 3.0)

    def test_quality_intercept_rate_no_interceptions(self):
        """No high-confidence cases are intercepted by quality gate."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=False),
            "case_002": _make_golden("case_002", expected_no_auto_send=False),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_must_human_review=False,
                predicted_no_auto_send=False,
            ),
            "case_002": _make_prediction(
                "case_002",
                predicted_must_human_review=False,
                predicted_no_auto_send=False,
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.quality_intercept_rate == 0.0

    def test_quality_intercept_rate_all_intercepted(self):
        """All high-confidence cases are intercepted by quality gate."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=True),
            "case_002": _make_golden("case_002", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_must_human_review=False,  # high confidence
                predicted_no_auto_send=True,  # quality blocked
            ),
            "case_002": _make_prediction(
                "case_002",
                predicted_must_human_review=False,  # high confidence
                predicted_no_auto_send=True,  # quality blocked
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.quality_intercept_rate == 1.0

    def test_quality_intercept_rate_partial(self):
        """Some high-confidence cases are intercepted."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=False),
            "case_002": _make_golden("case_002", expected_no_auto_send=True),
            "case_003": _make_golden("case_003", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_must_human_review=False,
                predicted_no_auto_send=False,
            ),
            "case_002": _make_prediction(
                "case_002",
                predicted_must_human_review=False,
                predicted_no_auto_send=True,  # intercepted
            ),
            "case_003": _make_prediction(
                "case_003",
                predicted_must_human_review=False,
                predicted_no_auto_send=True,  # intercepted
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        # 2 out of 3 high-confidence cases intercepted
        assert summary.quality_intercept_rate == pytest.approx(2.0 / 3.0)

    def test_quality_intercept_rate_excludes_low_confidence(self):
        """Low-confidence cases are not counted in intercept rate."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=True),
            "case_002": _make_golden("case_002", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_must_human_review=True,  # low confidence
                predicted_no_auto_send=True,
            ),
            "case_002": _make_prediction(
                "case_002",
                predicted_must_human_review=False,  # high confidence
                predicted_no_auto_send=True,  # intercepted
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        # Only case_002 is high confidence, and it's intercepted
        assert summary.quality_intercept_rate == 1.0

    def test_quality_intercept_rate_no_high_confidence(self):
        """No high-confidence cases yields 0.0 intercept rate."""
        golds = {
            "case_001": _make_golden("case_001", expected_no_auto_send=True),
        }
        preds = {
            "case_001": _make_prediction(
                "case_001",
                predicted_must_human_review=True,  # low confidence
                predicted_no_auto_send=True,
            ),
        }
        summary = compute_evaluation_summary(preds, golds)
        assert summary.quality_intercept_rate == 0.0

    def test_quality_metrics_empty_cases(self):
        """Empty cases yield 0.0 for both quality metrics."""
        summary = compute_evaluation_summary({}, {})
        assert summary.quality_gate_accuracy == 0.0
        assert summary.quality_intercept_rate == 0.0
