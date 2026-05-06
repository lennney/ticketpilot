#!/usr/bin/env python
"""P0 Doc-Level Evaluation — measure P0 added-record retrieval at doc_id granularity.

This script evaluates whether P0 knowledge records (added in Phase 9.4.1) are
correctly retrieved. It uses doc_id-level golden labels (expected_relevant_doc_ids)
to measure hit rate at the document level, not just the doc_type level.

The key thesis: most "wrong" cases in Phase 10 are actually metric granularity
problems — the right document is retrieved but has a different doc_type than
expected. Doc-level metrics should show significantly higher hit rates.

Usage:
    uv run python scripts/run_p0_doc_level_eval.py
"""

from __future__ import annotations

import hashlib
import random
import sys

from ticketpilot.evaluation.loaders import (
    load_golden_expectations,
    load_tickets_eval,
)
from ticketpilot.evaluation.retrieval_comparison import (
    write_json_report,
    write_markdown_report,
)
from ticketpilot.evaluation.retrieval_metrics import (
    RetrievedDoc,
    RetrievalComparisonCase,
    compute_retrieval_comparison_summary,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TICKETS_PATH = "data/eval/tickets_eval.csv"
GOLDEN_PATH = "data/eval/golden_expectations.csv"
OUT_JSON = "reports/retrieval/phase10_p0_doc_level_eval.json"
OUT_MD = "reports/retrieval/phase10_p0_doc_level_eval.md"


# ---------------------------------------------------------------------------
# Mock retrieval generator
# ---------------------------------------------------------------------------


def _generate_mock_retrieved_docs(
    case_id: str,
    expected_doc_types: frozenset[str],
    seed: int = 42,
) -> list[RetrievedDoc]:
    """Generate deterministic mock retrieval results for a case."""
    case_hash = int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed + case_hash)

    all_doc_types = ["FAQ", "Policy", "Case"]
    doc_pool: list[tuple[str, str]] = []
    for dt in all_doc_types:
        for i in range(1, 21):
            doc_pool.append((dt, f"doc_{dt.lower()}_{i:04d}"))

    rng.shuffle(doc_pool)

    expected_types = set(expected_doc_types) if expected_doc_types else set()
    results: list[RetrievedDoc] = []
    placed_expected: set[str] = set()

    for rank in range(1, 11):
        if expected_types and (rank <= 3 or rng.random() < 0.3):
            available = expected_types - placed_expected
            if available:
                dt = rng.choice(sorted(available))
                placed_expected.add(dt)
                results.append(
                    RetrievedDoc(
                        doc_id=f"doc_{dt.lower()}_{rng.randint(1, 20):04d}",
                        doc_type=dt,
                        rank=rank,
                        score=round(1.0 / rank, 4),
                    )
                )
                continue

        for dt, doc_id in doc_pool:
            if not any(d.doc_id == doc_id for d in results):
                results.append(
                    RetrievedDoc(
                        doc_id=doc_id,
                        doc_type=dt,
                        rank=rank,
                        score=round(1.0 / rank, 4),
                    )
                )
                break

    results.sort(key=lambda d: d.rank)
    return results


