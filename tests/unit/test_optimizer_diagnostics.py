"""Tests for the diagnostics engine."""

from __future__ import annotations

import pytest

from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvalPrediction,
    EvaluationMetrics,
    EvaluationSummary,
    GoldenExpectation,
    RiskFlagMetrics,
)
from ticketpilot.optimizer.diagnostics import (
    DiagnosticsEngine,
    Diagnosis,
    TYPE_INTENT_MISMATCH,
    TYPE_RISK_MISS,
    TYPE_RISK_FALSE_POSITIVE,
    TYPE_EVIDENCE_GAP,
    TYPE_SEVERITY_WRONG,
    TYPE_CONFIDENCE_MISROUTE,
)


# ---------------------------------------------------------------------------
# Helper to build test objects
# ---------------------------------------------------------------------------


def _make_golden(
    case_id: str,
    expected_issue_type: str = "refund",
    expected_risk_flags: frozenset[str] = frozenset(),
    expected_severity: str = "MEDIUM",
    must_human_review: bool = False,
    evidence_doc_types: frozenset[str] = frozenset(),
    fallback_required: bool = False,
    no_auto_send: bool = True,
) -> GoldenExpectation:
    return GoldenExpectation(
        case_id=case_id,
        expected_issue_type=expected_issue_type,
        expected_risk_flags=expected_risk_flags,
        expected_severity=expected_severity,
        expected_must_human_review=must_human_review,
        expected_evidence_doc_types=evidence_doc_types,
        expected_relevant_doc_ids=frozenset(),
        expected_fallback_required=fallback_required,
        expected_no_auto_send=no_auto_send,
    )


def _make_prediction(
    case_id: str,
    predicted_issue_type: str = "refund",
    predicted_risk_flags: frozenset[str] = frozenset(),
    predicted_severity: str = "MEDIUM",
    must_human_review: bool = False,
    evidence_doc_types: frozenset[str] = frozenset(),
    fallback_required: bool = False,
    no_auto_send: bool = True,
) -> EvalPrediction:
    return EvalPrediction(
        case_id=case_id,
        predicted_issue_type=predicted_issue_type,
        predicted_risk_flags=predicted_risk_flags,
        predicted_severity=predicted_severity,
        predicted_must_human_review=must_human_review,
        predicted_evidence_doc_types=evidence_doc_types,
        predicted_fallback_required=fallback_required,
        predicted_no_auto_send=no_auto_send,
    )


def _make_metrics(
    intent_correct: bool = True,
    severity_correct: bool = True,
    human_review_correct: bool = True,
    risk_exact: bool = True,
    risk_f1: float = 1.0,
    evidence_recall: float = 1.0,
    fallback_correct: bool = True,
    auto_send_correct: bool = True,
) -> EvaluationMetrics:
    return EvaluationMetrics(
        intent_accuracy=intent_correct,
        severity_accuracy=severity_correct,
        must_human_review_accuracy=human_review_correct,
        risk_flag_metrics=RiskFlagMetrics(
            precision=1.0 if risk_exact else 0.0,
            recall=1.0 if risk_exact else 0.0,
            f1=risk_f1,
            exact_match=risk_exact,
        ),
        evidence_doc_type_recall=evidence_recall,
        fallback_correctness=fallback_correct,
        no_auto_send_compliance=auto_send_correct,
    )


def _make_case(
    case_id: str,
    expected_issue_type: str = "refund",
    predicted_issue_type: str = "refund",
    intent_correct: bool = True,
    risk_exact: bool = True,
) -> CaseResult:
    """Create a minimal CaseResult for testing."""
    golden = _make_golden(case_id, expected_issue_type=expected_issue_type)
    prediction = _make_prediction(case_id, predicted_issue_type=predicted_issue_type)
    metrics = _make_metrics(
        intent_correct=intent_correct,
        risk_exact=risk_exact,
    )
    return CaseResult(
        case_id=case_id,
        golden=golden,
        prediction=prediction,
        metrics=metrics,
    )


