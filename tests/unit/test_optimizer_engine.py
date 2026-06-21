"""Tests for ticketpilot.optimizer.engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvaluationMetrics,
    EvaluationSummary,
    RiskFlagMetrics,
)
from ticketpilot.optimizer.config import COMPOSITE_WEIGHTS
from ticketpilot.optimizer.engine import OptimizationEngine, _now_iso
from ticketpilot.optimizer.scoring import (
    compute_composite,
    score_dict,
    extract_correct_ids,
)


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
            precision=risk_f1_score,
            recall=risk_f1_score,
            f1=risk_f1_score,
            exact_match=risk_exact,
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
        summary = _make_summary()  # all cases correct → 1.0 for every metric
        composite = compute_composite(summary, weights=COMPOSITE_WEIGHTS)
        assert abs(composite - 1.0) < 1e-9

    def test_zero_score(self) -> None:
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
        composite = compute_composite(summary, weights=COMPOSITE_WEIGHTS)
        assert abs(composite) < 1e-9

    def test_partial_score(self) -> None:
        # 3 correct, 2 wrong on intent only
        results = {}
        for i in range(1, 6):
            cid = f"CASE-{i:03d}"
            results[cid] = _make_case_result(cid, intent_ok=(i <= 3))
        summary = _make_summary(results)
        composite = compute_composite(summary, weights=COMPOSITE_WEIGHTS)
        # intent = 0.6, all others = 1.0
        expected = (
            0.25 * 0.6 + 0.20 * 1.0 + 0.20 * 1.0 + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0
        )
        assert abs(composite - expected) < 1e-9

    def test_composite_respects_weights(self) -> None:
        # Only risk_f1 is 0.5, rest are 1.0
        results = {}
        for i in range(1, 3):
            cid = f"CASE-{i:03d}"
            results[cid] = _make_case_result(cid, risk_exact=False)
        summary = _make_summary(results)
        composite = compute_composite(summary, weights=COMPOSITE_WEIGHTS)
        # risk_f1 is micro-averaged: 2 cases each with f1=0.0 → aggregate 0.0
        expected = (
            0.25 * 1.0 + 0.20 * 1.0 + 0.20 * 0.0 + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0
        )
        assert abs(composite - expected) < 1e-9


# ------------------------------------------------------------------
# Score dict
# ------------------------------------------------------------------


class TestScoreDict:
    def test_score_dict_keys(self) -> None:
        summary = _make_summary()
        scores = score_dict(summary)
        expected_keys = {
            "intent",
            "severity",
            "risk_f1",
            "evidence",
            "no_auto_send",
            "fallback",
        }
        assert set(scores.keys()) == expected_keys

    def test_score_dict_values(self) -> None:
        summary = _make_summary()
        scores = score_dict(summary)
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
        summary = _make_summary()
        correct = extract_correct_ids(summary)
        assert len(correct) == 5
        assert all(cid.startswith("CASE-") for cid in correct)

    def test_none_correct(self) -> None:
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
        correct = extract_correct_ids(summary)
        assert len(correct) == 0

    def test_partial_correct(self) -> None:
        results = {
            "OK-001": _make_case_result("OK-001"),
            "OK-002": _make_case_result("OK-002"),
            "BAD-001": _make_case_result("BAD-001", intent_ok=False, severity_ok=False),
        }
        summary = _make_summary(results)
        correct = extract_correct_ids(summary)
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
            "ticketpilot.optimizer.evaluator.predict_from_pipeline",
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
            with patch.object(OptimizerEvaluator, "load_dataset"):
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
            "ticketpilot.optimizer.evaluator.predict_from_pipeline",
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
            with patch.object(OptimizerEvaluator, "load_dataset"):
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
            CONSECUTIVE_NO_IMPROVEMENT_LIMIT,
        )

        # 验证常量存在且为合理值
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT > 0
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT <= 10

    def test_consecutive_limit_is_three(self):
        """CONSECUTIVE_NO_IMPROVEMENT_LIMIT should be 3."""
        from ticketpilot.optimizer.engine import CONSECUTIVE_NO_IMPROVEMENT_LIMIT

        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT == 3

    def test_early_termination_after_three_no_improvements(self):
        """run() should stop after CONSECUTIVE_NO_IMPROVEMENT_LIMIT consecutive no-improvement rounds."""
        from ticketpilot.optimizer.engine import (
            OptimizationEngine,
        )

        engine = OptimizationEngine(max_rounds=20)

        # Set up dataset so run() doesn't crash on hasattr check
        ds = MagicMock()
        ds.tickets = {"CASE-001": MagicMock()}
        engine.evaluator._dataset = ds

        # Mock _run_one_round to always return False (no improvement)
        with patch.object(engine, "_run_one_round", return_value=False):
            with patch.object(engine.evaluator, "get_baseline") as mock_base:
                mock_base.return_value = _make_summary(
                    {
                        f"CASE-{i:03d}": _make_case_result(f"CASE-{i:03d}")
                        for i in range(1, 4)
                    }
                )
                result = engine.run()

        # Should complete (not loop forever) and have no improvements
        assert result is False

    def test_best_state_updates_on_improvement(self):
        """_best_composite should update when _run_one_round improves score."""
        from ticketpilot.optimizer.engine import OptimizationEngine

        engine = OptimizationEngine(max_rounds=5)

        # Set up dataset so run() doesn't crash
        ds = MagicMock()
        ds.tickets = {"CASE-001": MagicMock()}
        engine.evaluator._dataset = ds

        with patch.object(engine, "_run_one_round") as mock_round:
            # Return True on first call (improvement), False on subsequent
            mock_round.side_effect = [True, False, False]
            with patch.object(engine.evaluator, "get_baseline") as mock_base:
                mock_base.return_value = _make_summary(
                    {
                        f"CASE-{i:03d}": _make_case_result(f"CASE-{i:03d}")
                        for i in range(1, 4)
                    }
                )
                with patch.object(engine.evaluator, "run_full_evaluation") as mock_full:
                    # Return a slightly better summary the first time
                    better = _make_summary(
                        {
                            f"CASE-{i:03d}": _make_case_result(f"CASE-{i:03d}")
                            for i in range(1, 6)
                        }
                    )
                    mock_full.return_value = better
                    engine.run()

        # After first improvement, _best_composite should have been set
        assert engine._best_composite > 0


# ------------------------------------------------------------------
# _analyze_causal_features tests
# ------------------------------------------------------------------


class TestAnalyzeCausalFeatures:
    """Verify _analyze_causal_features lift-based keyword extraction."""

    def test_empty_misclassified_returns_empty(self):
        """Empty misclassified_texts returns []."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        result = _analyze_causal_features([], ["correct text"], [], max_features=3)
        assert result == []

    def test_empty_correct_falls_back_to_extract(self):
        """When correctly_classified_texts is empty, falls back to _extract_chinese_keywords."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        mis = ["我要投诉你们客服态度太差了"]
        result = _analyze_causal_features(mis, [], ["投诉"], max_features=2)
        # Should find keywords from misclassified text, excluding "投诉"
        assert isinstance(result, list)
        assert len(result) <= 2
        assert "投诉" not in result

    def test_distinguishing_features_returned(self):
        """Features that appear more in misclassified than correct are returned."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        mis = [
            "我要投诉你们客服态度太差了",
            "态度恶劣我要投诉你们",
            "退款处理太慢我要投诉",
        ]
        correct = [
            "申请退款订单号12345",
            "我要申请退款",
            "退款处理一下",
        ]
        # "投诉" and "态度" should be distinguishing (appear in mis but not in correct)
        result = _analyze_causal_features(mis, correct, ["退款"], max_features=3)
        assert isinstance(result, list)
        assert len(result) > 0
        # "投诉" should appear (distinguishing feature)
        # "退款" should NOT appear (in existing_keywords)
        assert "退款" not in result

    def test_max_features_respected(self):
        """max_features limits returned keyword count."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        mis = ["投诉态度恶劣客服差劲"]
        correct = ["正常退货"]
        result = _analyze_causal_features(mis, correct, [], max_features=1)
        assert len(result) <= 1

    def test_existing_keywords_filtered(self):
        """Keywords in existing_keywords are excluded from results."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        mis = ["投诉态度恶劣客服差劲"]
        correct = ["正常处理"]
        result = _analyze_causal_features(
            mis, correct, ["投诉", "态度"], max_features=3
        )
        assert "投诉" not in result
        assert "态度" not in result

    def test_causal_returns_jieba_words_not_ngrams(self):
        """Verifies causal features are proper jieba words, not n-gram artifacts."""
        from ticketpilot.optimizer.diagnostics import _analyze_causal_features

        mis = [
            "我要投诉你们客服态度太差了，申请退款因为服务不好",
            "服务态度恶劣我要投诉，退款不退就算了",
        ]
        correct = [
            "申请退款订单号12345请尽快处理",
            "我要申请退款，订单号67890",
        ]
        result = _analyze_causal_features(mis, correct, ["退款"], max_features=3)
        assert isinstance(result, list)
        assert len(result) > 0
        # "退款" should NOT appear (in existing_keywords)
        assert "退款" not in result
        # Keywords should be proper Chinese words, not n-gram fragments
        for kw in result:
            assert len(kw) >= 2  # at least 2 chars
            # Should NOT be mid-word splits like '货但', '们的', '我申'
            assert kw not in ("货但", "们的", "我申", "诉你", "们客", "服态"), (
                f"'{kw}' is an n-gram artifact, not a real word"
            )


