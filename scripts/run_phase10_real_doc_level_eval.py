#!/usr/bin/env python
"""Phase 10.7.5 — Full Real Pipeline Doc-level Evaluation.

Loads real pipeline export rows and computes doc_id-level metrics for
all labeled cases. Determines whether fused_top10_but_metric_still_wrong
is primarily a metric granularity problem across the full dataset.

Modes:
    p0 (default) — P0-only subset, original paths
    full — full 86-labeled-case dataset, phase10_full_real_* paths

Usage:
    uv run python scripts/run_phase10_real_doc_level_eval.py [p0|full]
"""

from __future__ import annotations

import json
import pathlib
import sys
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


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------

MODE = (sys.argv[1] if len(sys.argv) > 1 else "p0").strip().lower()
if MODE not in ("p0", "full"):
    print(f"Error: unknown mode '{MODE}'. Use 'p0' or 'full'.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GOLDEN_PATH = "data/eval/golden_expectations.csv"

if MODE == "full":
    ROWS_PATH = "reports/retrieval/phase10_full_real_doc_level_rows.json"
    OUT_METRICS_JSON = "reports/retrieval/phase10_full_real_doc_level_eval_metrics.json"
    OUT_EVAL_MD = "reports/retrieval/phase10_full_real_doc_level_evaluation.md"
    OUT_RECHECK_MD = "reports/retrieval/phase10_full_real_doc_level_wrong_case_recheck.md"
    OUT_MISSES_MD = "reports/retrieval/phase10_full_real_doc_level_remaining_misses.md"
else:
    ROWS_PATH = "reports/retrieval/phase10_real_doc_level_rows.json"
    OUT_METRICS_JSON = "reports/retrieval/phase10_real_doc_level_eval_metrics.json"
    OUT_EVAL_MD = "reports/retrieval/phase10_real_doc_level_evaluation.md"
    OUT_RECHECK_MD = "reports/retrieval/phase10_real_doc_level_wrong_case_recheck.md"
    OUT_MISSES_MD = None  # P0 mode doesn't generate remaining misses report


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


def compute_metrics(
    cases: list[RetrievalComparisonCase],
) -> dict[str, Any]:
    """Compute doc-level metrics for all cases."""
    labeled_cases = [c for c in cases if c.expected_doc_ids and len(c.expected_doc_ids) > 0]
    unlabeled_cases = [c for c in cases if not (c.expected_doc_ids and len(c.expected_doc_ids) > 0)]

    summary = compute_retrieval_comparison_summary(cases)
    rechecks = recheck_wrong_cases_with_doc_id(summary.wrong_cases, cases)

    # Per-case doc_id analysis for labeled cases
    per_case: dict[str, dict[str, Any]] = {}
    for c in labeled_cases:
        metrics = None
        for cid, m in summary.per_case.items():
            if cid == c.case_id:
                metrics = m
                break
        expected = set(c.expected_doc_ids) if c.expected_doc_ids else set()
        retrieved_top10 = {d.doc_id for d in c.retrieved_docs[:10]}
        hit_doc_ids = expected & retrieved_top10
        missed_doc_ids = expected - retrieved_top10

        hit_ranks: dict[str, int] = {}
        for d in c.retrieved_docs[:10]:
            if d.doc_id in hit_doc_ids and d.doc_id not in hit_ranks:
                hit_ranks[d.doc_id] = d.rank

        doc_id_correct_at_10 = len(expected) > 0 and expected.issubset(retrieved_top10)

        per_case[c.case_id] = {
            "expected_doc_ids": sorted(expected),
            "hit_doc_ids": sorted(hit_doc_ids),
            "missed_doc_ids": sorted(missed_doc_ids),
            "hit_ranks": hit_ranks,
            "doc_id_correct_at_10": doc_id_correct_at_10,
            "doc_type_hit_at_10": metrics.top_k_doc_type_hit.get(10, False) if metrics else False,
            "doc_id_hit_at_10": metrics.top_k_doc_id_hit.get(10, False) if metrics and metrics.top_k_doc_id_hit else False,
        }

    # Aggregate
    labeled_total = len(labeled_cases)
    unlabeled_total = len(unlabeled_cases)
    doc_id_correct_at_10 = sum(1 for v in per_case.values() if v["doc_id_correct_at_10"])
    partial_hit = sum(1 for v in per_case.values()
                      if not v["doc_id_correct_at_10"] and len(v["hit_doc_ids"]) > 0)
    still_wrong = labeled_total - doc_id_correct_at_10

    recheck_found = [r for r in rechecks if r.doc_id_found]
    recheck_not_found = [r for r in rechecks if not r.doc_id_found]

    # Check for invalid doc_ids in golden
    invalid_doc_ids = 0
    for c in labeled_cases:
        if c.expected_doc_ids:
            for did in c.expected_doc_ids:
                # Check if doc_id looks valid (is a UUID or known format)
                if not did or len(did) < 10:
                    invalid_doc_ids += 1

    return {
        "config": {
            "rows_path": ROWS_PATH,
            "golden_path": GOLDEN_PATH,
            "mode": MODE,
            "total_cases": len(cases),
            "labeled_cases": labeled_total,
            "unlabeled_cases": unlabeled_total,
            "ks": DEFAULT_KS,
        },
        "provider": _extract_provider_info(),
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
        "doc_id_summary": {
            "labeled_case_count": labeled_total,
            "unlabeled_case_count": unlabeled_total,
            "cases_doc_id_correct_at_10": doc_id_correct_at_10,
            "cases_partial_hit": partial_hit,
            "cases_still_wrong_at_doc_id_level": still_wrong,
            "doc_id_success_rate": doc_id_correct_at_10 / labeled_total if labeled_total > 0 else 0.0,
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
        "per_case_results": per_case,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_provider_info() -> dict[str, Any]:
    """Extract provider identity from export rows."""
    try:
        data = json.loads(pathlib.Path(ROWS_PATH).read_text(encoding="utf-8"))
        for c in data["cases"]:
            t = c.get("retrieval_trace", {})
            if t.get("available"):
                return {
                    "embedding_provider": t.get("embedding_provider", "unknown"),
                    "keyword_count": t.get("keyword_count", 0),
                    "vector_count": t.get("vector_count", 0),
                    "fused_count": t.get("fused_count", 0),
                }
    except Exception:
        pass
    return {"embedding_provider": "unknown"}


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
    ds = metrics["doc_id_summary"]
    re = metrics["wrong_case_recheck"]
    prov = metrics["provider"]

    phase_label = "Phase 10.7.5" if MODE == "full" else "Phase 10.5.1"

    lines = [
        f"# {phase_label} — Real Pipeline Doc-Level Evaluation",
        "",
        f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        f"*Mode: {MODE}*",
        "",
        "## Dataset",
        "",
        f"- Total cases: {cfg['total_cases']}",
        f"- Labeled cases: {cfg['labeled_cases']}",
        f"- Unlabeled cases: {cfg['unlabeled_cases']}",
        f"- Rows: `{cfg['rows_path']}`",
        f"- Golden: `{cfg['golden_path']}`",
        "",
        "## Provider",
        "",
        f"- **Embedding provider**: `{prov.get('embedding_provider', 'unknown')}`",
        "",
    ]

    # Aggregate comparison
    lines.append("## Aggregate Metrics: Doc-Type vs Doc-ID")
    lines.append("")
    lines.append("| k | Doc-Type Hit Rate | Doc-ID Hit Rate | Delta |")
    lines.append("|---|-------------------|-----------------|-------|")
    for k in sorted(dt["hit_rate_at_k"].keys()):
        dt_rate = dt["hit_rate_at_k"][k]
        did_rate = (did.get("hit_rate_doc_id") or {}).get(k, 0.0)
        delta = did_rate - dt_rate
        delta_str = f"+{delta*100:.1f}%" if delta > 0 else f"{delta*100:.1f}%"
        lines.append(f"| {k} | {_pct(dt_rate)} | {_pct(did_rate)} | {delta_str} |")
    lines.append("")
    lines.append(f"| MRR | {dt['mrr']:.4f} | {(did.get('mrr_doc_id') or 0.0):.4f} | — |")
    lines.append("")

    # Doc-ID Summary
    lines.append("## Doc-ID Level Summary")
    lines.append("")
    lines.append(f"- **Labeled cases**: {ds['labeled_case_count']}")
    lines.append(f"- **Unlabeled cases**: {ds['unlabeled_case_count']}")
    lines.append(f"- **Doc-ID correct at Top-10**: {ds['cases_doc_id_correct_at_10']}/{ds['labeled_case_count']} ({_pct(ds['doc_id_success_rate'])})")
    lines.append(f"- **Partial hit**: {ds['cases_partial_hit']}")
    lines.append(f"- **Still wrong at doc-ID level**: {ds['cases_still_wrong_at_doc_id_level']}")
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

    # Per-case detail (show top-N cases to keep report readable)
    lines.append("## Per-Case Doc-ID Detail")
    lines.append("")
    lines.append("| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | All Correct? |")
    lines.append("|---------|-----------------|---------------|--------|-------------|")
    for case_id in sorted(metrics["per_case_results"].keys()):
        p = metrics["per_case_results"][case_id]
        expected_str = ", ".join(d[:8] for d in p["expected_doc_ids"])
        hit_str = ", ".join(f'{d[:8]}@{p["hit_ranks"].get(d,"?")}' for d in p["hit_doc_ids"]) or "—"
        missed_str = ", ".join(d[:8] for d in p["missed_doc_ids"]) or "—"
        status = "✅" if p["doc_id_correct_at_10"] else ( "⚠️ partial" if len(p["hit_doc_ids"]) > 0 else "❌" )
        lines.append(f"| {case_id} | {expected_str} | {hit_str} | {missed_str} | {status} |")
    lines.append("")

    # Interpretation
    lines.append("## Interpretation")
    lines.append("")

    still_wrong_count = ds["cases_still_wrong_at_doc_id_level"]
    success_count = ds["cases_doc_id_correct_at_10"]
    partial_count = ds["cases_partial_hit"]
    reclassified_count = re["doc_id_found_in_top_10"]
    total_wrong = re["total_wrong_cases_doc_type"]

    lines.append(f"**{success_count}/{ds['labeled_case_count']}** labeled cases have ALL expected doc_ids in top-10.")
    lines.append(f"**{still_wrong_count}** cases still missing at least one expected doc_id at doc-ID granularity.")
    if partial_count > 0:
        lines.append(f"**{partial_count}** cases have partial hits (some expected doc_ids found, some not).")
    lines.append("")

    if reclassified_count > 0 and total_wrong > 0:
        pct_reclassified = reclassified_count / total_wrong * 100
        lines.append(f"**Wrong-case recheck**: Of {total_wrong} doc-type wrong cases, "
                     f"{reclassified_count} ({pct_reclassified:.0f}%) have the correct doc_id in top-10 "
                     f"— confirming metric granularity as the primary cause.")
        lines.append("")
        if pct_reclassified >= 75:
            lines.append("**✅ Thesis confirmed**: The majority of wrong cases are metric granularity problems.")
        else:
            lines.append("**⚠️ Thesis partially confirmed**: Some wrong cases are metric granularity, "
                        "but a significant minority have genuine retrieval failures.")
    lines.append("")

    lines.append("### Remaining Bottlenecks")
    lines.append("")
    if still_wrong_count > 0:
        lines.append(f"- **{still_wrong_count} cases** with genuine retrieval misses (doc_id not in fused top-10):")
        for case_id in sorted(metrics["per_case_results"].keys()):
            p = metrics["per_case_results"][case_id]
            if not p["doc_id_correct_at_10"]:
                missed = ", ".join(d[:8] for d in p["missed_doc_ids"])
                rank_info = ""
                if len(p["hit_doc_ids"]) > 0:
                    rank_info += " (partial: some found)"
                lines.append(f"  - `{case_id}`: missing {missed}{rank_info}")
        lines.append("")
        lines.append("Possible causes: query underspecification (query expansion), RRF dual-source bias (fusion tuning), "
                     "or knowledge-record-term mismatch (keyword gap).")

    if ds["unlabeled_case_count"] > 0:
        lines.append("")
        lines.append(f"- **{ds['unlabeled_case_count']} unlabeled cases** — cannot be evaluated at doc-ID granularity. "
                     "See manual review report for details.")

    lines.append("")

    # Recommendations
    lines.append("### Recommendations")
    lines.append("")
    if MODE == "full":
        lines.append("1. **Archive Phase 10** — metric granularity thesis confirmed across full labeled dataset.")
        lines.append("2. **Query expansion audit** — for the remaining true misses, check if query underspecifies the needed knowledge.")
        lines.append("3. **Fusion ranking experiment** — for cases where doc_id found but below top-10, tune RRF or add reranker.")
        lines.append("4. **Portfolio snapshot** (Phase 10.8) — update with full-dataset real pipeline metrics.")
    else:
        lines.append("1. **Add more doc-level labels** — extend to non-P0 cases for broader coverage.")
        lines.append("2. **Query expansion audit** — for cases with genuine misses, check if query underspecifies the needed knowledge.")
        lines.append("3. **Fusion ranking experiment** — for cases where doc_id found but below top-10, tune RRF or add reranker.")
    lines.append("")

    out = pathlib.Path(OUT_EVAL_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Eval MD: {OUT_EVAL_MD}")


def write_wrong_case_recheck_md(metrics: dict[str, Any]) -> None:
    """Write wrong-case recheck report."""
    re = metrics["wrong_case_recheck"]
    ds = metrics["doc_id_summary"]
    phase_label = "Phase 10.7.5" if MODE == "full" else "Phase 10.5.1"

    lines = [
        f"# {phase_label} — Wrong-Case Doc-ID Recheck",
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
        f"| Labeled cases doc-ID correct at top-10 | {ds['cases_doc_id_correct_at_10']}/{ds['labeled_case_count']} |",
        f"| Still wrong at doc-ID level (labeled) | {ds['cases_still_wrong_at_doc_id_level']} |",
        "",
    ]

    if re["reclassified_cases"]:
        lines.append("## Reclassified Cases (Doc-ID Found)")
        lines.append("")
        lines.append("| Case ID | Original Failure Mode | Doc ID Found Rank |")
        lines.append("|---------|----------------------|-------------------|")
        for rc in re["reclassified_cases"]:
            lines.append(f"| {rc['case_id']} | {rc['original_failure_mode']} | {rc['doc_id_found_rank']} |")
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
        elif ratio >= 50:
            lines.append(f"**⚠️ Thesis partially confirmed**: {found}/{total} ({ratio:.0f}%) of wrong cases ")
            lines.append("are metric granularity problems. Remaining cases need deeper investigation.")
        else:
            lines.append(f"**❌ Thesis not supported**: Only {found}/{total} ({ratio:.0f}%) of wrong cases ")
            lines.append("are metric granularity. Most wrong cases have genuine retrieval failures.")
    else:
        lines.append("**No wrong cases to recheck.**")
    lines.append("")

    out = pathlib.Path(OUT_RECHECK_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Recheck MD: {OUT_RECHECK_MD}")


def write_remaining_misses_md(metrics: dict[str, Any]) -> None:
    """Write remaining true misses analysis report (full mode only)."""
    if MODE != "full":
        return

    ds = metrics["doc_id_summary"]
    re = metrics["wrong_case_recheck"]

    # Categorize remaining misses
    still_wrong_cases = []
    for case_id, p in metrics["per_case_results"].items():
        if not p["doc_id_correct_at_10"]:
            still_wrong_cases.append((case_id, p))

    lines = [
        "# Phase 10.7.5 — Remaining True Misses Analysis",
        "",
        f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total labeled cases | {ds['labeled_case_count']} |",
        f"| Fully correct at doc-ID level | {ds['cases_doc_id_correct_at_10']} |",
        f"| Still wrong (at least 1 doc_id missing) | {ds['cases_still_wrong_at_doc_id_level']} |",
        f"| Partial hits | {ds['cases_partial_hit']} |",
        f"| Doc-type wrong cases reclassified as doc_id-found | {re['doc_id_found_in_top_10']} |",
        "",
        "## True Miss Categorization",
        "",
        "### Query Expansion Gap (Potential)",
        "",
    ]

    query_expansion = []
    fusion_rank = []
    unknown = []

    for case_id, p in still_wrong_cases:
        missed = p["missed_doc_ids"]
        hit = p["hit_doc_ids"]
        # Heuristic categorization
        if len(hit) == 0 and len(missed) > 0:
            # No doc_ids found at all — could be query expansion or knowledge gap
            query_expansion.append((case_id, p))
        elif len(hit) > 0 and len(missed) > 0:
            # Partial hit — could be fusion ranking (some records ranked too low)
            fusion_rank.append((case_id, p))
        else:
            unknown.append((case_id, p))

    if query_expansion:
        lines.append(f"Cases where NO expected doc_id was found in top-10 ({len(query_expansion)}):")
        lines.append("")
        lines.append("| Case ID | Expected Doc IDs | Possible Cause |")
        lines.append("|---------|-----------------|----------------|")
        for case_id, p in query_expansion:
            expected_str = ", ".join(d[:8] for d in p["expected_doc_ids"])
            lines.append(f"| {case_id} | {expected_str} | Query underspecification / keyword mismatch |")
        lines.append("")

    if fusion_rank:
        lines.append("### Fusion Ranking Gap (Potential)")
        lines.append("")
        lines.append(f"Cases with partial hits ({len(fusion_rank)}):")
        lines.append("")
        lines.append("| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | Possible Cause |")
        lines.append("|---------|-----------------|---------------|--------|----------------|")
        for case_id, p in fusion_rank:
            expected_str = ", ".join(d[:8] for d in p["expected_doc_ids"])
            hit_str = ", ".join(f'{d[:8]}@{p["hit_ranks"].get(d,"?")}' for d in p["hit_doc_ids"]) or "—"
            missed_str = ", ".join(d[:8] for d in p["missed_doc_ids"]) or "—"
            lines.append(f"| {case_id} | {expected_str} | {hit_str} | {missed_str} | RRF dual-source bias / low rank |")
        lines.append("")

    lines.extend([
        "",
        "## Recommended Next Steps",
        "",
        "1. **Query expansion audit** — review query formulation for cases where no expected doc_id was found.",
        "   Determine if query terms match knowledge record terms.",
        "2. **Fusion ranking experiment** — for partial-hit cases, investigate if adjusting RRF k or",
        "   score-based fusion would bring the remaining doc_ids into top-10.",
        "3. **Manual review** — for cases where label ambiguity is suspected, verify golden labels.",
        "",
    ])

    out = pathlib.Path(OUT_MISSES_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Misses MD: {OUT_MISSES_MD}")


def main() -> None:
    mode_label = "Full-Dataset" if MODE == "full" else "P0"
    print(f"[{mode_label} Mode] Loading real pipeline export rows...")
    cases = load_real_cases()
    if not cases:
        print(f"Error: No cases loaded from {ROWS_PATH}", file=sys.stderr)
        sys.exit(1)

    labeled_count = sum(1 for c in cases if c.expected_doc_ids and len(c.expected_doc_ids) > 0)
    unlabeled_count = len(cases) - labeled_count
    print(f"Loaded {len(cases)} cases ({labeled_count} labeled, {unlabeled_count} unlabeled)")

    print("Computing doc-level metrics...")
    metrics = compute_metrics(cases)

    ds = metrics["doc_id_summary"]
    re = metrics["wrong_case_recheck"]
    print(f"\nDoc-ID correct at Top-10: {ds['cases_doc_id_correct_at_10']}/{ds['labeled_case_count']}")
    print(f"Still wrong at doc-ID level: {ds['cases_still_wrong_at_doc_id_level']}")
    print(f"Wrong-case recheck — found doc_id: {re['doc_id_found_in_top_10']}/{re['total_wrong_cases_doc_type']}")

    print("\nWriting reports...")
    write_metrics_json(metrics)
    write_evaluation_md(metrics)
    write_wrong_case_recheck_md(metrics)
    if MODE == "full":
        write_remaining_misses_md(metrics)

    print(f"\n[{mode_label} Mode] Done.")


if __name__ == "__main__":
    main()