def _make_summary(
    total_cases: int,
    cases: dict[str, CaseResult],
    aggregate_intent_accuracy: float = 1.0,
) -> EvaluationSummary:
    """Create a minimal EvaluationSummary for testing."""
    return EvaluationSummary(
        total_cases=total_cases,
        results=cases,
        aggregate_intent_accuracy=aggregate_intent_accuracy,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiagnosisDataclass:
    """Tests for the Diagnosis dataclass."""

    def test_diagnosis_creation(self):
        d = Diagnosis(
            type=TYPE_INTENT_MISMATCH,
            priority=2,
            affected_cases=["T001"],
            expected_values={"expected_intent": "refund"},
            predicted_values={"predicted_intent": "other"},
            suggested_fix_type="intent_keyword",
            suggested_keywords=["refund"],
            fix_gain=0.15,
            description="Intent mismatch: refund -> other",
        )
        assert d.type == TYPE_INTENT_MISMATCH
        assert d.priority == 2
        assert d.affected_cases == ["T001"]
        assert d.fix_gain == 0.15


class TestComputeFixGain:
    """Tests for the _compute_fix_gain helper."""

    def test_basic_gain(self):
        from ticketpilot.optimizer.diagnostics import _compute_fix_gain

        # 3 out of 10 cases, weight 0.25 → 0.075
        assert _compute_fix_gain(3, 0.25, 10) == pytest.approx(0.075)

    def test_zero_total(self):
        from ticketpilot.optimizer.diagnostics import _compute_fix_gain

        assert _compute_fix_gain(5, 0.25, 0) == 0.0

    def test_zero_cases(self):
        from ticketpilot.optimizer.diagnostics import _compute_fix_gain

        assert _compute_fix_gain(0, 0.25, 10) == 0.0

    def test_all_cases_affected(self):
        from ticketpilot.optimizer.diagnostics import _compute_fix_gain

        assert _compute_fix_gain(10, 0.25, 10) == pytest.approx(0.25)


class TestBuildConfusionMatrix:
    """Tests for _build_confusion_matrix helper."""

    def test_no_mismatches(self):
        from ticketpilot.optimizer.diagnostics import _build_confusion_matrix

        cases = {
            "T001": _make_case("T001", "refund", "refund", intent_correct=True),
        }
        matrix = _build_confusion_matrix(cases)
        assert len(matrix) == 0

    def test_single_mismatch(self):
        from ticketpilot.optimizer.diagnostics import _build_confusion_matrix

        cases = {
            "T001": _make_case("T001", "refund", "other", intent_correct=False),
        }
        matrix = _build_confusion_matrix(cases)
        assert len(matrix) == 1
        assert ("refund", "other") in matrix
        assert matrix[("refund", "other")] == ["T001"]

    def test_grouped_mismatches(self):
        from ticketpilot.optimizer.diagnostics import _build_confusion_matrix

        cases = {
            "T001": _make_case("T001", "refund", "other", intent_correct=False),
            "T002": _make_case("T002", "refund", "other", intent_correct=False),
            "T003": _make_case(
                "T003", "technical_issue", "other", intent_correct=False
            ),
        }
        matrix = _build_confusion_matrix(cases)
        assert len(matrix) == 2
        assert matrix[("refund", "other")] == ["T001", "T002"]
        assert matrix[("technical_issue", "other")] == ["T003"]


class TestDiagnosticsEngine:
    """Tests for the DiagnosticsEngine class."""

    def test_detects_intent_mismatches(self):
        cases = {
            "T001": _make_case("T001", "refund", "other", intent_correct=False),
            "T002": _make_case("T002", "refund", "refund", intent_correct=True),
        }
        summary = _make_summary(2, cases, aggregate_intent_accuracy=0.5)
        engine = DiagnosticsEngine(weights={"intent": 0.25})
        diagnoses = engine.analyze(summary, cases)
        assert len(diagnoses) > 0
        assert any(d.type == TYPE_INTENT_MISMATCH for d in diagnoses)

    def test_diagnoses_sorted_by_gain(self):
        # Create cases: 3 refund→other mismatches, 1 technical_issue→other mismatch
        cases = {
            f"T{i:03d}": _make_case(
                f"T{i:03d}", "refund", "other", intent_correct=False
            )
            for i in range(1, 4)
        }
        cases["T004"] = _make_case(
            "T004", "technical_issue", "other", intent_correct=False
        )
        cases["T005"] = _make_case("T005", "refund", "refund", intent_correct=True)

        summary = _make_summary(5, cases, aggregate_intent_accuracy=0.2)
        engine = DiagnosticsEngine(weights={"intent": 0.25})
        diagnoses = engine.analyze(summary, cases)

        assert len(diagnoses) >= 2
        # First diagnosis should have higher fix_gain than second
        assert diagnoses[0].fix_gain >= diagnoses[1].fix_gain

    def test_no_mismatches_returns_empty(self):
        cases = {
            "T001": _make_case("T001", "refund", "refund", intent_correct=True),
            "T002": _make_case("T002", "other", "other", intent_correct=True),
        }
        summary = _make_summary(2, cases, aggregate_intent_accuracy=1.0)
        engine = DiagnosticsEngine(weights={"intent": 0.25})
        diagnoses = engine.analyze(summary, cases)
        assert len(diagnoses) == 0

    def test_risk_miss_diagnosis(self):
        golden = _make_golden(
            "T001",
            expected_risk_flags=frozenset({"complaint_risk", "legal_risk"}),
        )
        prediction = _make_prediction(
            "T001",
            predicted_risk_flags=frozenset({"complaint_risk"}),
        )
        metrics = _make_metrics(risk_exact=False, risk_f1=0.67)
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden, prediction=prediction, metrics=metrics
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(weights={"risk_f1": 0.20})
        diagnoses = engine.analyze(summary, cases)

        risk_diags = [d for d in diagnoses if d.type == TYPE_RISK_MISS]
        assert len(risk_diags) == 1
        assert "T001" in risk_diags[0].affected_cases
        assert "legal_risk" in risk_diags[0].suggested_keywords

    def test_risk_false_positive_diagnosis(self):
        golden = _make_golden(
            "T001",
            expected_risk_flags=frozenset({"complaint_risk"}),
        )
        prediction = _make_prediction(
            "T001",
            predicted_risk_flags=frozenset({"complaint_risk", "privacy_risk"}),
        )
        metrics = _make_metrics(risk_exact=False, risk_f1=0.67)
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden, prediction=prediction, metrics=metrics
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(weights={"risk_f1": 0.20})
        diagnoses = engine.analyze(summary, cases)

        fp_diags = [d for d in diagnoses if d.type == TYPE_RISK_FALSE_POSITIVE]
        # risk_false_positive disabled — removing keywords is risky by design
        assert len(fp_diags) == 0

    def test_evidence_gap_diagnosis(self):
        golden = _make_golden(
            "T001",
            evidence_doc_types=frozenset({"faq", "policy"}),
        )
        prediction = _make_prediction(
            "T001",
            evidence_doc_types=frozenset({"faq"}),
        )
        metrics = _make_metrics(evidence_recall=0.5)
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden, prediction=prediction, metrics=metrics
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(weights={"evidence": 0.15})
        diagnoses = engine.analyze(summary, cases)

        ev_diags = [d for d in diagnoses if d.type == TYPE_EVIDENCE_GAP]
        # evidence_gap disabled — no fix handler implemented (reranker_weight not supported)
        assert len(ev_diags) == 0

    def test_severity_mismatch_diagnosis(self):
        golden = _make_golden("T001", expected_severity="HIGH")
        prediction = _make_prediction("T001", predicted_severity="LOW")
        metrics = _make_metrics(severity_correct=False)
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden, prediction=prediction, metrics=metrics
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(weights={"severity": 0.20})
        diagnoses = engine.analyze(summary, cases)

        sev_diags = [d for d in diagnoses if d.type == TYPE_SEVERITY_WRONG]
        # severity_wrong disabled — severity is derived from risk flags in assessor.py;
        # fixing risk flags side-effects severity improvement
        assert len(sev_diags) == 0

    def test_confidence_misroute_diagnosis(self):
        golden = _make_golden("T001", must_human_review=False, no_auto_send=False)
        prediction = _make_prediction("T001", must_human_review=True, no_auto_send=True)
        metrics = _make_metrics(human_review_correct=False, auto_send_correct=False)
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden, prediction=prediction, metrics=metrics
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(weights={"no_auto_send": 0.10, "fallback": 0.10})
        diagnoses = engine.analyze(summary, cases)

        conf_diags = [d for d in diagnoses if d.type == TYPE_CONFIDENCE_MISROUTE]
        assert len(conf_diags) == 1
        assert "T001" in conf_diags[0].affected_cases
        assert conf_diags[0].suggested_fix_type == "confidence_threshold"

    def test_multiple_mismatch_types(self):
        """Test that all diagnosis types can appear simultaneously."""
        golden1 = _make_golden(
            "T001",
            expected_issue_type="refund",
            expected_severity="HIGH",
            expected_risk_flags=frozenset({"complaint_risk"}),
        )
        pred1 = _make_prediction(
            "T001",
            predicted_issue_type="other",
            predicted_severity="LOW",
            predicted_risk_flags=frozenset(),
        )
        metrics1 = _make_metrics(
            intent_correct=False,
            severity_correct=False,
            risk_exact=False,
            risk_f1=0.0,
        )
        cases = {
            "T001": CaseResult(
                case_id="T001", golden=golden1, prediction=pred1, metrics=metrics1
            ),
        }
        summary = _make_summary(1, cases)
        engine = DiagnosticsEngine(
            weights={
                "intent": 0.25,
                "severity": 0.20,
                "risk_f1": 0.20,
                "evidence": 0.15,
                "no_auto_send": 0.10,
                "fallback": 0.10,
            }
        )
        diagnoses = engine.analyze(summary, cases)

        types_found = {d.type for d in diagnoses}
        assert TYPE_INTENT_MISMATCH in types_found
        # severity_wrong disabled — severity is derived from risk flags
        assert TYPE_RISK_MISS in types_found

    def test_empty_results(self):
        summary = _make_summary(0, {})
        engine = DiagnosticsEngine(weights={"intent": 0.25})
        diagnoses = engine.analyze(summary, {})
        assert diagnoses == []
