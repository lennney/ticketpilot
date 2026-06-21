"""Comparison report builder for retrieval evaluation.

Builds JSON and Markdown reports from RetrievalComparisonSummary data.
Follows the same pattern as evaluation/reporting.py.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any

from ticketpilot.evaluation.retrieval_metrics import (
    RetrievalComparisonSummary,
)


def _serialize_for_json(obj: Any) -> Any:
    """Serialize special types for JSON output.

    Handles frozenset, set, dict, and list types.
    """
    if isinstance(obj, frozenset):
        return sorted(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {str(k): _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


def _pct(value: float) -> str:
    """Format a ratio as a percentage string."""
    return f"{value * 100:.1f}%"


def _hit_rate_table(lines: list[str], hit_rates: dict[int, float], label: str) -> None:
    """Append a hit-rate markdown table to lines."""
    lines.append(f"### {label}")
    lines.append("")
    lines.append("| k | Hit Rate |")
    lines.append("|---|----------|")
    for k in sorted(hit_rates.keys()):
        lines.append(f"| {k} | {_pct(hit_rates[k])} |")
    lines.append("")


def comparison_summary_to_dict(
    summary: RetrievalComparisonSummary,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert retrieval comparison summary to a JSON-serializable dict.

    Args:
        summary: The computed comparison summary.
        tickets_path: Path to the tickets CSV used.
        golden_path: Path to the golden expectations CSV used.
        config: Optional configuration dict (embedding provider, model, etc.).

    Returns:
        Dict ready for JSON serialization.
    """
    per_case_dict: dict[str, dict[str, Any]] = {}
    for case_id, m in summary.per_case.items():
        entry: dict[str, Any] = {
            "top_k_doc_type_hit": m.top_k_doc_type_hit,
            "reciprocal_rank_doc_type": m.reciprocal_rank_doc_type,
        }
        if m.top_k_doc_id_hit is not None:
            entry["top_k_doc_id_hit"] = m.top_k_doc_id_hit
        if m.reciprocal_rank_doc_id is not None:
            entry["reciprocal_rank_doc_id"] = m.reciprocal_rank_doc_id
        per_case_dict[case_id] = entry

    wrong_cases_list: list[dict[str, Any]] = [
        {
            "case_id": w.case_id,
            "failure_mode": w.failure_mode,
            "details": w.details,
            "top_k_doc_type_hit": w.top_k_doc_type_hit,
            "reciprocal_rank_doc_type": w.reciprocal_rank_doc_type,
        }
        for w in summary.wrong_cases
    ]

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "tickets_path": tickets_path,
            "golden_path": golden_path,
        },
        "config": config or {},
        "total_cases": summary.total_cases,
        "aggregate_metrics": {
            "hit_rate_doc_type": summary.hit_rate_doc_type,
            "mrr_doc_type": summary.mrr_doc_type,
        },
        "per_case_results": per_case_dict,
        "wrong_cases": wrong_cases_list,
        "wrong_case_count": len(summary.wrong_cases),
    }

    if summary.hit_rate_doc_id is not None:
        result["aggregate_metrics"]["hit_rate_doc_id"] = summary.hit_rate_doc_id
    if summary.p0_added_record_hit_rate is not None:
        result["aggregate_metrics"]["p0_added_record_hit_rate"] = (
            summary.p0_added_record_hit_rate
        )
    if summary.mrr_doc_id is not None:
        result["aggregate_metrics"]["mrr_doc_id"] = summary.mrr_doc_id

    if summary.doc_id_rechecks is not None:
        result["doc_id_rechecks"] = [
            {
                "case_id": r.case_id,
                "original_failure_mode": r.original_failure_mode,
                "doc_id_found": r.doc_id_found,
                "doc_id_found_rank": r.doc_id_found_rank,
                "reclassified": r.reclassified,
            }
            for r in summary.doc_id_rechecks
        ]

    return _serialize_for_json(result)


