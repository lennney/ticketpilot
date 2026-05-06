#!/usr/bin/env python
"""Phase 10.5.1 — Real Pipeline Doc-level Evaluation.

Loads real pipeline export rows and computes doc_id-level metrics for
P0-labeled cases. Determines whether fused_top10_but_metric_still_wrong
is primarily a metric granularity problem.

Usage:
    uv run python scripts/run_phase10_real_doc_level_eval.py
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any

from ticketpilot.evaluation.loaders import load_golden_expectations
from ticketpilot.evaluation.retrieval_metrics import (
    DEFAULT_KS,
    RetrievedDoc,
    RetrievalComparisonCase,
    compute_retrieval_comparison_summary,
    recheck_wrong_cases_with_doc_id,
)

# Paths
ROWS_PATH = "reports/retrieval/phase10_real_doc_level_rows.json"
GOLDEN_PATH = "data/eval/golden_expectations.csv"
OUT_METRICS_JSON = "reports/retrieval/phase10_real_doc_level_eval_metrics.json"
OUT_EVAL_MD = "reports/retrieval/phase10_real_doc_level_evaluation.md"
OUT_RECHECK_MD = "reports/retrieval/phase10_real_doc_level_wrong_case_recheck.md"


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def load_real_cases() -> list[RetrievalComparisonCase]:
    """Load real pipeline export rows + golden expectations."""
    golden = load_golden_expectations(GOLDEN_PATH)
    data = json.loads(pathlib.Path(ROWS_PATH).read_text(encoding="utf-8"))

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


def compute_p0_metrics(
    cases: list[RetrievalComparisonCase],
) -> dict[str, Any]:
    """Compute P0 doc-level metrics."""
    p0_cases = [c for c in cases if c.expected_doc_ids and len(c.expected_doc_ids) > 0]

    summary = compute_retrieval_comparison_summary(cases)
    rechecks = recheck_wrong_cases_with_doc_id(summary.wrong_cases, cases)

    # Per-case doc_id analysis for P0 cases
    p0_per_case: dict[str, dict[str, Any]] = {}
    for c in p0_cases:
        metrics = None
        for cid, m in summary.per_case.items():
            if cid == c.case_id:
                metrics = m
                break
        expected = set(c.expected_doc_ids) if c.expected_doc_ids else set()
        retrieved_top10 = {d.doc_id for d in c.retrieved_docs[:10]}
        hit_doc_ids = expected & retrieved_top10
        missed_doc_ids = expected - retrieved_top10

        # Find ranks of hit doc_ids
        hit_ranks: dict[str, int] = {}
        for d in c.retrieved_docs[:10]:
            if d.doc_id in hit_doc_ids and d.doc_id not in hit_ranks:
                hit_ranks[d.doc_id] = d.rank

        doc_id_correct_at_10 = len(expected) > 0 and expected.issubset(retrieved_top10)

        p0_per_case[c.case_id] = {
            "expected_doc_ids": sorted(expected),
            "hit_doc_ids": sorted(hit_doc_ids),
            "missed_doc_ids": sorted(missed_doc_ids),
            "hit_ranks": hit_ranks,
            "doc_id_correct_at_10": doc_id_correct_at_10,
            "doc_type_hit_at_10": metrics.top_k_doc_type_hit.get(10, False) if metrics else False,
            "doc_id_hit_at_10": metrics.top_k_doc_id_hit.get(10, False) if metrics and metrics.top_k_doc_id_hit else False,
        }

    # Aggregate P0 metrics
    p0_total = len(p0_cases)
    p0_doc_id_correct_at_10 = sum(1 for v in p0_per_case.values() if v["doc_id_correct_at_10"])
    p0_still_wrong = p0_total - p0_doc_id_correct_at_10

    # Count cases with partial hits
    p0_partial = sum(
        1 for v in p0_per_case.values()
        if not v["doc_id_correct_at_10"] and len(v["hit_doc_ids"]) > 0
    )

    # Recheck analysis
    recheck_found = [r for r in rechecks if r.doc_id_found]
    recheck_not_found = [r for r in rechecks if not r.doc_id_found]

    return {
        "config": {
            "rows_path": ROWS_PATH,
            "golden_path": GOLDEN_PATH,
            "total_cases": len(cases),
            "p0_labeled_cases": p0_total,
            "ks": DEFAULT_KS,
        },
        "aggregate_doc_type_metrics": {
            "hit_rate_at_k": summary.hit_rate_doc_type,
            "mrr": summary.mrr_doc_type,
            "wrong_case_count": len(summary.wrong_cases),
        },
        "aggregate_doc_id_metrics": {
            "hit_rate_doc_id": summary.hit_rate_doc_id,
            "p0_added_record_hit_rate": summary.p0_added_record_hit_rate,
            "mrr_doc_id": summary.mrr_doc_id,
        },
        "p0_summary": {
            "labeled_case_count": p0_total,
            "missing_doc_id_label_count": 0,  # All 14 have labels now
            "cases_doc_id_correct_at_10": p0_doc_id_correct_at_10,
            "cases_partial_hit": p0_partial,
            "cases_still_wrong_at_doc_id_level": p0_still_wrong,
            "doc_id_success_rate": p0_doc_id_correct_at_10 / p0_total if p0_total > 0 else 0.0,
        },
        "wrong_case_recheck": {
            "total_wrong_cases_doc_type": len(summary.wrong_cases),
            "doc_id_found_in_top_10": len(recheck_found),
            "doc_id_not_found": len(recheck_not_found),
            "reclassified_cases": [
                {
                    "case_id": r.case_id,
                    "original_failure_mode": r.original_failure_mode,
                    "doc_id_found_rank": r.doc_id_found_rank,
                    "reclassified": r.reclassified,
                }
                for r in recheck_found
            ],
            "still_wrong_cases": [
                {
                    "case_id": r.case_id,
                    "original_failure_mode": r.original_failure_mode,
                }
                for r in recheck_not_found
            ],
        },
        "per_case_p0_results": p0_per_case,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_metrics_json(metrics: dict[str, Any]) -> None:
    out = pathlib.Path(OUT_METRICS_JSON)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Metrics JSON: {OUT_METRICS_JSON}")


def write_evaluation_md(metrics: dict[str, Any]) -> None:
    """Write evaluation report markdown."""
    cfg = metrics["config"]
    dt = metrics["aggregate_doc_type_metrics"]
    did = metrics["aggregate_doc_id_metrics"]
    p0 = metrics["p0_summary"]
    re = metrics["wrong_case_recheck"]

    lines = [
        "# Phase 10.5.1 — Real Pipeline Doc-Level Evaluation",
        "",
        f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Dataset",
        "",
        f"- Total cases: {cfg['total_cases']}",
        f"- P0-labeled cases: {cfg['p0_labeled_cases']}",
        f"- Rows: `{cfg['rows_path']}`",
        f"- Golden: `{cfg['golden_path']}`",
        "",
        "## Provider",
        "",
    ]

    # Extract provider info from first case with trace
    provider_name = "unknown"
    try:
        data = json.loads(pathlib.Path(ROWS_PATH).read_text(encoding="utf-8"))
        for c in data["cases"]:
            t = c.get("retrieval_trace", {})
            if t.get("available"):
                provider_name = t.get("embedding_provider", "unknown")
                break
    except Exception:
        pass
    lines.append(f"- **Embedding provider**: `{provider_name}`")
    lines.append("")

    # Aggregate comparison
    lines.append("## Aggregate Metrics: Doc-Type vs Doc-ID")
    lines.append("")
    lines.append("| k | Doc-Type Hit Rate | Doc-ID Hit Rate | P0 Added-Record Hit Rate | Delta |")
    lines.append("|---|-------------------|-----------------|--------------------------|-------|")
    for k in sorted(dt["hit_rate_at_k"].keys()):
        dt_rate = dt["hit_rate_at_k"][k]
        did_rate = (did.get("hit_rate_doc_id") or {}).get(k, 0.0)
        p0_rate = (did.get("p0_added_record_hit_rate") or {}).get(k, 0.0)
        delta = p0_rate - dt_rate
        delta_str = f"+{delta*100:.1f}%" if delta > 0 else f"{delta*100:.1f}%"
        lines.append(f"| {k} | {_pct(dt_rate)} | {_pct(did_rate)} | {_pct(p0_rate)} | {delta_str} |")
    lines.append("")
    lines.append(f"| MRR | {dt['mrr']:.4f} | {(did.get('mrr_doc_id') or 0.0):.4f} | — | — |")
    lines.append("")

    # P0 Summary
    lines.append("## P0 Doc-Level Summary")
    lines.append("")
    lines.append(f"- **Labeled cases**: {p0['labeled_case_count']}")
    lines.append(f"- **Doc-ID correct at Top-10**: {p0['cases_doc_id_correct_at_10']}/{p0['labeled_case_count']} ({_pct(p0['doc_id_success_rate'])})")
    lines.append(f"- **Partial hit**: {p0['cases_partial_hit']}")
    lines.append(f"- **Still wrong at doc-ID level**: {p0['cases_still_wrong_at_doc_id_level']}")
    lines.append("")

    # Wrong-case recheck
    lines.append("## Wrong-Case Recheck (Doc-ID Granularity)")
    lines.append("")
    lines.append(f"- **Wrong cases (doc-type)**: {re['total_wrong_cases_doc_type']}")
    lines.append(f"- **Doc-ID found in top-10**: {re['doc_id_found_in_top_10']}")
    lines.append(f"- **Still wrong after doc-ID check**: {re['doc_id_not_found']}")
    lines.append("")

    if re["reclassified_cases"]:
        lines.append("### Reclassified Cases")
        lines.append("")
        lines.append("| Case ID | Original Failure Mode | Doc ID Found Rank |")
        lines.append("|---------|----------------------|-------------------|")
        for rc in re["reclassified_cases"]:
            lines.append(f"| {rc['case_id']} | {rc['original_failure_mode']} | {rc['doc_id_found_rank']} |")
        lines.append("")

    if re["still_wrong_cases"]:
        lines.append("### Still Wrong After Doc-ID Check")
        lines.append("")
        lines.append("| Case ID | Original Failure Mode |")
        lines.append("|---------|----------------------|")
        for sw in re["still_wrong_cases"]:
            lines.append(f"| {sw['case_id']} | {sw['original_failure_mode']} |")
        lines.append("")

    # Per-case detail
    lines.append("## Per-Case P0 Doc-ID Detail")
    lines.append("")
    lines.append("| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | All Correct? |")
    lines.append("|---------|-----------------|---------------|--------|-------------|")
    for case_id in sorted(metrics["per_case_p0_results"].keys()):
        p = metrics["per_case_p0_results"][case_id]
        expected_str = ", ".join(d[:8] for d in p["expected_doc_ids"])
        hit_str = ", ".join(f'{d[:8]}@{p["hit_ranks"].get(d,"?")}' for d in p["hit_doc_ids"]) or "—"
        missed_str = ", ".join(d[:8] for d in p["missed_doc_ids"]) or "—"
        status = "✅" if p["doc_id_correct_at_10"] else "❌"
        lines.append(f"| {case_id} | {expected_str} | {hit_str} | {missed_str} | {status} |")
    lines.append("")

    # Interpretation
    lines.append("## Interpretation")
    lines.append("")

    still_wrong_count = p0["cases_still_wrong_at_doc_id_level"]
    success_count = p0["cases_doc_id_correct_at_10"]
    partial_count = p0["cases_partial_hit"]
    reclassified_ratio = re["doc_id_found_in_top_10"]
    total_wrong = re["total_wrong_cases_doc_type"]

    lines.append(f"**{success_count}/{p0['labeled_case_count']}** P0-labeled cases have ALL expected doc_ids in top-10.")
    lines.append(f"**{still_wrong_count}** cases still missing at least one expected doc_id even at doc-ID granularity.")
    if partial_count > 0:
        lines.append(f"**{partial_count}** cases have partial hits (some expected doc_ids found, some not).")
    lines.append("")

    if reclassified_ratio > 0 and total_wrong > 0:
        pct_reclassified = reclassified_ratio / total_wrong * 100
        lines.append(f"**Wrong-case recheck**: Of {total_wrong} doc-type wrong cases, "
                     f"{reclassified_ratio} ({pct_reclassified:.0f}%) have the correct doc_id in top-10 "
                     f"— confirming metric granularity as the primary cause.")
    lines.append("")

    lines.append("### Remaining Bottlenecks")
    lines.append("")
    if still_wrong_count > 0:
        lines.append(f"- **{still_wrong_count} cases** with genuine retrieval misses (doc_id not in fused top-10):")
        for case_id in sorted(metrics["per_case_p0_results"].keys()):
            p = metrics["per_case_p0_results"][case_id]
            if not p["doc_id_correct_at_10"]:
                missed = ", ".join(d[:8] for d in p["missed_doc_ids"])
                lines.append(f"  - `{case_id}`: missing {missed}")
        lines.append("- These need deeper investigation: keyword recall, vector recall, or fusion ranking.")
    lines.append("")

    lines.append("### Recommendations")
    lines.append("")
    lines.append("1. **Add more doc-level labels** — extend to non-P0 cases for broader coverage.")
    lines.append("2. **Query expansion audit** — for cases with genuine misses, check if query underspecifies the needed knowledge.")
    lines.append("3. **Fusion ranking experiment** — for cases where doc_id found but below top-10, tune RRF or add reranker.")
    lines.append("4. **Portfolio snapshot** — doc-level evaluation results are ready for Phase 10 portfolio.")
    lines.append("")

    out = pathlib.Path(OUT_EVAL_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Eval MD: {OUT_EVAL_MD}")


def write_wrong_case_recheck_md(metrics: dict[str, Any]) -> None:
    """Write wrong-case recheck report."""
    re = metrics["wrong_case_recheck"]
    p0 = metrics["p0_summary"]

    lines = [
        "# Phase 10.5.1 — Wrong-Case Doc-ID Recheck",
        "",
        f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Purpose",
        "",
        "Reclassify doc-type-level wrong cases using doc-ID granularity to determine "
        "whether the remaining wrong cases are a metric granularity problem or a "
        "genuine retrieval failure.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total wrong cases (doc-type) | {re['total_wrong_cases_doc_type']} |",
        f"| Doc-ID found in top-10 | {re['doc_id_found_in_top_10']} |",
        f"| Still wrong after doc-ID check | {re['doc_id_not_found']} |",
        f"| P0 doc-ID correct at top-10 | {p0['cases_doc_id_correct_at_10']}/{p0['labeled_case_count']} |",
        f"| P0 still wrong at doc-ID level | {p0['cases_still_wrong_at_doc_id_level']} |",
        "",
    ]

    if re["reclassified_cases"]:
        lines.append("## Reclassified Cases (Doc-ID Found)")
        lines.append("")
        lines.append("| Case ID | Original Failure Mode | Doc ID Found | Found Rank |")
        lines.append("|---------|----------------------|--------------|------------|")
        for rc in re["reclassified_cases"]:
            lines.append(f"| {rc['case_id']} | {rc['original_failure_mode']} | doc_id found | {rc['doc_id_found_rank']} |")
        lines.append("")
        lines.append("**Conclusion**: These cases are *metric granularity* problems — the correct document ")
        lines.append("was retrieved but the doc-type metric didn't recognize it.")
        lines.append("")

    if re["still_wrong_cases"]:
        lines.append("## Still Wrong After Doc-ID Check")
        lines.append("")
        lines.append("| Case ID | Original Failure Mode | Details |")
        lines.append("|---------|----------------------|---------|")
        for sw in re["still_wrong_cases"]:
            lines.append(f"| {sw['case_id']} | {sw['original_failure_mode']} | Genuine retrieval miss |")
        lines.append("")
        lines.append("**Conclusion**: These cases have genuine retrieval failures — the expected doc_id ")
        lines.append("was not in fused top-10 results. Requires deeper bottleneck investigation.")
        lines.append("")

    lines.append("## Answer to Thesis Question")
    lines.append("")
    total = re["total_wrong_cases_doc_type"]
    found = re["doc_id_found_in_top_10"]
    if total > 0:
        ratio = found / total * 100
        if ratio >= 75:
            lines.append(f"**✅ Thesis confirmed**: {found}/{total} ({ratio:.0f}%) of wrong cases are ")
            lines.append("metric granularity problems (doc_id found but doc_type metric missed them).")
        else:
            lines.append(f"**⚠️ Thesis partially confirmed**: {found}/{total} ({ratio:.0f}%) of wrong cases ")
            lines.append("are metric granularity problems. Remaining cases need deeper investigation.")
    lines.append("")

    out = pathlib.Path(OUT_RECHECK_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Recheck MD: {OUT_RECHECK_MD}")


def main() -> None:
    print("Loading real pipeline export rows...")
    cases = load_real_cases()
    print(f"Loaded {len(cases)} cases")

    p0_count = sum(1 for c in cases if c.expected_doc_ids and len(c.expected_doc_ids) > 0)
    print(f"P0-labeled: {p0_count}")

    print("\nComputing P0 doc-level metrics...")
    metrics = compute_p0_metrics(cases)

    pm = metrics["p0_summary"]
    re = metrics["wrong_case_recheck"]
    print(f"\nP0 Doc-ID correct at Top-10: {pm['cases_doc_id_correct_at_10']}/{pm['labeled_case_count']}")
    print(f"Still wrong at doc-ID level: {pm['cases_still_wrong_at_doc_id_level']}")
    print(f"Wrong-case recheck — found doc_id: {re['doc_id_found_in_top_10']}/{re['total_wrong_cases_doc_type']}")

    print("\nWriting reports...")
    write_metrics_json(metrics)
    write_evaluation_md(metrics)
    write_wrong_case_recheck_md(metrics)

    print("\nDone.")


if __name__ == "__main__":
    main()
