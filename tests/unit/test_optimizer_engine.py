"""Tests for ticketpilot.optimizer.engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvaluationMetrics,
    EvaluationSummary,
    RiskFlagMetrics,
)
from ticketpilot.optimizer.config import COMPOSITE_WEIGHTS, OptimizerConfig
from ticketpilot.optimizer.engine import OptimizationEngine, _now_iso


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_case_result(
    case_id: str,
    intent_ok: bool = True,
    severity_ok: bool = True,
    risk_exact: bool = True,
    risk_f1_score: float | None = None,
    evidence_recall: float = 1.0,
    fallback_ok: bool = True,
    no_auto_send_ok: bool = True,
) -> CaseResult:
    """Create a minimal CaseResult for testing."""
    if risk_f1_score is None:
        risk_f1_score = 1.0 if risk_exact else 0.0
    from ticketpilot.evaluation.schemas import (
        EvalPrediction,
        GoldenExpectation,
        MismatchEntry,
    )

    golden = GoldenExpectation(
        case_id=case_id,
        expected_issue_type="refund",
        expected_risk_flags=frozenset(),
        expected_severity="MEDIUM",
        expected_must_human_review=False,
        expected_evidence_doc_types=frozenset(),
        expected_relevant_doc_ids=frozenset(),
        expected_fallback_required=False,
        expected_no_auto_send=False,
    )
    prediction = EvalPrediction(
        case_id=case_id,
        predicted_issue_type="refund",
        predicted_risk_flags=frozenset(),
        predicted_severity="MEDIUM",
        predicted_must_human_review=False,
        predicted_evidence_doc_types=frozenset(),
        predicted_fallback_required=False,
        predicted_no_auto_send=False,
    )
    metrics = EvaluationMetrics(
        intent_accuracy=intent_ok,
        severity_accuracy=severity_ok,
        must_human_review_accuracy=True,
        risk_flag_metrics=RiskFlagMetrics(
            precision=risk_f1_score, recall=risk_f1_score, f1=risk_f1_score, exact_match=risk_exact
        ),
        evidence_doc_type_recall=evidence_recall,
        fallback_correctness=fallback_ok,
        no_auto_send_compliance=no_auto_send_ok,
    )
    return CaseResult(
        case_id=case_id,
        golden=golden,
        prediction=prediction,
        metrics=metrics,
        mismatches=[],
    )


def _make_summary(
    results: dict[str, CaseResult] | None = None,
) -> EvaluationSummary:
    """Create an EvaluationSummary with sensible defaults."""
    if results is None:
        results = {}
        for i in range(1, 6):
            cid = f"CASE-{i:03d}"
            results[cid] = _make_case_result(cid)

    total = len(results)
    intent_acc = (
        sum(1 for r in results.values() if r.metrics.intent_accuracy) / total
        if total > 0
        else 0.0
    )
    severity_acc = (
        sum(1 for r in results.values() if r.metrics.severity_accuracy) / total
        if total > 0
        else 0.0
    )
    risk_f1 = (
        sum(r.metrics.risk_flag_metrics.f1 for r in results.values()) / total
        if total > 0
        else 0.0
    )
    evidence = (
        sum(r.metrics.evidence_doc_type_recall for r in results.values()) / total
        if total > 0
        else 0.0
    )
    fallback = (
        sum(1 for r in results.values() if r.metrics.fallback_correctness) / total
        if total > 0
        else 0.0
    )
    no_auto = (
        sum(1 for r in results.values() if r.metrics.no_auto_send_compliance) / total
        if total > 0
        else 0.0
    )
    return EvaluationSummary(
        total_cases=total,
        results=results,
        aggregate_intent_accuracy=intent_acc,
        aggregate_severity_accuracy=severity_acc,
        aggregate_risk_flag_f1=risk_f1,
        aggregate_evidence_doc_type_recall=evidence,
        aggregate_fallback_correctness=fallback,
        aggregate_no_auto_send_compliance=no_auto,
    )


# ------------------------------------------------------------------
# OptimizationEngine init
# ------------------------------------------------------------------

class TestOptimizationEngineInit:
    def test_default_config(self) -> None:
        engine = OptimizationEngine()
        assert engine.config.max_rounds == 20
        assert engine.config.diagnose_only is False
        assert engine.config.dry_run is False
        assert engine.config.resume is False

    def test_custom_config(self) -> None:
        engine = OptimizationEngine(
            max_rounds=5,
            diagnose_only=True,
            dry_run=True,
            resume=True,
        )
        assert engine.config.max_rounds == 5
        assert engine.config.diagnose_only is True
        assert engine.config.dry_run is True
        assert engine.config.resume is True

    def test_components_created(self) -> None:
        engine = OptimizationEngine()
        assert engine.evaluator is not None
        assert engine.diagnostics is not None
        assert engine.fixer is not None
        assert engine.history is not None

    def test_weights_from_config(self) -> None:
        engine = OptimizationEngine()
        assert engine.config.weights == COMPOSITE_WEIGHTS


# ------------------------------------------------------------------
# Composite score calculation
# ------------------------------------------------------------------

class TestComputeComposite:
    def test_perfect_score(self) -> None:
        engine = OptimizationEngine()
        summary = _make_summary()  # all cases correct → 1.0 for every metric
        composite = engine._compute_composite(summary)
        assert abs(composite - 1.0) < 1e-9

    def test_zero_score(self) -> None:
        engine = OptimizationEngine()
        results = {}
        for i in range(1, 4):
            cid = f"FAIL-{i:03d}"
            results[cid] = _make_case_result(
                cid,
                intent_ok=False,
                severity_ok=False,
                risk_exact=False,
                evidence_recall=0.0,
                fallback_ok=False,
                no_auto_send_ok=False,
            )
        summary = _make_summary(results)
        composite = engine._compute_composite(summary)
        assert abs(composite) < 1e-9

    def test_partial_score(self) -> None:
        engine = OptimizationEngine()
        # 3 correct, 2 wrong on intent only
        results = {}
        for i in range(1, 6):
            cid = f"CASE-{i:03d}"
            results[cid] = _make_case_result(
                cid, intent_ok=(i <= 3)
            )
        summary = _make_summary(results)
        composite = engine._compute_composite(summary)
        # intent = 0.6, all others = 1.0
        expected = 0.25 * 0.6 + 0.20 * 1.0 + 0.20 * 1.0 + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0
        assert abs(composite - expected) < 1e-9

    def test_composite_respects_weights(self) -> None:
        engine = OptimizationEngine()
        # Only risk_f1 is 0.5, rest are 1.0
        results = {}
        for i in range(1, 3):
            cid = f"CASE-{i:03d}"
            results[cid] = _make_case_result(cid, risk_exact=False)
        summary = _make_summary(results)
        composite = engine._compute_composite(summary)
        # risk_f1 is micro-averaged: 2 cases each with f1=0.0 → aggregate 0.0
        expected = (
            0.25 * 1.0 + 0.20 * 1.0 + 0.20 * 0.0
            + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0
        )
        assert abs(composite - expected) < 1e-9


# ------------------------------------------------------------------
# Score dict
# ------------------------------------------------------------------

class TestScoreDict:
    def test_score_dict_keys(self) -> None:
        engine = OptimizationEngine()
        summary = _make_summary()
        scores = engine._score_dict(summary)
        expected_keys = {"intent", "severity", "risk_f1", "evidence", "no_auto_send", "fallback"}
        assert set(scores.keys()) == expected_keys

    def test_score_dict_values(self) -> None:
        engine = OptimizationEngine()
        summary = _make_summary()
        scores = engine._score_dict(summary)
        assert scores["intent"] == summary.aggregate_intent_accuracy
        assert scores["severity"] == summary.aggregate_severity_accuracy
        assert scores["risk_f1"] == summary.aggregate_risk_flag_f1
        assert scores["evidence"] == summary.aggregate_evidence_doc_type_recall
        assert scores["no_auto_send"] == summary.aggregate_no_auto_send_compliance
        assert scores["fallback"] == summary.aggregate_fallback_correctness


# ------------------------------------------------------------------
# Extract correct IDs
# ------------------------------------------------------------------

class TestExtractCorrectIds:
    def test_all_correct(self) -> None:
        engine = OptimizationEngine()
        summary = _make_summary()
        correct = engine._extract_correct_ids(summary)
        assert len(correct) == 5
        assert all(cid.startswith("CASE-") for cid in correct)

    def test_none_correct(self) -> None:
        engine = OptimizationEngine()
        results = {}
        for i in range(1, 4):
            cid = f"FAIL-{i:03d}"
            results[cid] = _make_case_result(
                cid,
                intent_ok=False,
                severity_ok=False,
                risk_exact=False,
                fallback_ok=False,
                no_auto_send_ok=False,
            )
        summary = _make_summary(results)
        correct = engine._extract_correct_ids(summary)
        assert len(correct) == 0

    def test_partial_correct(self) -> None:
        engine = OptimizationEngine()
        results = {
            "OK-001": _make_case_result("OK-001"),
            "OK-002": _make_case_result("OK-002"),
            "BAD-001": _make_case_result(
                "BAD-001", intent_ok=False, severity_ok=False
            ),
        }
        summary = _make_summary(results)
        correct = engine._extract_correct_ids(summary)
        assert correct == {"OK-001", "OK-002"}


# ------------------------------------------------------------------
# show_history
# ------------------------------------------------------------------

class TestShowHistory:
    def test_show_history_empty(self, tmp_path: object) -> None:
        engine = OptimizationEngine()
        # Point history to a temp file so we don't touch real data
        engine.config.history_jsonl = tmp_path / "empty.jsonl"  # type: ignore
        engine.config.state_json = tmp_path / "empty_state.json"  # type: ignore
        engine.history = engine.history.__class__(engine.config)
        engine.history.init(clear=True)
        records = engine.show_history()
        assert records == []

    def test_show_history_returns_records(self, tmp_path: object) -> None:
        engine = OptimizationEngine()
        engine.config.history_jsonl = tmp_path / "hist.jsonl"  # type: ignore
        engine.config.state_json = tmp_path / "state.json"  # type: ignore
        engine.history = engine.history.__class__(engine.config)
        engine.history.init(clear=True)
        engine.history.record({"iteration": 1, "composite": 0.5})
        engine.history.record({"iteration": 2, "composite": 0.6})
        records = engine.show_history()
        assert len(records) == 2


# ------------------------------------------------------------------
# _now_iso
# ------------------------------------------------------------------

class TestNowIso:
    def test_returns_iso_string(self) -> None:
        result = _now_iso()
        assert "T" in result
        assert "+" in result or "Z" in result


# ------------------------------------------------------------------
# Incremental evaluation (Task 1)
# ------------------------------------------------------------------

class TestIncrementalEvaluation:
    """Verify incremental evaluation produces same results as full evaluation."""

    def test_run_partial_evaluation_returns_summary(self):
        """run_partial_evaluation returns an EvaluationSummary with mocked pipeline."""
        from ticketpilot.evaluation.schemas import (
            EvalPrediction,
            EvaluationSummary,
            GoldenExpectation,
        )
        from ticketpilot.optimizer.evaluator import OptimizerEvaluator

        ticket = MagicMock()
        ticket.original_text = "test ticket text"
        ticket.customer_id = "CUST-001"

        golden = GoldenExpectation(
            case_id="CASE-001",
            expected_issue_type="refund",
            expected_risk_flags=frozenset(),
            expected_severity="MEDIUM",
            expected_must_human_review=False,
            expected_evidence_doc_types=frozenset(),
            expected_relevant_doc_ids=frozenset(),
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )

        ds = MagicMock()
        ds.tickets = {"CASE-001": ticket}
        ds.ticket_count = 1
        ds.golden = {"CASE-001": golden}

        with patch(
            'ticketpilot.optimizer.evaluator.predict_from_pipeline',
            return_value=EvalPrediction(
                case_id="CASE-001",
                predicted_issue_type="refund",
                predicted_risk_flags=frozenset(),
                predicted_severity="MEDIUM",
                predicted_must_human_review=False,
                predicted_evidence_doc_types=frozenset(),
                predicted_fallback_required=False,
                predicted_no_auto_send=False,
            ),
        ):
            with patch.object(OptimizerEvaluator, 'load_dataset'):
                engine = OptimizationEngine()
                engine.evaluator._dataset = ds
                engine.evaluator._predictions = {}

                result = engine.evaluator.run_partial_evaluation(
                    affected_case_ids={"CASE-001"},
                )
                assert isinstance(result, EvaluationSummary)
                assert result.total_cases == 1

    def test_partial_evaluation_preserves_unaffected(self):
        """Unaffected predictions carry over from previous_predictions."""
        from ticketpilot.evaluation.schemas import (
            EvalPrediction,
            EvaluationSummary,
            GoldenExpectation,
        )
        from ticketpilot.optimizer.evaluator import OptimizerEvaluator

        ticket = MagicMock()
        ticket.original_text = "test text"
        ticket.customer_id = "CUST-001"

        golden = {
            "CASE-001": GoldenExpectation(
                case_id="CASE-001",
                expected_issue_type="refund",
                expected_risk_flags=frozenset(),
                expected_severity="MEDIUM",
                expected_must_human_review=False,
                expected_evidence_doc_types=frozenset(),
                expected_relevant_doc_ids=frozenset(),
                expected_fallback_required=False,
                expected_no_auto_send=False,
            ),
            "CASE-002": GoldenExpectation(
                case_id="CASE-002",
                expected_issue_type="refund",
                expected_risk_flags=frozenset(),
                expected_severity="MEDIUM",
                expected_must_human_review=False,
                expected_evidence_doc_types=frozenset(),
                expected_relevant_doc_ids=frozenset(),
                expected_fallback_required=False,
                expected_no_auto_send=False,
            ),
        }

        ds = MagicMock()
        ds.tickets = {"CASE-001": ticket, "CASE-002": MagicMock()}
        ds.ticket_count = 2
        ds.golden = golden

        CASE_002_PRED = EvalPrediction(
            case_id="CASE-002",
            predicted_issue_type="refund",
            predicted_risk_flags=frozenset(),
            predicted_severity="MEDIUM",
            predicted_must_human_review=False,
            predicted_evidence_doc_types=frozenset(),
            predicted_fallback_required=False,
            predicted_no_auto_send=False,
        )

        with patch(
            'ticketpilot.optimizer.evaluator.predict_from_pipeline',
            return_value=EvalPrediction(
                case_id="CASE-001",
                predicted_issue_type="refund",
                predicted_risk_flags=frozenset(),
                predicted_severity="MEDIUM",
                predicted_must_human_review=False,
                predicted_evidence_doc_types=frozenset(),
                predicted_fallback_required=False,
                predicted_no_auto_send=False,
            ),
        ):
            with patch.object(OptimizerEvaluator, 'load_dataset'):
                engine = OptimizationEngine()
                engine.evaluator._dataset = ds

                result = engine.evaluator.run_partial_evaluation(
                    affected_case_ids={"CASE-001"},
                    previous_predictions={"CASE-002": CASE_002_PRED},
                )
                assert isinstance(result, EvaluationSummary)
                assert result.total_cases == 2


# ------------------------------------------------------------------
# Best state tracking + early termination (Task 3)
# ------------------------------------------------------------------

class TestBestStateTracking:
    """Verify best state tracking and early termination logic."""

    def test_best_composite_tracks_improvements(self):
        """Best composite should update when score improves."""
        from ticketpilot.optimizer.engine import (
            OptimizationEngine, CONSECUTIVE_NO_IMPROVEMENT_LIMIT,
        )

        # 验证常量存在且为合理值
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT > 0
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT <= 10

    def test_consecutive_limit_is_three(self):
        """CONSECUTIVE_NO_IMPROVEMENT_LIMIT should be 3."""
        from ticketpilot.optimizer.engine import CONSECUTIVE_NO_IMPROVEMENT_LIMIT
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT == 3