def comparison_summary_to_markdown(
    summary: RetrievalComparisonSummary,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    config: dict[str, Any] | None = None,
) -> str:
    """Build a Markdown report from retrieval comparison summary.

    Args:
        summary: The computed comparison summary.
        tickets_path: Path to the tickets CSV used.
        golden_path: Path to the golden expectations CSV used.
        config: Optional configuration dict.

    Returns:
        Markdown report string.
    """
    lines: list[str] = [
        "# Retrieval Comparison Report",
        "",
        f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Dataset",
        "",
        f"- Tickets: `{tickets_path}`",
        f"- Golden expectations: `{golden_path}`",
        f"- Total cases: {summary.total_cases}",
        "",
    ]

    if config:
        lines.append("## Configuration")
        lines.append("")
        for k, v in config.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    # Aggregate metrics
    lines.append("## Aggregate Metrics")
    lines.append("")

    _hit_rate_table(lines, summary.hit_rate_doc_type, "Top-K Doc Type Hit Rate")

    if summary.hit_rate_doc_id is not None:
        _hit_rate_table(lines, summary.hit_rate_doc_id, "Top-K Doc ID Hit Rate")

    if summary.p0_added_record_hit_rate is not None:
        _hit_rate_table(
            lines, summary.p0_added_record_hit_rate, "Top-K P0 Added Record Hit Rate"
        )

    lines.append("### Mean Reciprocal Rank")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| MRR (doc_type) | {summary.mrr_doc_type:.4f} |")
    if summary.mrr_doc_id is not None:
        lines.append(f"| MRR (doc_id) | {summary.mrr_doc_id:.4f} |")
    lines.append("")

    # Wrong cases
    lines.append("## Wrong Cases")
    lines.append("")

    if summary.wrong_cases:
        mode_counts: dict[str, int] = {}
        for w in summary.wrong_cases:
            mode_counts[w.failure_mode] = mode_counts.get(w.failure_mode, 0) + 1

        lines.append("### Failure Mode Distribution")
        lines.append("")
        lines.append("| Failure Mode | Count |")
        lines.append("|--------------|-------|")
        for mode, count in sorted(mode_counts.items()):
            lines.append(f"| {mode} | {count} |")
        lines.append("")

        lines.append("### Per-Case Details")
        lines.append("")
        for w in summary.wrong_cases:
            hit_str = ", ".join(
                f"@{k}:{'hit' if v else 'miss'}"
                for k, v in sorted(w.top_k_doc_type_hit.items())
            )
            lines.append(f"- **{w.case_id}** ({w.failure_mode})")
            lines.append(f"  - Hit pattern: {hit_str}")
            lines.append(f"  - RR (doc_type): {w.reciprocal_rank_doc_type:.4f}")
            lines.append(f"  - {w.details}")
            lines.append("")
    else:
        lines.append("No retrieval failures detected.")
        lines.append("")

    # Doc ID recheck section
    if summary.doc_id_rechecks:
        found_count = sum(1 for r in summary.doc_id_rechecks if r.doc_id_found)
        lines.append("## Doc-ID Wrong-Case Recheck")
        lines.append("")
        lines.append(
            f"Of {len(summary.doc_id_rechecks)} wrong cases, "
            f"{found_count} have an expected doc_id in top-10 results "
            f"(reclassified from doc_type failure to doc_id hit)."
        )
        lines.append("")

        if found_count > 0:
            lines.append("### Reclassified Cases")
            lines.append("")
            lines.append(
                "| Case ID | Original Failure Mode | Doc ID Found Rank | Reclassification |"
            )
            lines.append(
                "|---------|----------------------|-------------------|------------------|"
            )
            for r in summary.doc_id_rechecks:
                if r.doc_id_found:
                    lines.append(
                        f"| {r.case_id} | {r.original_failure_mode} | "
                        f"{r.doc_id_found_rank} | {r.reclassified} |"
                    )
            lines.append("")

    return "\n".join(lines)


def write_json_report(
    summary: RetrievalComparisonSummary,
    output_path: str | pathlib.Path,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    config: dict[str, Any] | None = None,
) -> None:
    """Write a JSON retrieval comparison report.

    Args:
        summary: The computed comparison summary.
        output_path: Path for the JSON report.
        tickets_path: Path to the tickets CSV used.
        golden_path: Path to the golden expectations CSV used.
        config: Optional configuration dict.
    """
    data = comparison_summary_to_dict(
        summary,
        tickets_path=tickets_path,
        golden_path=golden_path,
        config=config,
    )
    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown_report(
    summary: RetrievalComparisonSummary,
    output_path: str | pathlib.Path,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    config: dict[str, Any] | None = None,
) -> str:
    """Write a Markdown retrieval comparison report.

    Args:
        summary: The computed comparison summary.
        output_path: Path for the Markdown report.
        tickets_path: Path to the tickets CSV used.
        golden_path: Path to the golden expectations CSV used.
        config: Optional configuration dict.

    Returns:
        The Markdown content as a string.
    """
    md = comparison_summary_to_markdown(
        summary,
        tickets_path=tickets_path,
        golden_path=golden_path,
        config=config,
    )
    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    return md
