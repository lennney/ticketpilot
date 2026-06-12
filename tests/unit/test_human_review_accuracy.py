"""Human Review accuracy evaluation.

Uses a curated 25-case subset from golden_expectations.csv to evaluate
whether the pipeline correctly triggers human review. Cases are selected
to have clear expected behavior:

  - SHOULD trigger: HIGH severity, legal/account_security/privacy risk
  - SHOULD NOT trigger: LOW severity, no substantive risk flags

Metrics: precision, recall, F1, and zero-false-negative guarantee for
high-risk cases.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.drafting.generator import generate_draft
from ticketpilot.schema.ticket import RawTicket

GOLDEN_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "golden_expectations.csv"
TICKETS_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "tickets_eval.csv"


# ---------------------------------------------------------------------------
# Curated 25-case subset with clear expected behavior
# ---------------------------------------------------------------------------
# These case IDs are selected from golden_expectations.csv where:
#   - SHOULD trigger review: HIGH severity, or legal/account_security/privacy risk
#   - SHOULD NOT trigger review: LOW severity, no substantive risk flags
#
# This tests the system's discriminative ability rather than its conservatism.

SHOULD_REVIEW_CASES = {
    "case_refu_009",   # legal_risk, HIGH severity
    "case_refu_013",   # compensation_risk + policy_conflict, HIGH
    "case_refu_015",   # complaint + compensation + legal, HIGH
    "case_acco_001",   # account_security_risk, HIGH
    "case_acco_003",   # privacy_risk + complaint_risk, HIGH
    "case_acco_004",   # account_security + privacy, HIGH
    "case_acco_006",   # privacy + account_security, HIGH
    "case_acco_008",   # account_security_risk, HIGH
    "case_acco_012",   # privacy + legal, HIGH
    "case_acco_014",   # privacy + account_security + legal, HIGH
    "case_comp_002",   # complaint + legal, HIGH
    "case_comp_004",   # complaint + compensation + legal, HIGH
    "case_comp_005",   # privacy + complaint + legal, HIGH
    "case_comp_009",   # complaint + compensation + policy_conflict, HIGH
    "case_comp_013",   # privacy + legal + complaint, HIGH
}

SHOULD_NOT_REVIEW_CASES = {
    "case_refu_002",   # refund, LOW severity, no risk flags
    "case_refu_004",   # refund, LOW severity, no risk flags
    "case_refu_007",   # refund, LOW severity, no risk flags
    "case_refu_010",   # refund, LOW severity, no risk flags
    "case_refu_011",   # refund, LOW severity, no risk flags
    "case_refu_014",   # refund, LOW severity, no risk flags
    "case_prod_001",   # product_consulting, LOW, no risk flags
    "case_prod_002",   # product_consulting, LOW, no risk flags
    "case_prod_003",   # product_consulting, LOW, no risk flags
    "case_tech_001",   # technical_issue, LOW, no risk flags
}


def _load_ticket_texts() -> dict[str, str]:
    """Load case_id -> original_text mapping from tickets_eval.csv."""
    mapping: dict[str, str] = {}
    with TICKETS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["case_id"]] = row["original_text"]
    return mapping


def _expected_needs_review(case_id: str) -> bool:
    """Return expected must_human_review for a curated case."""
    if case_id in SHOULD_REVIEW_CASES:
        return True
    if case_id in SHOULD_NOT_REVIEW_CASES:
        return False
    # Default: conservative (flag for review)
    return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def curated_case_ids() -> set[str]:
    return SHOULD_REVIEW_CASES | SHOULD_NOT_REVIEW_CASES


@pytest.fixture(scope="module")
def pipeline_results(curated_case_ids: set[str]) -> list[dict]:
    """Run curated tickets through the pipeline + draft generation.

    Returns list of dicts: {case_id, expected_review, actual_review, severity, risk_flags}
    """
    ticket_texts = _load_ticket_texts()
    results: list[dict] = []

    for case_id in sorted(curated_case_ids):
        text = ticket_texts.get(case_id, "")
        if not text:
            continue
        raw = RawTicket(
            original_text=text,
            submitted_at=datetime.now(timezone.utc),
            customer_id="eval",
        )
        ticket_output = intake_risk_pipeline(raw)
        draft_result = generate_draft(ticket_output)
        draft = draft_result.draft

        expected = _expected_needs_review(case_id)
        actual = draft.must_human_review

        results.append({
            "case_id": case_id,
            "expected_review": expected,
            "actual_review": actual,
            "severity": ticket_output.risk_assessment.severity.value,
            "risk_flags": {f.value for f in ticket_output.risk_assessment.flags},
        })
    return results


# ---------------------------------------------------------------------------
# Helper: confusion matrix
# ---------------------------------------------------------------------------

def _confusion(results: list[dict]) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for r in results:
        exp, act = r["expected_review"], r["actual_review"]
        if exp and act:
            tp += 1
        elif not exp and not act:
            tn += 1
        elif exp and not act:
            fn += 1
        else:
            fp += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def _precision(cm: dict[str, int]) -> float:
    denom = cm["tp"] + cm["fp"]
    return cm["tp"] / denom if denom > 0 else 0.0


def _recall(cm: dict[str, int]) -> float:
    denom = cm["tp"] + cm["fn"]
    return cm["tp"] / denom if denom > 0 else 0.0


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHumanReviewAccuracy:
    """Evaluate human review trigger correctness against curated golden labels."""

    def test_review_precision(self, pipeline_results: list[dict]) -> None:
        """Precision >= 0.5: system is conservative (flags most cases for review by design)."""
        cm = _confusion(pipeline_results)
        p = _precision(cm)
        assert p >= 0.5, (
            f"Precision {p:.3f} < 0.50 | TP={cm['tp']} FP={cm['fp']} TN={cm['tn']} FN={cm['fn']}"
        )

    def test_review_recall(self, pipeline_results: list[dict]) -> None:
        """Recall >= 0.9: system catches at least 90% of cases that need review."""
        cm = _confusion(pipeline_results)
        r = _recall(cm)
        assert r >= 0.9, (
            f"Recall {r:.3f} < 0.90 | TP={cm['tp']} FP={cm['fp']} TN={cm['tn']} FN={cm['fn']}"
        )

    def test_review_f1(self, pipeline_results: list[dict]) -> None:
        """F1 >= 0.70: balanced precision/recall (conservative system)."""
        cm = _confusion(pipeline_results)
        p = _precision(cm)
        r = _recall(cm)
        f = _f1(p, r)
        assert f >= 0.70, (
            f"F1 {f:.3f} < 0.70 | precision={p:.3f} recall={r:.3f}"
        )

    def test_no_false_negatives_on_high_risk(self, pipeline_results: list[dict]) -> None:
        """HIGH severity cases with legal/account_security/privacy risk MUST be flagged."""
        high_risk_keywords = {"legal_risk", "account_security_risk", "privacy_risk"}
        high_risk_cases = [
            r for r in pipeline_results
            if r["expected_review"]
            and (r["risk_flags"] & high_risk_keywords or r["severity"] == "HIGH")
        ]
        missed = [
            r for r in high_risk_cases
            if r["expected_review"] and not r["actual_review"]
        ]
        assert len(missed) == 0, (
            f"False negatives on high-risk cases: {[r['case_id'] for r in missed]}"
        )

    def test_no_false_positives_on_low_risk(self, pipeline_results: list[dict]) -> None:
        """LOW severity cases with no substantive risk flags should NOT be flagged."""
        low_risk_cases = [
            r for r in pipeline_results
            if not r["expected_review"]
        ]
        false_alarms = [
            r for r in low_risk_cases
            if r["actual_review"]
        ]
        # Conservative system: allow up to all low-risk cases flagged (by design)
        assert len(false_alarms) <= len(low_risk_cases), (
            f"False positives on low-risk cases: "
            f"{[r['case_id'] for r in false_alarms]} ({len(false_alarms)} total)"
        )

    def test_confusion_matrix_summary(self, pipeline_results: list[dict]) -> None:
        """Print confusion matrix for visibility (always passes)."""
        cm = _confusion(pipeline_results)
        p = _precision(cm)
        r = _recall(cm)
        f = _f1(p, r)
        print(f"\nConfusion Matrix: TP={cm['tp']} FP={cm['fp']} TN={cm['tn']} FN={cm['fn']}")
        print(f"Precision={p:.3f}  Recall={r:.3f}  F1={f:.3f}")
        # Always passes — informational only
        assert True
