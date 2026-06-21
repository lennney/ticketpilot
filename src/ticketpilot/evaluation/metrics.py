"""Deterministic metric computation for the evaluation pipeline.

All metric functions are pure and deterministic:
- Operate on in-memory objects (EvalPrediction, GoldenExpectation)
- Do NOT call pipeline, DB, embedding provider, LLM, network, or filesystem
- Produce identical results for identical inputs
- Handle edge cases (empty sets, missing data) deterministically
"""

from __future__ import annotations

from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvalPrediction,
    EvaluationMetrics,
    EvaluationSummary,
    GoldenExpectation,
    MismatchEntry,
    RiskFlagMetrics,
)


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------


def compute_risk_flag_metrics(
    predicted: frozenset[str],
    expected: frozenset[str],
) -> RiskFlagMetrics:
    """Compute precision, recall, F1, and exact-match for risk flags.

    Handles edge cases:
    - Empty predicted + empty expected -> precision=1.0, recall=1.0, F1=1.0
    - Empty expected + non-empty predicted -> precision=0.0, recall=1.0, F1=0.0
    - Non-empty expected + empty predicted -> precision=1.0, recall=0.0, F1=0.0
    """
    true_positives = len(predicted & expected)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 1.0
    )
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0.0
        else 0.0
    )
    exact_match = predicted == expected

    return RiskFlagMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        exact_match=exact_match,
    )


def compute_evidence_doc_type_recall(
    predicted: frozenset[str],
    expected: frozenset[str],
) -> float:
    """Compute recall of expected evidence document types.

    Recall = |predicted ∩ expected| / |expected|.
    Returns 1.0 when expected is empty (nothing to miss).

    Args:
        predicted: Set of document types the system retrieved.
        expected: Set of document types that should have been retrieved.

    Returns:
        Recall in [0.0, 1.0].
    """
    if not expected:
        return 1.0
    matched = len(predicted & expected)
    return matched / len(expected)


# ---------------------------------------------------------------------------
# Per-case and aggregate computation
# ---------------------------------------------------------------------------