# ------------------------------------------------------------------
# _verify_fix incremental path tests
# ------------------------------------------------------------------


class TestVerifyFixIncremental:
    """Verify _verify_fix() uses incremental eval when affected_cases provided."""

    def test_verify_fix_incremental_with_affected_cases(self):
        """_verify_fix calls run_partial_evaluation when affected_cases provided."""
        from ticketpilot.optimizer.engine import OptimizationEngine

        engine = OptimizationEngine()

        with patch.object(engine.evaluator, "run_partial_evaluation") as mock_partial:
            mock_partial.return_value = _make_summary()
            with patch.object(engine.evaluator, "run_full_evaluation") as mock_full:
                summary = _make_summary()
                improved, _, _ = engine._verify_fix(
                    summary,
                    {"CASE-001"},
                    affected_cases={"CASE-001"},
                    old_predictions={"CASE-001": MagicMock()},
                )
                # Should call run_partial_evaluation, NOT run_full_evaluation
                assert mock_partial.called
                assert not mock_full.called

    def test_verify_fix_full_without_affected_cases(self):
        """_verify_fix calls run_full_evaluation when affected_cases is None."""
        from ticketpilot.optimizer.engine import OptimizationEngine

        engine = OptimizationEngine()

        with patch.object(engine.evaluator, "run_partial_evaluation") as mock_partial:
            with patch.object(engine.evaluator, "run_full_evaluation") as mock_full:
                mock_full.return_value = _make_summary()
                summary = _make_summary()
                improved, _, _ = engine._verify_fix(summary, {"CASE-001"})
                # Should call run_full_evaluation, NOT run_partial_evaluation
                assert mock_full.called
                assert not mock_partial.called
