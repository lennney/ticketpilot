#!/usr/bin/env python
"""Offline draft evaluation CLI runner for Phase 11.

Runs evidence-grounded draft generation over eval tickets using FakeLLMProvider,
computes deterministic draft quality metrics, and writes JSON and Markdown reports.

This script does NOT call real LLM APIs, database, embedding provider, or network.
All computation uses FakeLLMProvider and is deterministic.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from datetime import datetime, timezone
from typing import NoReturn

from ticketpilot.evaluation.draft_metrics import (
    compute_draft_evaluation_summary,
)
from ticketpilot.evaluation.schemas import (
    DraftEvaluationRow,
    DraftEvaluationSummary,
)
from ticketpilot.evaluation.loaders import load_tickets_eval
from ticketpilot.schema.ticket import RawTicket


def die(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit with the given code."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run offline draft evaluation using FakeLLMProvider."
    )
    parser.add_argument(
        "--tickets",
        required=True,
        help="Path to tickets_eval.csv",
    )
    parser.add_argument(
        "--out-rows",
        required=True,
        help="Path for per-case JSON rows output",
    )
    parser.add_argument(
        "--out-summary",
        required=True,
        help="Path for summary JSON output",
    )
    parser.add_argument(
        "--out-md",
        required=True,
        help="Path for Markdown report output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit to N tickets (0 = all). Useful for fast smoke test.",
    )
    return parser.parse_args(argv)


def _run_pipeline(ticket_text: str, ticket_id: str, submitted_at: str):
    """Run draft generation pipeline for a single ticket.

    Uses the Phase 11.6 generate_draft() from generator.py to get
    full DraftGenerationResult with structured validation data
    (citation validation + claim guard).
    """
    from ticketpilot.drafting.generator import generate_draft as gen_draft
    from ticketpilot.pipeline import intake_risk_pipeline

    raw = RawTicket(
        original_text=ticket_text,
        submitted_at=submitted_at,
    )
    ticket_output = intake_risk_pipeline(raw)
    gen_result = gen_draft(ticket_output)
    return gen_result


def _build_row(
    case_id: str,
    gen_result,
) -> DraftEvaluationRow:
    """Convert DraftGenerationResult to DraftEvaluationRow.

    Works with both Phase 11.6+ (DraftGenerationResult) results.
    Falls back gracefully when validation metadata is unavailable.

    expected_human_review is True when the input ticket has any
    high-risk signal before draft generation runs:
    - must_human_review flag is set on risk assessment
    - severity is HIGH
    - risk_flags are non-empty
    - no evidence candidates were found
    """
    draft = gen_result.draft
    ticket_output = gen_result.ticket_output  # available on DraftGenerationResult
    evidence = ticket_output.evidence_candidates
    risk = ticket_output.risk_assessment

    # Pre-draft human review conditions (from ticket state, not pipeline output)
    expected_hr = (
        risk.must_human_review if risk and risk.must_human_review else False
    ) or (
        risk.severity.value == "high" if risk else False
    ) or (
        bool(risk.flags) if risk and risk.flags else False
    ) or (
        len(evidence) == 0
    )

    cv = gen_result.citation_validation
    gr = gen_result.guard_result
    valid_count = len(cv.valid_cited_evidence_ids) if cv else 0
    invalid_count = len(cv.invalid_cited_evidence_ids) if cv else 0
    cited_count = valid_count + invalid_count
    avail_count = len(evidence)
    citation_passed = cv.is_valid if cv else True
    guard_ok = gr.guard_passed if gr else True
    unsupported_count = len(draft.unsupported_claims)
    forbidden_count = 1 if (gr and gr.has_forbidden_promise) else 0
    safe_fallback = draft.fallback_reason == "no_evidence"
    confidence = draft.confidence
    actual_hr = draft.must_human_review

    return DraftEvaluationRow(
        case_id=case_id,
        provider_name=gen_result.provider_name,
        model_name=gen_result.model_name,
        cited_evidence_count=cited_count,
        available_evidence_count=avail_count,
        valid_citation_count=valid_count,
        invalid_citation_count=invalid_count,
        unsupported_claim_count=unsupported_count,
        forbidden_promise_count=forbidden_count,
        guard_passed=guard_ok,
        citation_validation_passed=citation_passed,
        safe_fallback_used=safe_fallback,
        expected_human_review=expected_hr,
        actual_human_review=actual_hr,
        confidence=confidence,
    )


def _serialize_row(row: DraftEvaluationRow) -> dict:
    """Serialize DraftEvaluationRow to dict for JSON output."""
    return {
        "case_id": row.case_id,
        "provider_name": row.provider_name,
        "model_name": row.model_name,
        "cited_evidence_count": row.cited_evidence_count,
        "available_evidence_count": row.available_evidence_count,
        "valid_citation_count": row.valid_citation_count,
        "invalid_citation_count": row.invalid_citation_count,
        "unsupported_claim_count": row.unsupported_claim_count,
        "forbidden_promise_count": row.forbidden_promise_count,
        "guard_passed": row.guard_passed,
        "citation_validation_passed": row.citation_validation_passed,
        "safe_fallback_used": row.safe_fallback_used,
        "expected_human_review": row.expected_human_review,
        "actual_human_review": row.actual_human_review,
        "confidence": row.confidence,
    }


def _serialize_summary(summary: DraftEvaluationSummary) -> dict:
    """Serialize DraftEvaluationSummary to dict for JSON output."""
    return {
        "total_cases": summary.total_cases,
        "citation_precision_avg": summary.citation_precision_avg,
        "evidence_coverage_avg": summary.evidence_coverage_avg,
        "unsupported_claim_rate": summary.unsupported_claim_rate,
        "forbidden_promise_rate": summary.forbidden_promise_rate,
        "safe_fallback_rate": summary.safe_fallback_rate,
        "human_review_trigger_accuracy": summary.human_review_trigger_accuracy,
        "citation_validation_pass_rate": summary.citation_validation_pass_rate,
        "claim_guard_pass_rate": summary.claim_guard_pass_rate,
        "average_confidence": summary.average_confidence,
    }


def _write_markdown_report(
    summary: DraftEvaluationSummary,
    rows: list[DraftEvaluationRow],
    output_path: str,
    tickets_path: str,
    timestamp: str,
) -> None:
    """Write a Markdown report of draft evaluation results."""

    lines: list[str] = [
        "# Phase 11.8 — Offline Draft Evaluation Report",
        "",
        f"> **评估时间:** {timestamp}",
        f"> **数据来源:** {tickets_path}",
        "> **提供商:** FakeLLMProvider (确定性，无网络调用)",
        "",
        "> **范围边界:**",
        "> - 本地演示 / 作品集原型 — 不是生产系统",
        "> - 合成数据 — 不使用真实客户数据",
        "> - 离线评估 — 不是生产基准测试",
        "> - 草稿生成模式 — 不自动发送回复",
        "> - 无真实 LLM API 调用 — 使用确定性 FakeLLMProvider",
        "",
        "## 指标定义",
        "",
        "| 指标 | 定义 |",
        "|---|---|",
        "| citation_precision_avg | 有效引用数 / 总引用数 (无引用时为 None，不计入平均) |",
        "| evidence_coverage_avg | 已引用有效证据数 / 可用证据数 (无可用证据时为 None，不计入平均) |",
        "| unsupported_claim_rate | 含有无证据声明的案例数 / 总案例数 |",
        "| forbidden_promise_rate | 检测到禁止承诺的案例数 / 总案例数 |",
        "| safe_fallback_rate | 触发无证据回退的案例数 / 总案例数 |",
        "| human_review_trigger_accuracy | 人工审核触发正确率 (期望 vs 实际) |",
        "| citation_validation_pass_rate | 引用验证通过的案例数 / 总案例数 |",
        "| claim_guard_pass_rate | 护卫检查通过的案例数 / 总案例数 |",
        "| average_confidence | 平均置信度 (无置信度数据时为 None) |",
        "",
        "## 汇总指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 总案例数 | {summary.total_cases} |",
    ]

    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    summary_data = _serialize_summary(summary)
    for key in (
        "citation_precision_avg",
        "evidence_coverage_avg",
        "unsupported_claim_rate",
        "forbidden_promise_rate",
        "safe_fallback_rate",
        "human_review_trigger_accuracy",
        "citation_validation_pass_rate",
        "claim_guard_pass_rate",
        "average_confidence",
    ):
        label = key.replace("_", " ").replace("avg", "avg").title()
        lines.append(f"| {label} | {fmt(summary_data[key])} |")

    lines += [
        "",
        "## 简短解读",
        "",
        f"共评估 {summary.total_cases} 个工单。",
    ]

    if summary_data.get("citation_precision_avg") is not None:
        lines.append(
            f"平均引用精确度为 {summary_data['citation_precision_avg']:.2%}，"
            "反映了草稿中引用的证据质量。"
        )
    if summary_data.get("unsupported_claim_rate", 0) > 0:
        lines.append(
            f"无证据支持的声明率为 {summary_data['unsupported_claim_rate']:.2%}，"
            "这些案例需要人工审核。"
        )
    if summary_data.get("forbidden_promise_rate", 0) > 0:
        lines.append(
            f"禁止承诺率为 {summary_data['forbidden_promise_rate']:.2%}，"
            "这些案例触发了安全护卫检查。"
        )

    lines += [
        "",
        "## 局限性说明",
        "",
        "- **FakeLLMProvider 测试工作流机制，而非真实 LLM 生成质量**",
        "- 无生产环境或企业级验证",
        "- 无真实客户数据",
        "- 仅使用离线合成fixture评估",
        "- 下一阶段建议接入真实 LLM provider 以验证语义生成质量",
        "",
    ]

    pathlib.Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def run_draft_eval(args: argparse.Namespace) -> None:
    """Load tickets, run draft generation, compute metrics, write reports."""
    tickets = load_tickets_eval(args.tickets)
    if not tickets:
        die(f"No tickets loaded from {args.tickets}")

    case_ids = sorted(tickets.keys())
    if args.limit > 0:
        case_ids = case_ids[: args.limit]

    rows: list[DraftEvaluationRow] = []
    errors: list[str] = []

    for case_id in case_ids:
        ticket = tickets[case_id]
        try:
            result = _run_pipeline(
                ticket_text=ticket.original_text,
                ticket_id=case_id,
                submitted_at=ticket.submitted_at,
            )
            row = _build_row(case_id, result)
            rows.append(row)
        except Exception as exc:  # pragma: no cover
            errors.append(f"Case {case_id!r}: {exc}")

    if errors:
        print(f"Warning: {len(errors)} case(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)

    summary = compute_draft_evaluation_summary(rows)

    # Write rows JSON
    import json

    rows_data = [_serialize_row(r) for r in rows]
    pathlib.Path(args.out_rows).write_text(
        json.dumps(rows_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Per-case rows written to {args.out_rows}")

    # Write summary JSON
    summary_data = _serialize_summary(summary)
    pathlib.Path(args.out_summary).write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Summary written to {args.out_summary}")

    # Write markdown report
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _write_markdown_report(
        summary,
        rows,
        args.out_md,
        args.tickets,
        timestamp,
    )
    print(f"Markdown report written to {args.out_md}")


def main() -> None:
    """Entry point for the CLI."""
    args = parse_args()
    run_draft_eval(args)


if __name__ == "__main__":
    main()