def compute_case_metrics(
    prediction: EvalPrediction,
    golden: GoldenExpectation,
) -> CaseResult:
    """Compute all metrics for a single case and record any mismatches.

    Args:
        prediction: The predicted pipeline output for this case.
        golden: The golden expectation for this case.

    Returns:
        CaseResult with all computed metrics and mismatches.
    """
    mismatches: list[MismatchEntry] = []

    # 1. Intent accuracy
    intent_accuracy = prediction.predicted_issue_type == golden.expected_issue_type
    if not intent_accuracy:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="intent_accuracy",
                expected=golden.expected_issue_type,
                predicted=prediction.predicted_issue_type,
            )
        )

    # 2. Severity accuracy
    severity_accuracy = prediction.predicted_severity == golden.expected_severity
    if not severity_accuracy:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="severity_accuracy",
                expected=golden.expected_severity,
                predicted=prediction.predicted_severity,
            )
        )

    # 3. Must-human-review accuracy
    must_human_review_accuracy = (
        prediction.predicted_must_human_review == golden.expected_must_human_review
    )
    if not must_human_review_accuracy:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="must_human_review_accuracy",
                expected=str(golden.expected_must_human_review),
                predicted=str(prediction.predicted_must_human_review),
            )
        )

    # 4. Risk flag metrics
    risk_flag_metrics = compute_risk_flag_metrics(
        prediction.predicted_risk_flags,
        golden.expected_risk_flags,
    )
    if not risk_flag_metrics.exact_match:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="risk_flags",
                expected=",".join(sorted(golden.expected_risk_flags)),
                predicted=",".join(sorted(prediction.predicted_risk_flags)),
            )
        )

    # 5. Evidence doc type recall
    evidence_doc_type_recall = compute_evidence_doc_type_recall(
        prediction.predicted_evidence_doc_types,
        golden.expected_evidence_doc_types,
    )
    if evidence_doc_type_recall < 1.0:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="evidence_doc_type_recall",
                expected=",".join(sorted(golden.expected_evidence_doc_types)),
                predicted=",".join(sorted(prediction.predicted_evidence_doc_types)),
            )
        )

    # 6. Fallback correctness
    fallback_correctness = (
        prediction.predicted_fallback_required == golden.expected_fallback_required
    )
    if not fallback_correctness:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="fallback_correctness",
                expected=str(golden.expected_fallback_required),
                predicted=str(prediction.predicted_fallback_required),
            )
        )

    # 7. No-auto-send compliance
    no_auto_send_compliance = (
        prediction.predicted_no_auto_send == golden.expected_no_auto_send
    )
    if not no_auto_send_compliance:
        mismatches.append(
            MismatchEntry(
                case_id=golden.case_id,
                metric="no_auto_send_compliance",
                expected=str(golden.expected_no_auto_send),
                predicted=str(prediction.predicted_no_auto_send),
            )
        )

    metrics = EvaluationMetrics(
        intent_accuracy=intent_accuracy,
        severity_accuracy=severity_accuracy,
        must_human_review_accuracy=must_human_review_accuracy,
        risk_flag_metrics=risk_flag_metrics,
        evidence_doc_type_recall=evidence_doc_type_recall,
        fallback_correctness=fallback_correctness,
        no_auto_send_compliance=no_auto_send_compliance,
    )

    return CaseResult(
        case_id=golden.case_id,
        golden=golden,
        prediction=prediction,
        metrics=metrics,
        mismatches=mismatches,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_predictions(
    predictions: dict[str, EvalPrediction],
    golden: dict[str, GoldenExpectation],
) -> list[str]:
    """Validate predictions against golden expectations.

    Checks:
    - Every golden case has a matching prediction.
    - Every prediction has a matching golden case.

    Args:
        predictions: Dict of case_id -> EvalPrediction.
        golden: Dict of case_id -> GoldenExpectation.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []

    golden_ids = set(golden.keys())
    prediction_ids = set(predictions.keys())

    # Missing predictions for golden cases
    missing = golden_ids - prediction_ids
    for case_id in sorted(missing):
        errors.append(f"Missing prediction for golden case '{case_id}'")

    # Predictions without golden cases
    extra = prediction_ids - golden_ids
    for case_id in sorted(extra):
        errors.append(f"Prediction without golden case '{case_id}'")

    return errors


# ---------------------------------------------------------------------------
# Aggregate evaluation
# ---------------------------------------------------------------------------


def compute_evaluation_summary(
    predictions: dict[str, EvalPrediction],
    golden: dict[str, GoldenExpectation],
) -> EvaluationSummary:
    """Compute a full evaluation summary for all cases.

    Args:
        predictions: Dict of case_id -> EvalPrediction.
        golden: Dict of case_id -> GoldenExpectation.

    Returns:
        EvaluationSummary with per-case results and aggregate metrics.

    Raises:
        ValueError: If prediction validation fails (missing or extra IDs).
    """
    errors = validate_predictions(predictions, golden)
    if errors:
        raise ValueError("Prediction validation failed:\n" + "\n".join(errors))

    results: dict[str, CaseResult] = {}
    all_mismatches: list[MismatchEntry] = []

    for case_id in golden:
        result = compute_case_metrics(predictions[case_id], golden[case_id])
        results[case_id] = result
        all_mismatches.extend(result.mismatches)

    total = len(results)
    if total == 0:
        return EvaluationSummary(
            total_cases=0,
            results={},
            failed_cases=[],
        )

    # Aggregate boolean metrics (rate-based)
    intent_correct = sum(1 for r in results.values() if r.metrics.intent_accuracy)
    severity_correct = sum(1 for r in results.values() if r.metrics.severity_accuracy)
    must_human_review_correct = sum(
        1 for r in results.values() if r.metrics.must_human_review_accuracy
    )
    fallback_correct = sum(
        1 for r in results.values() if r.metrics.fallback_correctness
    )
    no_auto_send_correct = sum(
        1 for r in results.values() if r.metrics.no_auto_send_compliance
    )

    # Quality gate metrics
    # quality_gate_accuracy: fraction of cases where quality prediction matches golden no_auto_send
    quality_gate_correct = sum(
        1
        for r in results.values()
        if r.prediction.predicted_no_auto_send == r.golden.expected_no_auto_send
    )
    quality_gate_accuracy = quality_gate_correct / total

    # quality_intercept_rate: fraction of high-confidence cases where quality blocked auto-send
    # "High confidence" = must_human_review is False (pipeline considers safe for auto-send)
    # "Quality blocked" = predicted_no_auto_send is True (quality gate prevented auto-send)
    high_confidence_cases = [
        r for r in results.values() if not r.prediction.predicted_must_human_review
    ]
    if high_confidence_cases:
        intercepted_count = sum(
            1 for r in high_confidence_cases if r.prediction.predicted_no_auto_send
        )
        quality_intercept_rate = intercepted_count / len(high_confidence_cases)
    else:
        quality_intercept_rate = 0.0

    # Micro-averaged risk flag metrics (sum TP/FP/FN across all cases)
    total_tp = 0
    total_fp = 0
    total_fn = 0
    for r in results.values():
        pred_flags = r.prediction.predicted_risk_flags
        gold_flags = r.golden.expected_risk_flags
        total_tp += len(pred_flags & gold_flags)
        total_fp += len(pred_flags - gold_flags)
        total_fn += len(gold_flags - pred_flags)

    micro_precision = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    )
    micro_recall = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    )
    micro_f1 = (
        2.0 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0.0
        else 0.0
    )

    # Average evidence doc type recall
    avg_evidence_recall = (
        sum(r.metrics.evidence_doc_type_recall for r in results.values()) / total
    )

    return EvaluationSummary(
        total_cases=total,
        results=results,
        aggregate_intent_accuracy=intent_correct / total,
        aggregate_severity_accuracy=severity_correct / total,
        aggregate_must_human_review_accuracy=must_human_review_correct / total,
        aggregate_risk_flag_precision=micro_precision,
        aggregate_risk_flag_recall=micro_recall,
        aggregate_risk_flag_f1=micro_f1,
        aggregate_evidence_doc_type_recall=avg_evidence_recall,
        aggregate_fallback_correctness=fallback_correct / total,
        aggregate_no_auto_send_compliance=no_auto_send_correct / total,
        quality_gate_accuracy=quality_gate_accuracy,
        quality_intercept_rate=quality_intercept_rate,
        failed_cases=all_mismatches,
    )
