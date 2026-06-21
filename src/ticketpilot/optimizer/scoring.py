"""Scoring helpers for the optimizer — composite score, metric dict, and correct-case extraction.

These module-level functions are extracted from ``OptimizationEngine`` so they
can be imported and tested independently.
"""
from __future__ import annotations

import logging

from ticketpilot.evaluation.schemas import EvaluationSummary

logger = logging.getLogger(__name__)


def compute_composite(summary: EvaluationSummary, weights: dict[str, float]) -> float:
    """Compute the weighted composite score from an evaluation summary.

    Uses the provided ``weights`` dict, e.g. ``COMPOSITE_WEIGHTS``::

        intent * 0.25 + severity * 0.20 + risk_f1 * 0.20
        + evidence * 0.15 + no_auto_send * 0.10 + fallback * 0.10

    Returns:
        Float in [0.0, 1.0].
    """
    scores = score_dict(summary)
    return sum(
        scores[metric] * weight
        for metric, weight in weights.items()
    )


def score_dict(summary: EvaluationSummary) -> dict[str, float]:
    """Extract the metric dict used for composite scoring.

    Returns:
        Dict mapping metric names to their float values:
        ``intent``, ``severity``, ``risk_f1``, ``evidence``,
        ``no_auto_send``, ``fallback``.
    """
    return {
        "intent": summary.aggregate_intent_accuracy,
        "severity": summary.aggregate_severity_accuracy,
        "risk_f1": summary.aggregate_risk_flag_f1,
        "evidence": summary.aggregate_evidence_doc_type_recall,
        "no_auto_send": summary.aggregate_no_auto_send_compliance,
        "fallback": summary.aggregate_fallback_correctness,
    }


def extract_correct_ids(summary: EvaluationSummary) -> set[str]:
    """Get the set of case IDs where all metrics are correct.

    A case is "correct" if its intent accuracy, severity accuracy,
    risk flag exact match, fallback correctness, and no_auto_send
    compliance are all ``True``.
    """
    correct: set[str] = set()
    for case_id, case in summary.results.items():
        m = case.metrics
        if (
            m.intent_accuracy
            and m.severity_accuracy
            and m.risk_flag_metrics.exact_match
            and m.fallback_correctness
            and m.no_auto_send_compliance
        ):
            correct.add(case_id)
    return correct