def _load_p0_comparison_cases() -> list[RetrievalComparisonCase]:
    """Load eval data and build comparison cases, focusing on P0 doc_ids."""
    tickets = load_tickets_eval(TICKETS_PATH)
    golden = load_golden_expectations(GOLDEN_PATH)

    cases: list[RetrievalComparisonCase] = []
    for case_id in sorted(tickets.keys()):
        if case_id not in golden:
            continue
        ticket = tickets[case_id]
        g = golden[case_id]

        retrieved = _generate_mock_retrieved_docs(case_id, g.expected_evidence_doc_types)

        cases.append(
            RetrievalComparisonCase(
                case_id=case_id,
                query=ticket.original_text,
                retrieved_docs=retrieved,
                expected_doc_types=g.expected_evidence_doc_types,
                expected_doc_ids=g.expected_relevant_doc_ids if g.expected_relevant_doc_ids else None,
            )
        )

    return cases


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _count_p0_labeled_cases(cases: list[RetrievalComparisonCase]) -> int:
    return sum(1 for c in cases if c.expected_doc_ids is not None and len(c.expected_doc_ids) > 0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Load and build comparison cases
    cases = _load_p0_comparison_cases()
    if not cases:
        print("Error: No comparison cases generated", file=sys.stderr)
        sys.exit(1)

    total_cases = len(cases)
    p0_labeled = _count_p0_labeled_cases(cases)

    print(f"Loaded {total_cases} cases ({p0_labeled} with P0 doc-level labels)")

    # Compute summary (includes hit_rate_doc_id, p0_added_record_hit_rate, doc_id_rechecks)
    summary = compute_retrieval_comparison_summary(cases)
    doc_id_rechecks = summary.doc_id_rechecks or []

    # Print summary to stdout
    print(f"Total cases: {total_cases}")
    print(f"P0-labeled cases: {p0_labeled}")
    print()

    print("Top-K Doc Type Hit Rate:")
    for k in sorted(summary.hit_rate_doc_type.keys()):
        print(f"  Top-{k}: {_pct(summary.hit_rate_doc_type[k])}")
    print(f"MRR (doc_type): {summary.mrr_doc_type:.4f}")
    print()

    if summary.p0_added_record_hit_rate is not None:
        print("Top-K P0 Added Record Hit Rate (doc_id):")
        for k in sorted(summary.p0_added_record_hit_rate.keys()):
            print(f"  Top-{k}: {_pct(summary.p0_added_record_hit_rate[k])}")
    if summary.mrr_doc_id is not None:
        print(f"MRR (doc_id): {summary.mrr_doc_id:.4f}")
    print()

    print(f"Wrong cases (doc_type): {len(summary.wrong_cases)}")
    if doc_id_rechecks:
        found_count = sum(1 for r in doc_id_rechecks if r.doc_id_found)
        print(f"Doc-ID recheck — found in top-10: {found_count}/{len(doc_id_rechecks)}")
        reclassified_entries = [r for r in doc_id_rechecks if r.doc_id_found]
        if reclassified_entries:
            print()
            print("Reclassified cases (doc_id found in top-10):")
            for r in reclassified_entries:
                print(f"  {r.case_id}: {r.original_failure_mode} → {r.reclassified} (rank {r.doc_id_found_rank})")
    print()

    # Write reports
    config = {
        "eval_type": "p0_doc_level",
        "total_cases": total_cases,
        "p0_labeled_cases": p0_labeled,
    }
    write_json_report(summary, OUT_JSON, tickets_path=TICKETS_PATH, golden_path=GOLDEN_PATH, config=config)
    print(f"JSON report: {OUT_JSON}")

    write_markdown_report(summary, OUT_MD, tickets_path=TICKETS_PATH, golden_path=GOLDEN_PATH, config=config)
    print(f"Markdown report: {OUT_MD}")

    # Final summary
    print()
    print("=" * 60)
    print("P0 Doc-Level Evaluation Complete")
    print("=" * 60)
    if summary.p0_added_record_hit_rate is not None:
        for k in sorted(summary.p0_added_record_hit_rate.keys()):
            val = summary.p0_added_record_hit_rate[k]
            doc_type_val = summary.hit_rate_doc_type.get(k, 0.0)
            print(f"  Top-{k}: doc_type={_pct(doc_type_val)}  doc_id(P0)={_pct(val)}  delta={_pct(val - doc_type_val)}")
    print(f"  Wrong cases (doc_type): {len(summary.wrong_cases)}")
    if doc_id_rechecks:
        found = sum(1 for r in doc_id_rechecks if r.doc_id_found)
        print(f"  Reclassified by doc_id: {found}/{len(doc_id_rechecks)}")


if __name__ == "__main__":
    main()
