"""Tests for ticketpilot.optimizer.verifier."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch


from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvalPrediction,
    EvaluationMetrics,
    EvaluationSummary,
    GoldenExpectation,
    MismatchEntry,
    RiskFlagMetrics,
)
from ticketpilot.optimizer.config import MAX_SINGLE_METRIC_DROP
from ticketpilot.optimizer.verifier import (
    VerificationResult,
    Verifier,
    compute_composite_score,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(
    *,
    total_cases: int = 3,
    intent: float = 0.8,
    severity: float = 0.7,
    risk_f1: float = 0.6,
    evidence: float = 0.9,
    no_auto_send: float = 1.0,
    fallback: float = 0.5,
    results: dict[str, CaseResult] | None = None,
) -> EvaluationSummary:
    """Create an EvaluationSummary with controlled metric values."""
    return EvaluationSummary(
        total_cases=total_cases,
        results=results or {},
        aggregate_intent_accuracy=intent,
        aggregate_severity_accuracy=severity,
        aggregate_risk_flag_f1=risk_f1,
        aggregate_evidence_doc_type_recall=evidence,
        aggregate_no_auto_send_compliance=no_auto_send,
        aggregate_fallback_correctness=fallback,
    )


def _make_case_result(
    case_id: str,
    *,
    mismatches: list[MismatchEntry] | None = None,
) -> CaseResult:
    """Create a minimal CaseResult with controlled mismatches."""
    golden = GoldenExpectation(
        case_id=case_id,
        expected_issue_type="refund",
        expected_severity="MEDIUM",
        expected_must_human_review=False,
        expected_fallback_required=False,
        expected_no_auto_send=False,
    )
    prediction = EvalPrediction(
        case_id=case_id,
        predicted_issue_type="refund",
        predicted_severity="MEDIUM",
        predicted_must_human_review=False,
        predicted_fallback_required=False,
        predicted_no_auto_send=False,
    )
    metrics = EvaluationMetrics(
        intent_accuracy=True,
        severity_accuracy=True,
        must_human_review_accuracy=True,
        risk_flag_metrics=RiskFlagMetrics(
            precision=1.0, recall=1.0, f1=1.0, exact_match=True
        ),
        evidence_doc_type_recall=1.0,
        fallback_correctness=True,
        no_auto_send_compliance=True,
    )
    return CaseResult(
        case_id=case_id,
        golden=golden,
        prediction=prediction,
        metrics=metrics,
        mismatches=mismatches or [],
    )


def _make_mismatch(case_id: str, metric: str = "intent_accuracy") -> MismatchEntry:
    return MismatchEntry(
        case_id=case_id,
        metric=metric,
        expected="refund",
        predicted="billing",
    )


# ---------------------------------------------------------------------------
# VerificationResult basics
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_dataclass_fields(self) -> None:
        r = VerificationResult(
            passed=True,
            layer1_passed=True,
            layer2_passed=True,
            layer3_passed=True,
        )
        assert r.passed is True
        assert r.composite_delta == 0.0
        assert r.metric_deltas == {}
        assert r.regressed_cases == []
        assert r.improved_cases == []
        assert r.message == ""

    def test_failure_fields(self) -> None:
        r = VerificationResult(
            passed=False,
            layer1_passed=False,
            layer2_passed=True,
            layer3_passed=True,
            composite_delta=-0.01,
            message="Layer 1 failed",
            pytest_returncode=1,
        )
        assert r.passed is False
        assert r.pytest_returncode == 1


# ---------------------------------------------------------------------------
# compute_composite_score
# ---------------------------------------------------------------------------


class TestComputeCompositeScore:
    def test_zero_summary(self) -> None:
        summary = _make_summary(
            intent=0.0,
            severity=0.0,
            risk_f1=0.0,
            evidence=0.0,
            no_auto_send=0.0,
            fallback=0.0,
        )
        score = compute_composite_score(summary)
        assert score == 0.0

    def test_perfect_summary(self) -> None:
        summary = _make_summary(
            intent=1.0,
            severity=1.0,
            risk_f1=1.0,
            evidence=1.0,
            no_auto_send=1.0,
            fallback=1.0,
        )
        score = compute_composite_score(summary)
        # All weights sum to 1.0, so perfect = 1.0
        assert abs(score - 1.0) < 1e-6

    def test_custom_weights(self) -> None:
        summary = _make_summary(intent=1.0, severity=0.0)
        score = compute_composite_score(
            summary, weights={"intent": 0.5, "severity": 0.5}
        )
        assert abs(score - 0.5) < 1e-6

    def test_partial_scores(self) -> None:
        summary = _make_summary(
            intent=0.8,
            severity=0.6,
            risk_f1=0.7,
            evidence=0.9,
            no_auto_send=1.0,
            fallback=0.5,
        )
        score = compute_composite_score(summary)
        assert 0.0 <= score <= 1.0
        # Manually verify: 0.25*0.8 + 0.20*0.6 + 0.20*0.7 + 0.15*0.9 + 0.10*1.0 + 0.10*0.5
        # = 0.20 + 0.12 + 0.14 + 0.135 + 0.10 + 0.05 = 0.745
        assert abs(score - 0.745) < 1e-4


# ---------------------------------------------------------------------------
# Verifier: Layer 1 (mocked pytest)
# ---------------------------------------------------------------------------


class TestVerifierLayer1:
    @patch("subprocess.run")
    def test_pytest_pass(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        verifier = Verifier()
        passed, output, rc = verifier._layer1_pytest()
        assert passed is True
        assert rc == 0
        assert "OK" in output

    @patch("subprocess.run")
    def test_pytest_fail(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="FAILED", stderr="error")
        verifier = Verifier()
        passed, output, rc = verifier._layer1_pytest()
        assert passed is False
        assert rc == 1

    @patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=300),
    )
    def test_pytest_timeout(self, mock_run: MagicMock) -> None:
        verifier = Verifier()
        passed, output, rc = verifier._layer1_pytest()
        assert passed is False
        assert rc == -1
        assert "timed out" in output

    @patch("subprocess.run", side_effect=OSError("no python"))
    def test_pytest_os_error(self, mock_run: MagicMock) -> None:
        verifier = Verifier()
        passed, output, rc = verifier._layer1_pytest()
        assert passed is False
        assert rc == -1


# ---------------------------------------------------------------------------
# Verifier: Layer 2 (mocked evaluation)
# ---------------------------------------------------------------------------


class TestVerifierLayer2:
    def test_improved_composite_passes(self) -> None:
        old = _make_summary(
            intent=0.7,
            severity=0.7,
            risk_f1=0.7,
            evidence=0.7,
            no_auto_send=0.7,
            fallback=0.7,
        )
        new = _make_summary(
            intent=0.8,
            severity=0.8,
            risk_f1=0.8,
            evidence=0.8,
            no_auto_send=0.8,
            fallback=0.8,
        )
        verifier = Verifier()
        passed, sum_out, delta, deltas = verifier._layer2_evaluate(old, new_summary=new)
        assert passed is True
        assert delta > 0
        assert "composite" in deltas

    def test_worse_composite_fails(self) -> None:
        old = _make_summary(intent=0.9, severity=0.9)
        new = _make_summary(intent=0.5, severity=0.5)
        verifier = Verifier()
        passed, _, delta, _ = verifier._layer2_evaluate(old, new_summary=new)
        assert passed is False
        assert delta < 0

    def test_identical_composite_fails(self) -> None:
        old = _make_summary(intent=0.8, severity=0.8)
        new = _make_summary(intent=0.8, severity=0.8)
        verifier = Verifier()
        passed, _, delta, _ = verifier._layer2_evaluate(old, new_summary=new)
        assert passed is False
        assert delta == 0.0

    def test_no_evaluator_no_new_summary_skips(self) -> None:
        old = _make_summary()
        verifier = Verifier()
        passed, sum_out, delta, deltas = verifier._layer2_evaluate(old)
        assert passed is True  # skip = pass
        assert delta == 0.0


# ---------------------------------------------------------------------------
# Verifier: Layer 3 (safety checks)
# ---------------------------------------------------------------------------


class TestVerifierLayer3:
    def test_improvement_no_regression_passes(self) -> None:
        # T001 was wrong before, now correct → improvement
        # T002 was correct before, still correct → no regression
        case_result = _make_case_result("T002")
        old_results = {
            "T001": _make_case_result("T001", mismatches=[_make_mismatch("T001")]),
            "T002": case_result,
        }
        new_results = {
            "T001": _make_case_result("T001"),  # fixed!
            "T002": case_result,
        }
        old_summary = _make_summary(total_cases=2, results=old_results)
        new_summary = _make_summary(total_cases=2, results=new_results)
        old_correct_ids = {"T002"}

        verifier = Verifier()
        passed, regressed, improved = verifier._layer3_safety(
            old_summary, new_summary, old_correct_ids
        )
        assert passed is True
        assert "T001" in improved
        assert regressed == []

    def test_regression_fails(self) -> None:
        # T001 was correct before, now wrong → regression
        old_results = {
            "T001": _make_case_result("T001"),
            "T002": _make_case_result("T002"),
        }
        new_results = {
            "T001": _make_case_result("T001", mismatches=[_make_mismatch("T001")]),
            "T002": _make_case_result("T002"),
        }
        old_summary = _make_summary(total_cases=2, results=old_results)
        new_summary = _make_summary(total_cases=2, results=new_results)
        old_correct_ids = {"T001", "T002"}

        verifier = Verifier()
        passed, regressed, improved = verifier._layer3_safety(
            old_summary, new_summary, old_correct_ids
        )
        assert passed is False
        assert "T001" in regressed

    def test_no_improvement_fails(self) -> None:
        # No cases improved → fails MIN_CASES_FIXED check
        old_results = {
            "T001": _make_case_result("T001"),
            "T002": _make_case_result("T002"),
        }
        new_results = {
            "T001": _make_case_result("T001"),
            "T002": _make_case_result("T002"),
        }
        old_summary = _make_summary(total_cases=2, results=old_results)
        new_summary = _make_summary(total_cases=2, results=new_results)
        old_correct_ids = {"T001", "T002"}

        verifier = Verifier()
        passed, _, _ = verifier._layer3_safety(
            old_summary, new_summary, old_correct_ids
        )
        assert passed is False  # no improvement

    def test_metric_drop_exceeding_threshold_fails(self) -> None:
        old_summary = _make_summary(
            intent=0.9,
            severity=0.9,
            risk_f1=0.9,
            evidence=0.9,
            no_auto_send=0.9,
            fallback=0.9,
        )
        # Drop intent by >2%
        new_summary = _make_summary(
            intent=0.9 - MAX_SINGLE_METRIC_DROP - 0.01,
            severity=0.9,
            risk_f1=0.9,
            evidence=0.9,
            no_auto_send=0.9,
            fallback=0.9,
            results={
                "T001": _make_case_result("T001", mismatches=[_make_mismatch("T001")]),
            },
        )
        old_correct_ids = set()  # all were wrong
        # Add results to old
        old_summary.results = {"T001": _make_case_result("T001")}

        verifier = Verifier()
        passed, _, _ = verifier._layer3_safety(
            old_summary, new_summary, old_correct_ids
        )
        assert passed is False

    def test_none_new_summary_fails(self) -> None:
        old_summary = _make_summary()
        verifier = Verifier()
        passed, _, _ = verifier._layer3_safety(old_summary, None, set())
        assert passed is False


# ---------------------------------------------------------------------------
# Verifier: full integration (mocked layers)
# ---------------------------------------------------------------------------


class TestVerifierIntegration:
    @patch.object(Verifier, "_layer1_pytest", return_value=(True, "OK", 0))
    def test_all_layers_pass(self, _mock_l1: MagicMock) -> None:
        old_summary = _make_summary(
            intent=0.7,
            severity=0.7,
            risk_f1=0.7,
            evidence=0.7,
            no_auto_send=0.7,
            fallback=0.7,
        )
        new_summary = _make_summary(
            intent=0.8,
            severity=0.8,
            risk_f1=0.8,
            evidence=0.8,
            no_auto_send=0.8,
            fallback=0.8,
        )

        case_result_old = _make_case_result("T001", mismatches=[_make_mismatch("T001")])
        case_result_new = _make_case_result("T001")  # fixed
        old_summary.results = {"T001": case_result_old}
        new_summary.results = {"T001": case_result_new}
        old_summary.total_cases = 1
        new_summary.total_cases = 1

        verifier = Verifier()
        result = verifier.verify(
            old_summary,
            old_correct_ids=set(),
            new_summary=new_summary,
        )
        assert result.passed is True
        assert result.layer1_passed is True
        assert result.layer2_passed is True
        assert result.layer3_passed is True
        assert "PASSED" in result.message

    @patch.object(Verifier, "_layer1_pytest", return_value=(False, "FAIL", 1))
    def test_layer1_failure_cascades(self, _mock_l1: MagicMock) -> None:
        old = _make_summary()
        new = _make_summary(
            intent=0.8,
            severity=0.8,
            risk_f1=0.8,
            evidence=0.8,
            no_auto_send=0.8,
            fallback=0.8,
        )
        case_old = _make_case_result("T001", mismatches=[_make_mismatch("T001")])
        case_new = _make_case_result("T001")
        old.results = {"T001": case_old}
        new.results = {"T001": case_new}
        old.total_cases = 1
        new.total_cases = 1

        verifier = Verifier()
        result = verifier.verify(old, old_correct_ids=set(), new_summary=new)
        assert result.passed is False
        assert result.layer1_passed is False
        assert "Layer 1 FAILED" in result.message
