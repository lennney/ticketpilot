#!/usr/bin/env python
"""Retrieval comparison CLI — compare retrieved evidence against golden expectations.

Modes:
    mock      — synthetic retrieval results (testing tooling, no external deps)
    export    — run real pipeline, save retrieval rows to JSON for later comparison
    compare   — compare two pre-exported row files (fake vs real)

Usage:
    # Mock mode (default)
    uv run python scripts/run_retrieval_comparison.py \\
        --tickets data/eval/tickets_eval.csv \\
        --golden data/eval/golden_expectations.csv \\
        --out-json reports/retrieval/comparison_report.json \\
        --out-md reports/retrieval/comparison_report.md

    # Export mode — run pipeline, save rows
    uv run python scripts/run_retrieval_comparison.py \\
        --mode export \\
        --tickets data/eval/tickets_eval.csv \\
        --golden data/eval/golden_expectations.csv \\
        --out-rows reports/retrieval/fake_retrieval_rows.json

    # Compare mode — compare two pre-exported row files
    uv run python scripts/run_retrieval_comparison.py \\
        --mode compare \\
        --fake-run-json reports/retrieval/fake_retrieval_rows.json \\
        --real-run-json reports/retrieval/real_retrieval_rows.json \\
        --golden data/eval/golden_expectations.csv \\
        --out-json reports/retrieval/fake_vs_real_comparison.json \\
        --out-md reports/retrieval/fake_vs_real_comparison.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
from datetime import datetime, timezone
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
    sub = parser.add_subparsers(dest="mode", help="Operation mode")

    # --- mock mode (default for backwards compat) ---
    mock = sub.add_parser("mock", help="Synthetic retrieval results (testing)")
    mock.add_argument("--tickets", required=True)
    mock.add_argument("--golden", required=True)
    mock.add_argument("--out-json", required=True)
    mock.add_argument("--out-md", required=True)
    mock.add_argument("--mock-seed", type=int, default=42)

    # --- export mode (run pipeline, save rows) ---
    export = sub.add_parser("export", help="Run pipeline and export retrieval rows")
    export.add_argument("--tickets", required=True)
    export.add_argument("--golden", required=True)
    export.add_argument("--out-rows", required=True)

    # --- compare mode (compare two row files) ---
    compare = sub.add_parser("compare", help="Compare two pre-exported row files")
    compare.add_argument("--fake-run-json", required=True)
    compare.add_argument("--real-run-json", required=True)
    compare.add_argument("--golden", required=True)
    compare.add_argument("--out-json", required=True)
    compare.add_argument("--out-md", required=True)
    compare.add_argument("--top-k", type=str, default="1,3,5,10")

    args = parser.parse_args(argv)
    if args.mode is None:
        # Default to mock mode if no subcommand given (backwards compat with old CLI)
        args.mode = "mock"
        # Re-parse with mock defaults
        return _parse_legacy_args(argv)
    return args


def _parse_legacy_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse legacy flat args (backwards compat with Batch 5A CLI)."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets", required=True)
    parser.add_argument("--golden", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--mock-seed", type=int, default=42)
    ns = parser.parse_args(argv)
    ns.mode = "mock"
    return ns


# ---------------------------------------------------------------------------
# Mock mode (Batch 5A)
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


def _generate_mock_comparison_cases(
    tickets_path: str,
    golden_path: str,
    seed: int = 42,
) -> list[RetrievalComparisonCase]:
    """Load eval data and generate mock retrieval comparison cases."""
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


def _run_mock_mode(args: argparse.Namespace) -> None:
    cases = _generate_mock_comparison_cases(args.tickets, args.golden, seed=args.mock_seed)
    if not cases:
        die("No comparison cases generated")
    summary = compute_retrieval_comparison_summary(cases)
    config = {"retrieval_mode": "mock", "mock_seed": args.mock_seed}
    write_json_report(summary, args.out_json, tickets_path=args.tickets, golden_path=args.golden, config=config)
    print(f"JSON report written to {args.out_json}")
    write_markdown_report(summary, args.out_md, tickets_path=args.tickets, golden_path=args.golden, config=config)
    print(f"Markdown report written to {args.out_md}")
    print(f"\nTotal cases: {summary.total_cases}")
    for k, rate in sorted(summary.hit_rate_doc_type.items()):
        print(f"  Top-{k} doc_type hit rate: {rate * 100:.1f}%")
    print(f"  MRR (doc_type): {summary.mrr_doc_type:.4f}")
    print(f"  Wrong cases: {len(summary.wrong_cases)}")


# ---------------------------------------------------------------------------
# Export mode (Batch 5B) — run pipeline, save rows
# ---------------------------------------------------------------------------


def _run_pipeline_export(args: argparse.Namespace) -> None:
    """Run the pipeline for each ticket and export retrieval rows as JSON."""
    from ticketpilot.pipeline import intake_risk_pipeline
    from ticketpilot.retrieval.embedding_config import load_embedding_config_from_env
    from ticketpilot.retrieval.providers import create_embedding_provider
    from ticketpilot.schema.ticket import RawTicket

    # Build embedding provider from env config (uses FakeEmbeddingProvider by default)
    try:
        config = load_embedding_config_from_env()
        embedding_provider = create_embedding_provider(config)
    except Exception:
        embedding_provider = None

    tickets = load_tickets_eval(args.tickets)
    golden = load_golden_expectations(args.golden)

    rows: list[dict[str, Any]] = []
    for case_id in sorted(tickets.keys()):
        if case_id not in golden:
            continue
        ticket = tickets[case_id]
        g = golden[case_id]

        raw = RawTicket(
            original_text=ticket.original_text,
            submitted_at=datetime.utcnow(),
            customer_id=ticket.customer_id,
        )
        output = intake_risk_pipeline(raw, embedding_provider=embedding_provider)

        docs = []
        for i, cand in enumerate(output.evidence_candidates, start=1):
            docs.append({
                "chunk_id": str(cand.chunk_id),
                "doc_id": str(cand.doc_id),
                "doc_type": cand.doc_type.value if hasattr(cand.doc_type, "value") else str(cand.doc_type),
                "rank": i,
                "score": cand.score,
            })

        trace_info: dict[str, Any] = {"available": False}
        if output.retrieval_trace is not None:
            t = output.retrieval_trace
            trace_info = {
                "available": True,
                "keyword_count": len(t.keyword_results),
                "vector_count": len(t.vector_results),
                "fused_count": len(t.fused_results),
                "total_latency_ms": t.total_latency_ms,
                "embedding_provider": t.embedding_provider,
                "keyword_results": [
                    {
                        "chunk_id": str(r.chunk_id),
                        "doc_id": str(r.doc_id),
                        "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                        "score": r.score,
                        "rank": r.rank,
                        "search_method": r.search_method,
                    }
                    for r in t.keyword_results
                ],
                "vector_results": [
                    {
                        "chunk_id": str(r.chunk_id),
                        "doc_id": str(r.doc_id),
                        "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                        "score": r.score,
                        "rank": r.rank,
                        "embedding_provider": r.embedding_provider,
                    }
                    for r in t.vector_results
                ],
                "fused_results": [
                    {
                        "chunk_id": str(r.chunk_id),
                        "doc_id": str(r.doc_id),
                        "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                        "rrf_score": r.rrf_score,
                        "keyword_rank": r.keyword_rank,
                        "keyword_contribution": r.keyword_contribution,
                        "vector_rank": r.vector_rank,
                        "vector_contribution": r.vector_contribution,
                        "sources": r.sources,
                    }
                    for r in t.fused_results
                ],
                "final_evidence_ids": [str(eid) for eid in t.final_evidence_ids],
            }

        rows.append({
            "case_id": case_id,
            "query": ticket.original_text,
            "retrieved_docs": docs,
            "expected_doc_types": sorted(g.expected_evidence_doc_types),
            "expected_doc_ids": sorted(g.expected_relevant_doc_ids) if g.expected_relevant_doc_ids else [],
            "retrieval_trace": trace_info,
        })

    out = pathlib.Path(args.out_rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": len(rows),
            "cases": rows,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Exported {len(rows)} retrieval rows to {args.out_rows}")


# ---------------------------------------------------------------------------
# Compare mode (Batch 5B) — compare two pre-exported row files
# ---------------------------------------------------------------------------


def _load_row_cases(
    rows_path: str,
    golden_path: str,
) -> list[RetrievalComparisonCase]:
    """Load pre-exported retrieval rows and golden expectations into comparison cases."""
    golden = load_golden_expectations(golden_path)
    data = json.loads(pathlib.Path(rows_path).read_text(encoding="utf-8"))

    cases: list[RetrievalComparisonCase] = []
    for item in data["cases"]:
        case_id = item["case_id"]
        g = golden.get(case_id)
        if g is None:
            continue
        docs = [
            RetrievedDoc(
                doc_id=d["doc_id"],
                doc_type=d["doc_type"],
                rank=d["rank"],
                score=d["score"],
            )
            for d in item["retrieved_docs"]
        ]
        cases.append(
            RetrievalComparisonCase(
                case_id=case_id,
                query=item.get("query", ""),
                retrieved_docs=docs,
                expected_doc_types=frozenset(item["expected_doc_types"]),
                expected_doc_ids=frozenset(item["expected_doc_ids"]) if item.get("expected_doc_ids") else None,
            )
        )
    return cases


def _serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, frozenset):
        return sorted(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {str(k): _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


def _run_compare_mode(args: argparse.Namespace) -> None:
    ks = [int(k.strip()) for k in args.top_k.split(",") if k.strip()]

    fake_cases = _load_row_cases(args.fake_run_json, args.golden)
    real_cases = _load_row_cases(args.real_run_json, args.golden)

    if not fake_cases or not real_cases:
        die("One or both row files contain no valid cases")

    fake_summary = compute_retrieval_comparison_summary(fake_cases, ks=ks)
    real_summary = compute_retrieval_comparison_summary(real_cases, ks=ks)

    # Build comparison report
    generated_at = datetime.now(timezone.utc)
    lines: list[str] = [
        "# Fake vs Real Retrieval Comparison",
        "",
        f"*Generated at {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Dataset",
        "",
        f"- Total cases: {fake_summary.total_cases}",
        f"- Golden expectations: `{args.golden}`",
        "",
    ]

    # Load metadata from row files
    fake_data = json.loads(pathlib.Path(args.fake_run_json).read_text(encoding="utf-8"))
    real_data = json.loads(pathlib.Path(args.real_run_json).read_text(encoding="utf-8"))

    lines.append("## Providers")
    lines.append("")
    lines.append("| Metric | Fake | Real |")
    lines.append("|--------|------|------|")
    lines.append(f"| File | `{args.fake_run_json}` | `{args.real_run_json}` |")
    lines.append(f"| Generated | {fake_data.get('generated_at', '?')} | {real_data.get('generated_at', '?')} |")

    # Detailed per-case row counts
    fake_rows = len(fake_data.get("cases", []))
    real_rows = len(real_data.get("cases", []))
    lines.append(f"| Cases | {fake_rows} | {real_rows} |")

    # Try to extract provider metadata from trace
    fake_providers: set[str] = set()
    real_providers: set[str] = set()
    for c in fake_data.get("cases", []):
        t = c.get("retrieval_trace", {})
        ep = t.get("embedding_provider")
        if ep:
            fake_providers.add(str(ep))
    for c in real_data.get("cases", []):
        t = c.get("retrieval_trace", {})
        ep = t.get("embedding_provider")
        if ep:
            real_providers.add(str(ep))
    lines.append(f"| Embedding provider | {', '.join(sorted(fake_providers)) or '?'} | {', '.join(sorted(real_providers)) or '?'} |")
    lines.append("")

    # Aggregate metrics comparison table
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append("### Top-K Doc Type Hit Rate")
    lines.append("")
    lines.append("| k | Fake | Real | Delta |")
    lines.append("|---|------|------|-------|")
    for k in ks:
        f_rate = fake_summary.hit_rate_doc_type.get(k, 0.0)
        r_rate = real_summary.hit_rate_doc_type.get(k, 0.0)
        delta = r_rate - f_rate
        delta_str = f"+{delta*100:.1f}%" if delta > 0 else f"{delta*100:.1f}%"
        lines.append(f"| {k} | {f_rate*100:.1f}% | {r_rate*100:.1f}% | {delta_str} |")
    lines.append("")

    lines.append("### Mean Reciprocal Rank")
    lines.append("")
    lines.append("| Metric | Fake | Real | Delta |")
    lines.append("|--------|------|------|-------|")
    lines.append(f"| MRR (doc_type) | {fake_summary.mrr_doc_type:.4f} | {real_summary.mrr_doc_type:.4f} | {real_summary.mrr_doc_type - fake_summary.mrr_doc_type:+.4f} |")
    if fake_summary.mrr_doc_id is not None or real_summary.mrr_doc_id is not None:
        f_mrr_id = fake_summary.mrr_doc_id or 0.0
        r_mrr_id = real_summary.mrr_doc_id or 0.0
        lines.append(f"| MRR (doc_id) | {f_mrr_id:.4f} | {r_mrr_id:.4f} | {r_mrr_id - f_mrr_id:+.4f} |")
    else:
        lines.append("| MRR (doc_id) | N/A | N/A | N/A — golden file does not include doc-level labels |")
    lines.append("")

    # Wrong cases
    lines.append("## Wrong Cases")
    lines.append("")
    lines.append("| Metric | Fake | Real |")
    lines.append("|--------|------|------|")
    lines.append(f"| Wrong cases | {len(fake_summary.wrong_cases)} | {len(real_summary.wrong_cases)} |")

    if fake_summary.wrong_cases or real_summary.wrong_cases:
        lines.append("")
        lines.append("### Failure Mode Distribution")
        lines.append("")
        f_modes: dict[str, int] = {}
        r_modes: dict[str, int] = {}
        for w in fake_summary.wrong_cases:
            f_modes[w.failure_mode] = f_modes.get(w.failure_mode, 0) + 1
        for w in real_summary.wrong_cases:
            r_modes[w.failure_mode] = r_modes.get(w.failure_mode, 0) + 1
        all_modes = sorted(set(list(f_modes.keys()) + list(r_modes.keys())))
        lines.append("| Failure Mode | Fake | Real |")
        lines.append("|--------------|------|------|")
        for mode in all_modes:
            lines.append(f"| {mode} | {f_modes.get(mode, 0)} | {r_modes.get(mode, 0)} |")
        lines.append("")

    # Doc ID note
    lines.append("## Limitations")
    lines.append("")
    lines.append("doc_id Recall@K is not available because the current golden file ")
    lines.append("does not include doc-level labels (`expected_relevant_doc_ids`). ")
    lines.append("This metric will be available once doc-level golden labels are added.")
    lines.append("")

    md_content = "\n".join(lines)

    # Write reports
    out_json = pathlib.Path(args.out_json)
    out_md = pathlib.Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    # Build JSON report
    comparison_data = {
        "generated_at": generated_at.isoformat(),
        "config": {"top_k": ks},
        "golden_path": args.golden,
        "fake": {
            "rows_path": args.fake_run_json,
            "total_cases": fake_summary.total_cases,
            "hit_rate_doc_type": fake_summary.hit_rate_doc_type,
            "mrr_doc_type": fake_summary.mrr_doc_type,
            "wrong_case_count": len(fake_summary.wrong_cases),
        },
        "real": {
            "rows_path": args.real_run_json,
            "total_cases": real_summary.total_cases,
            "hit_rate_doc_type": real_summary.hit_rate_doc_type,
            "mrr_doc_type": real_summary.mrr_doc_type,
            "wrong_case_count": len(real_summary.wrong_cases),
        },
        "delta": {
            "hit_rate_doc_type": {
                str(k): round(real_summary.hit_rate_doc_type.get(k, 0.0) - fake_summary.hit_rate_doc_type.get(k, 0.0), 4)
                for k in ks
            },
            "mrr_doc_type": round(real_summary.mrr_doc_type - fake_summary.mrr_doc_type, 4),
        },
        "wrong_cases_fake": [
            {"case_id": w.case_id, "failure_mode": w.failure_mode, "details": w.details}
            for w in fake_summary.wrong_cases
        ],
        "wrong_cases_real": [
            {"case_id": w.case_id, "failure_mode": w.failure_mode, "details": w.details}
            for w in real_summary.wrong_cases
        ],
    }
    if fake_summary.hit_rate_doc_id is not None or real_summary.hit_rate_doc_id is not None:
        comparison_data["fake"]["hit_rate_doc_id"] = fake_summary.hit_rate_doc_id
        comparison_data["real"]["hit_rate_doc_id"] = real_summary.hit_rate_doc_id
        comparison_data["fake"]["mrr_doc_id"] = fake_summary.mrr_doc_id
        comparison_data["real"]["mrr_doc_id"] = real_summary.mrr_doc_id

    out_json.write_text(
        json.dumps(_serialize_for_json(comparison_data), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    out_md.write_text(md_content, encoding="utf-8")

    print(f"JSON report written to {args.out_json}")
    print(f"Markdown report written to {args.out_md}")
    print("\nTop-K Doc Type Hit Rate:")
    for k in ks:
        f_rate = fake_summary.hit_rate_doc_type.get(k, 0.0)
        r_rate = real_summary.hit_rate_doc_type.get(k, 0.0)
        delta = r_rate - f_rate
        print(f"  Top-{k}: Fake={f_rate*100:.1f}%  Real={r_rate*100:.1f}%  Delta={delta:+.1%}")
    print(f"  MRR (doc_type): Fake={fake_summary.mrr_doc_type:.4f}  Real={real_summary.mrr_doc_type:.4f}")
    print(f"  Wrong cases: Fake={len(fake_summary.wrong_cases)}  Real={len(real_summary.wrong_cases)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    if args.mode == "mock":
        _run_mock_mode(args)
    elif args.mode == "export":
        _run_pipeline_export(args)
    elif args.mode == "compare":
        _run_compare_mode(args)
    else:
        die(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
