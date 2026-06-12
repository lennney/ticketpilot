"""Offline draft evaluation metrics for evidence-grounded draft generation.

All functions are deterministic and operate on in-memory objects without
calling pipeline, DB, embedding provider, LLM, network, or filesystem.

Metric definitions:
- citation_precision: valid cited IDs / total cited IDs (None if no citations)
- evidence_coverage: cited valid evidence IDs / available evidence IDs (None if no evidence)
- unsupported_claim_rate: drafts with unsupported_claims / total drafts
- forbidden_promise_rate: drafts with forbidden promise failures / total drafts
- safe_fallback_rate: safe-fallback drafts / total drafts (1.0 if no fallback cases)
- human_review_trigger_correctness: correct triggers / total cases where condition applies
- citation_validation_pass_rate: structurally valid / total cases
- claim_guard_pass_rate: guard_passed=True / total cases
- average_confidence: mean of non-None confidence values
"""

from __future__ import annotations

from collections import Counter

from ticketpilot.evaluation.schemas import DraftEvaluationRow, DraftEvaluationSummary

# ---------------------------------------------------------------------------
# Per-case metric computation
# ---------------------------------------------------------------------------


def compute_citation_precision(row: DraftEvaluationRow) -> float | None:
    """Citation precision: valid citations / total citations.

    Returns None when there are no cited IDs (avoids division-by-zero
    or misleading 1.0 for substantive responses without citations).
    """
    total = row.valid_citation_count + row.invalid_citation_count
    if total == 0:
        return None
    return row.valid_citation_count / total


def compute_evidence_coverage(row: DraftEvaluationRow) -> float | None:
    """Evidence coverage: cited valid evidence IDs / available evidence IDs.

    Returns None when there are no available evidence candidates
    (avoids claiming 0% coverage when no evidence exists).
    """
    if row.available_evidence_count == 0:
        return None
    return row.cited_evidence_count / row.available_evidence_count


def compute_human_review_trigger_correct(
    row: DraftEvaluationRow,
) -> bool | None:
    """Whether actual_human_review matches expected_human_review.

    Returns None when the case has no trigger condition
    (both expected and actual are False).
    """
    # A case with no trigger condition: expected=False and actual=False
    # is considered correct, but we don't count it in the denominator
    # for trigger correctness (per spec: correctness over cases where
    # condition applies). We still track it as True.
    return row.expected_human_review == row.actual_human_review


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------


def _filter_none(values: list[float | None]) -> list[float]:
    """Drop None values from a list of floats."""
    return [v for v in values if v is not None]


def compute_draft_evaluation_summary(
    rows: list[DraftEvaluationRow],
) -> DraftEvaluationSummary:
    """Aggregate per-case DraftEvaluationRows into a summary.

    Ignores None values for averaging (cite/evidence coverage None
    cases excluded from numerator and denominator).

    Args:
        rows: List of DraftEvaluationRow, one per eval case.

    Returns:
        DraftEvaluationSummary with averaged metrics.
    """
    n = len(rows)
    if n == 0:
        return DraftEvaluationSummary(total_cases=0)

    # Citation precision
    precisions = _filter_none([compute_citation_precision(r) for r in rows])
    citation_precision_avg = sum(precisions) / len(precisions) if precisions else None

    # Evidence coverage
    coverages = _filter_none([compute_evidence_coverage(r) for r in rows])
    evidence_coverage_avg = sum(coverages) / len(coverages) if coverages else None

    # Unsupported claim rate
    unsupported_count = sum(1 for r in rows if r.unsupported_claim_count > 0)
    unsupported_claim_rate = unsupported_count / n

    # Forbidden promise rate
    forbidden_count = sum(1 for r in rows if r.forbidden_promise_count > 0)
    forbidden_promise_rate = forbidden_count / n

    # Safe fallback rate
    fallback_cases = [r for r in rows if r.safe_fallback_used]
    fallback_count = len(fallback_cases)
    safe_fallback_rate = fallback_count / n if n > 0 else 0.0

    # Human review trigger correctness
    # Denominator: cases where any trigger condition exists
    # (expected=True OR any guard/validation failure reason)
    trigger_cases = [
        r for r in rows
        if r.expected_human_review
        or not r.citation_validation_passed
        or not r.guard_passed
    ]
    trigger_correct_count = sum(
        1 for r in trigger_cases if r.expected_human_review == r.actual_human_review
    )
    human_review_trigger_accuracy = (
        trigger_correct_count / len(trigger_cases) if trigger_cases else None
    )

    # Citation validation pass rate
    valid_citation_cases = [
        r for r in rows if r.citation_validation_passed
    ]
    citation_validation_pass_rate = (
        len(valid_citation_cases) / n if n > 0 else 0.0
    )

    # Claim guard pass rate
    guard_pass_cases = [r for r in rows if r.guard_passed]
    claim_guard_pass_rate = len(guard_pass_cases) / n if n > 0 else 0.0

    # Per-failure-type pass rates
    failure_counter: Counter[str] = Counter()
    for r in rows:
        for ft in r.guard_failure_types:
            failure_counter[ft] += 1
    per_failure_type_pass_rates: dict[str, float] = {
        k: (n - v) / n for k, v in failure_counter.items()
    }  # pass rate = 1 - failure_rate

    # Average confidence
    confidences = [r.confidence for r in rows if r.confidence is not None]
    average_confidence = sum(confidences) / len(confidences) if confidences else None

    return DraftEvaluationSummary(
        total_cases=n,
        citation_precision_avg=citation_precision_avg,
        evidence_coverage_avg=evidence_coverage_avg,
        unsupported_claim_rate=unsupported_claim_rate,
        forbidden_promise_rate=forbidden_promise_rate,
        safe_fallback_rate=safe_fallback_rate,
        human_review_trigger_accuracy=human_review_trigger_accuracy,
        citation_validation_pass_rate=citation_validation_pass_rate,
        claim_guard_pass_rate=claim_guard_pass_rate,
        per_failure_type_pass_rates=per_failure_type_pass_rates,
        average_confidence=average_confidence,
    )
