#!/usr/bin/env python
"""Retrieval comparison CLI — compare retrieved evidence against golden expectations.

Batch 5A: mock mode only (synthetic retrieval results for testing tooling).
Batch 5B will add --retrieval-mode pipeline for real API comparison.

Usage:
    # Mock mode (default) — no real pipeline or API calls
    uv run python scripts/run_retrieval_comparison.py \
        --tickets data/eval/tickets_eval.csv \
        --golden data/eval/golden_expectations.csv \
        --out-json reports/retrieval/comparison_report.json \
        --out-md reports/retrieval/comparison_report.md
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from typing import Any, NoReturn

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


def die(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit with the given code."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare retrieved evidence against golden expectations.",
    )
    parser.add_argument(
        "--tickets",
        required=True,
        help="Path to tickets_eval.csv",
    )
    parser.add_argument(
        "--golden",
        required=True,
        help="Path to golden_expectations.csv",
    )
    parser.add_argument(
        "--out-json",
        required=True,
        help="Path for output JSON report",
    )
    parser.add_argument(
        "--out-md",
        required=True,
        help="Path for output Markdown report",
    )
    parser.add_argument(
        "--retrieval-mode",
        choices=["mock", "pipeline"],
        default="mock",
        help="Retrieval source: 'mock' (default) generates synthetic results for "
        "testing. 'pipeline' runs the real retrieval pipeline (5B).",
    )
    parser.add_argument(
        "--mock-seed",
        type=int,
        default=42,
        help="Random seed for mock retrieval results (default: 42)",
    )
    return parser.parse_args(argv)


def _generate_mock_retrieved_docs(
    case_id: str,
    expected_doc_types: frozenset[str],
    seed: int = 42,
) -> list[RetrievedDoc]:
    """Generate deterministic mock retrieval results for a case.

    Produces 10 synthetic RetrievedDoc entries. Expected doc_types are placed at
    ranks that vary by case_id hash, simulating different retrieval quality levels.

    Args:
        case_id: Case identifier (used for deterministic seeding).
        expected_doc_types: Set of doc types that should be considered relevant.
        seed: Base random seed for reproducibility.

    Returns:
        List of 10 RetrievedDoc entries.
    """
    case_hash = int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed + case_hash)

    all_doc_types = ["FAQ", "Policy", "Case"]
    doc_pool: list[tuple[str, str]] = []
    for dt in all_doc_types:
        for i in range(1, 21):
            doc_pool.append((dt, f"doc_{dt.lower()}_{i:04d}"))

    rng.shuffle(doc_pool)

    # Decide whether expected types land in top results (70% chance) or are buried
    expected_types = set(expected_doc_types) if expected_doc_types else set()
    results: list[RetrievedDoc] = []
    placed_expected: set[str] = set()

    for rank in range(1, 11):
        if expected_types and (rank <= 3 or rng.random() < 0.3):
            # Place an expected doc_type if not all have been placed
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

        # Pick from remaining pool
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

    # Sort by rank to ensure correct ordering
    results.sort(key=lambda d: d.rank)
    return results


def _generate_mock_comparison_cases(
    tickets_path: str,
    golden_path: str,
    seed: int = 42,
) -> list[RetrievalComparisonCase]:
    """Load eval data and generate mock retrieval comparison cases.

    Args:
        tickets_path: Path to tickets_eval.csv.
        golden_path: Path to golden_expectations.csv.
        seed: Random seed for mock results.

    Returns:
        List of RetrievalComparisonCase with mock retrieved docs.
    """
    tickets = load_tickets_eval(tickets_path)
    golden = load_golden_expectations(golden_path)

    cases: list[RetrievalComparisonCase] = []
    for case_id in sorted(tickets.keys()):
        if case_id not in golden:
            continue
        ticket = tickets[case_id]
        g = golden[case_id]

        retrieved = _generate_mock_retrieved_docs(case_id, g.expected_evidence_doc_types, seed)

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


def run_comparison(args: argparse.Namespace) -> None:
    """Load data, compute retrieval metrics, write reports."""
    if args.retrieval_mode == "pipeline":
        die("Pipeline retrieval mode not yet implemented (planned for Batch 5B)")

    cases = _generate_mock_comparison_cases(
        args.tickets, args.golden, seed=args.mock_seed
    )
    if not cases:
        die("No comparison cases generated — check tickets and golden files")

    summary = compute_retrieval_comparison_summary(cases)

    config: dict[str, Any] = {
        "retrieval_mode": args.retrieval_mode,
        "mock_seed": args.mock_seed,
    }

    write_json_report(
        summary,
        args.out_json,
        tickets_path=args.tickets,
        golden_path=args.golden,
        config=config,
    )
    print(f"JSON report written to {args.out_json}")

    write_markdown_report(
        summary,
        args.out_md,
        tickets_path=args.tickets,
        golden_path=args.golden,
        config=config,
    )
    print(f"Markdown report written to {args.out_md}")

    print(f"\nTotal cases: {summary.total_cases}")
    for k, rate in sorted(summary.hit_rate_doc_type.items()):
        print(f"  Top-{k} doc_type hit rate: {rate * 100:.1f}%")
    print(f"  MRR (doc_type): {summary.mrr_doc_type:.4f}")
    print(f"  Wrong cases: {len(summary.wrong_cases)}")


def main() -> None:
    """Entry point for the CLI."""
    args = parse_args()
    run_comparison(args)


if __name__ == "__main__":
    main()
