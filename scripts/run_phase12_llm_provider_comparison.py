#!/usr/bin/env python3
"""Phase 12 LLM Provider Comparison Runner.

Compares FakeLLMProvider (baseline) against OpenAICompatibleProvider (real).
Local demo / portfolio prototype only - no production benchmark claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ticketpilot.drafting.generator import generate_draft
from ticketpilot.drafting.llm_provider import FakeLLMProvider, SAFE_FALLBACK_TEXT
from ticketpilot.drafting.provider_config import load_llm_provider_config, create_llm_provider
from ticketpilot.evaluation.draft_metrics import compute_draft_evaluation_summary
from ticketpilot.evaluation.schemas import DraftEvaluationRow
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.ticket import (
    TicketOutput, IntentClass, RiskSeverity, RiskFlag,
    RawTicket, NormalizedTicket, ClassificationResult, RiskAssessment,
)
from uuid import uuid4


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _make_mock_evidence() -> list[EvidenceCandidate]:
    """Create mock evidence candidates for testing."""
    return [
        EvidenceCandidate(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid4(),
            source_table="knowledge_faq",
            content="The return policy requires requests within 7 days.",
            score=0.85,
            rank=1,
            title="Return Policy",
        ),
        EvidenceCandidate(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.POLICY,
            source_id=uuid4(),
            source_table="knowledge_policy",
            content="For refunds, customers must submit requests within 30 days of purchase.",
            score=0.80,
            rank=2,
            title="Refund Policy",
        ),
    ]


def _build_ticket_output(case: dict[str, Any], evidence: list) -> TicketOutput:
    """Build a TicketOutput from a fixture case and mock evidence."""
    severity = RiskSeverity(case.get("severity", "low"))
    now = datetime.now(timezone.utc)
    flags: set[RiskFlag] = set()
    for flag_str in case.get("risk_flags", []):
        try:
            flags.add(RiskFlag(flag_str))
        except (ValueError, KeyError):
            pass

    # Map fixture issue_type to IntentClass (relaxed mapping)
    issue_type = case["issue_type"]
    intent_map: dict[str, IntentClass] = {
        "refund": IntentClass.REFUND,
        "refund_request": IntentClass.REFUND,
        "return_exchange": IntentClass.RETURN_EXCHANGE,
        "account_issue": IntentClass.ACCOUNT_ISSUE,
        "account_security": IntentClass.ACCOUNT_ISSUE,
        "technical_issue": IntentClass.TECHNICAL_ISSUE,
        "product_consulting": IntentClass.PRODUCT_CONSULTING,
        "logistics": IntentClass.LOGISTICS,
        "logistics_inquiry": IntentClass.LOGISTICS,
        "logistics_issue": IntentClass.LOGISTICS,
        "complaint": IntentClass.COMPLAINT,
        "privacy_concern": IntentClass.COMPLAINT,
        "legal_complaint": IntentClass.COMPLAINT,
        "compensation_claim": IntentClass.COMPLAINT,
        "policy_inquiry": IntentClass.OTHER,
        "billing_inquiry": IntentClass.OTHER,
        "policy_dispute": IntentClass.OTHER,
        "general_inquiry": IntentClass.OTHER,
        "other": IntentClass.OTHER,
    }
    intent = intent_map.get(issue_type, IntentClass.OTHER)

    return TicketOutput(
        ticket_id=case["case_id"],
        raw_ticket=RawTicket(
            original_text=case["normalized_text"],
            submitted_at=now,
        ),
        normalized_ticket=NormalizedTicket(
            text=case["normalized_text"],
            language="zh",
            cleaned_at=now,
        ),
        classification=ClassificationResult(
            intent=intent,
            confidence=0.9,
            classified_at=now,
        ),
        risk_assessment=RiskAssessment(
            flags=flags,
            severity=severity,
            must_human_review=False,
            assessed_at=now,
        ),
        output_at=now,
        evidence_candidates=evidence,
    )


def _build_row_from_result(
    case: dict[str, Any],
    result: Any,
) -> dict[str, Any]:
    """Extract DraftEvaluationRow fields from a DraftGenerationResult."""
    cv = result.citation_validation
    guard = result.guard_result

    return {
        "case_id": case["case_id"],
        "provider_name": result.provider_name,
        "model_name": result.model_name,
        "cited_evidence_count": len(result.draft.cited_evidence_ids),
        "available_evidence_count": len(cv.available_evidence_ids),
        "valid_citation_count": len(cv.valid_cited_evidence_ids),
        "invalid_citation_count": len(cv.invalid_cited_evidence_ids),
        "unsupported_claim_count": len(result.draft.unsupported_claims),
        "forbidden_promise_count": (
            1 if (guard.forbidden_promise_details and len(guard.forbidden_promise_details) > 0) else 0
        ),
        "guard_passed": guard.guard_passed,
        "citation_validation_passed": cv.is_valid,
        "safe_fallback_used": _is_safe_fallback_text(result.draft.draft_text),
        "expected_human_review": case.get("must_human_review", False),
        "actual_human_review": result.draft.must_human_review,
        "confidence": result.draft.confidence,
    }


def _is_safe_fallback_text(text: str) -> bool:
    """Check if draft text is a safe-fallback message."""
    patterns = ["无法确认具体政策条款", "建议转人工处理", "转人工", "证据不足"]
    text_lower = text.lower()
    return any(p in text_lower for p in patterns) or text == SAFE_FALLBACK_TEXT


def run_provider_comparison(
    provider_name: str,
    provider: Any,
    fixtures: list[dict[str, Any]],
    limit: int | None = None,
) -> dict[str, Any]:
    """Run comparison for a single provider."""
    results = []
    evidence = _make_mock_evidence()
    cases = fixtures[:limit] if limit else fixtures

    for case in cases:
        try:
            ticket_output = _build_ticket_output(case, evidence)
            gen_result = generate_draft(ticket_output, provider=provider)

            row_data = _build_row_from_result(case, gen_result)

            # Also keep legacy fields for report compatibility
            result_dict = {
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "provider": provider_name,
                "draft_text_length": len(gen_result.draft.draft_text),
                "confidence": gen_result.draft.confidence,
                "must_human_review": gen_result.draft.must_human_review,
                "fallback_reason": gen_result.draft.fallback_reason,
                "escalation_reason": gen_result.draft.escalation_reason,
                "has_citations": len(gen_result.draft.cited_evidence_ids) > 0,
                "safety_notes_count": len(gen_result.draft.safety_notes),
                # Extended metrics
                "cited_evidence_count": row_data["cited_evidence_count"],
                "available_evidence_count": row_data["available_evidence_count"],
                "valid_citation_count": row_data["valid_citation_count"],
                "invalid_citation_count": row_data["invalid_citation_count"],
                "guard_passed": row_data["guard_passed"],
                "citation_validation_passed": row_data["citation_validation_passed"],
                "safe_fallback_used": row_data["safe_fallback_used"],
                "unsupported_claim_count": row_data["unsupported_claim_count"],
                "forbidden_promise_count": row_data["forbidden_promise_count"],
                "actual_human_review": row_data["actual_human_review"],
                "provider_name": row_data["provider_name"],
                "model_name": row_data["model_name"],
            }
            results.append(result_dict)
        except Exception as e:
            results.append({
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "provider": provider_name,
                "error": str(e),
            })

    return {
        "provider": provider_name,
        "total_cases": len(results),
        "successful": sum(1 for r in results if "error" not in r),
        "results": results,
    }


def generate_report(fake_results: dict, real_results: dict | None, output_dir: Path) -> Path:
    """Generate markdown comparison report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"phase12_llm_provider_comparison_report_{timestamp}.md"

    def _compute_stats(provider_results: dict) -> dict:
        rows = [r for r in provider_results["results"] if "error" not in r]
        if not rows:
            return {}
        n = len(rows)
        return {
            "total": provider_results["total_cases"],
            "successful": provider_results["successful"],
            "avg_confidence": sum(r.get("confidence", 0) for r in rows) / n,
            "human_review_count": sum(1 for r in rows if r.get("must_human_review")),
            "guard_pass_count": sum(1 for r in rows if r.get("guard_passed", False)),
            "citation_valid_count": sum(1 for r in rows if r.get("citation_validation_passed", False)),
            "safe_fallback_count": sum(1 for r in rows if r.get("safe_fallback_used", False)),
            "cited_evidence_avg": sum(r.get("cited_evidence_count", 0) for r in rows) / n,
            "valid_citation_avg": sum(r.get("valid_citation_count", 0) for r in rows) / n,
            "invalid_citation_avg": sum(r.get("invalid_citation_count", 0) for r in rows) / n,
        }

    fake_stats = _compute_stats(fake_results)
    real_stats = _compute_stats(real_results) if real_results else None

    report = f"""# Phase 12: LLM Provider Comparison Report

**Generated**: {datetime.now().isoformat()}
**Scope**: Local demo / portfolio prototype - NOT a production benchmark

## Summary

| Provider | Cases | Success | Avg Confidence | Human Review | Guard Passed | Citation Valid | Safe Fallback |
|----------|-------|---------|----------------|--------------|--------------|----------------|---------------|
| FakeLLMProvider | {fake_stats.get('total','-')} | {fake_stats.get('successful','-')} | {fake_stats.get('avg_confidence',0):.2f} | {fake_stats.get('human_review_count','-')} | {fake_stats.get('guard_pass_count','-')} | {fake_stats.get('citation_valid_count','-')} | {fake_stats.get('safe_fallback_count','-')} |
"""
    if real_stats:
        report += f"| OpenAICompatibleProvider | {real_stats.get('total','-')} | {real_stats.get('successful','-')} | {real_stats.get('avg_confidence',0):.2f} | {real_stats.get('human_review_count','-')} | {real_stats.get('guard_pass_count','-')} | {real_stats.get('citation_valid_count','-')} | {real_stats.get('safe_fallback_count','-')} |\n"
    else:
        report += "| OpenAICompatibleProvider | - | real: not configured | - | - | - | - | - |\n"

    report += """
## Citation Metrics

| Provider | Avg Cited | Avg Valid Citations | Avg Invalid Citations |
|----------|-----------|---------------------|-----------------------|
| FakeLLMProvider | """ + f"{fake_stats.get('cited_evidence_avg', 0):.2f} | {fake_stats.get('valid_citation_avg', 0):.2f} | {fake_stats.get('invalid_citation_avg', 0):.2f}"
    if real_stats:
        report += f"| OpenAICompatibleProvider | {real_stats.get('total','-')} | {real_stats.get('successful','-')} | {real_stats.get('avg_confidence',0):.2f} | {real_stats.get('human_review_count','-')} | {real_stats.get('guard_pass_count','-')} | {real_stats.get('citation_valid_count','-')} | {real_stats.get('safe_fallback_count','-')} |\n"
    else:
        report += "| OpenAICompatibleProvider | - | real: not configured | - | - | - | - | - |\n"

    report += """
## Citation Metrics

| Provider | Avg Cited | Avg Valid Citations | Avg Invalid Citations |
|----------|-----------|---------------------|-----------------------|
| FakeLLMProvider | """ + f"{fake_stats.get('cited_evidence_avg', 0):.2f} | {fake_stats.get('valid_citation_avg', 0):.2f} | {fake_stats.get('invalid_citation_avg', 0):.2f}"

    if real_stats:
        report += f"""
| OpenAICompatibleProvider | {real_stats.get('cited_evidence_avg', 0):.2f} | {real_stats.get('valid_citation_avg', 0):.2f} | {real_stats.get('invalid_citation_avg', 0):.2f} |
"""
    else:
        report += """
| OpenAICompatibleProvider | - | - | - |
"""

    report += """
## Methodology

- Fixture set: 25 synthetic cases covering diverse scenarios
- Both providers receive same evidence (mock) and same case parameters
- Comparison focuses on: response quality, confidence, human review triggers
- Citation validation and claim guard applied to all results

## Boundary

This is a **local demo / portfolio prototype**. Results do not constitute:
- Production benchmark
- Comparative evaluation of commercial LLM services
- Guarantee of deployment readiness

## Detailed Results

"""
    for result in fake_results["results"][:5]:
        report += f"### {result['case_id']} ({result['scenario']})\n"
        report += f"- Confidence: {result.get('confidence', 0):.2f}\n"
        report += f"- Human Review: {result.get('must_human_review', False)}\n"
        report += f"- Has Citations: {result.get('has_citations', False)}\n"
        report += f"- Guard Passed: {result.get('guard_passed', True)}\n"
        report += f"- Citation Validation: {'PASS' if result.get('citation_validation_passed', False) else 'FAIL'}\n"
        report += f"- Safe Fallback: {result.get('safe_fallback_used', False)}\n\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


def _rows_to_eval_rows(rows: list[dict]) -> list[DraftEvaluationRow]:
    """Convert result rows to DraftEvaluationRow list."""
    eval_rows = []
    for r in rows:
        if "error" in r:
            continue
        try:
            eval_rows.append(DraftEvaluationRow(
                case_id=r["case_id"],
                provider_name=r.get("provider_name", ""),
                model_name=r.get("model_name", ""),
                cited_evidence_count=r.get("cited_evidence_count", 0),
                available_evidence_count=r.get("available_evidence_count", 0),
                valid_citation_count=r.get("valid_citation_count", 0),
                invalid_citation_count=r.get("invalid_citation_count", 0),
                unsupported_claim_count=r.get("unsupported_claim_count", 0),
                forbidden_promise_count=r.get("forbidden_promise_count", 0),
                guard_passed=r.get("guard_passed", True),
                citation_validation_passed=r.get("citation_validation_passed", True),
                safe_fallback_used=r.get("safe_fallback_used", False),
                expected_human_review=r.get("expected_human_review", False),
                actual_human_review=r.get("actual_human_review", False),
                confidence=r.get("confidence"),
            ))
        except Exception:
            continue
    return eval_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 12 LLM Provider Comparison")
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures/phase12_draft_comparison_cases.json"))
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to process")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/eval"), help="Output directory for reports")
    parser.add_argument("--extended-rows", action="store_true", help="Output extended DraftEvaluationRow JSON")
    args = parser.parse_args()

    if not args.fixtures.exists():
        print(f"Error: Fixture file not found: {args.fixtures}")
        return 1

    fixtures = load_fixtures(args.fixtures)
    print(f"Loaded {len(fixtures)} test cases")

    print("Running FakeLLMProvider baseline...")
    fake_provider = FakeLLMProvider()
    fake_results = run_provider_comparison("fake", fake_provider, fixtures, args.limit)
    print(f"  {fake_results['successful']}/{fake_results['total_cases']} successful")

    real_results = None
    try:
        config = load_llm_provider_config()
        if config.provider_type == "openai_compatible":
            print("Real provider configured, running comparison...")
            real_provider = create_llm_provider(config)
            real_results = run_provider_comparison("openai_compatible", real_provider, fixtures, args.limit)
            print(f"  {real_results['successful']}/{real_results['total_cases']} successful")
        else:
            print("Real provider not configured")
    except Exception as e:
        print(f"Real provider check failed: {e}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.extended_rows:
        # Build DraftEvaluationRow objects and compute summary for both providers
        fake_rows = _rows_to_eval_rows(fake_results["results"])
        real_rows = _rows_to_eval_rows(real_results["results"]) if real_results else []

        # Compute per-provider summaries
        fake_summary = compute_draft_evaluation_summary(fake_rows) if fake_rows else None
        real_summary = compute_draft_evaluation_summary(real_rows) if real_rows else None

        extended_data = {
            "fake_rows": [r.model_dump() for r in fake_rows],
            "fake_summary": fake_summary.model_dump() if fake_summary else None,
            "real_rows": [r.model_dump() for r in real_rows],
            "real_summary": real_summary.model_dump() if real_summary else None,
            "timestamp": timestamp,
            "limit": args.limit,
        }

        json_path = args.output_dir / f"phase12_extended_eval_rows_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(extended_data, f, indent=2, ensure_ascii=False)
        print(f"Extended rows JSON saved to: {json_path}")
        if fake_summary:
            print(f"  Fake: {len(fake_rows)} rows, citation_precision={fake_summary.citation_precision_avg:.3f}, "
                  f"guard_pass_rate={fake_summary.claim_guard_pass_rate:.3f}")
        if real_summary:
            print(f"  Real: {len(real_rows)} rows, citation_precision={real_summary.citation_precision_avg:.3f}, "
                  f"guard_pass_rate={real_summary.claim_guard_pass_rate:.3f}")
        elif real_results:
            print(f"  Real: failed to compute summary ({len(real_results.get('results', []))} result rows)")

    # Always save legacy JSON
    json_path = args.output_dir / f"phase12_llm_provider_comparison_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "fake_results": fake_results,
            "real_results": real_results,
            "timestamp": timestamp,
            "limit": args.limit,
        }, f, indent=2, ensure_ascii=False)
    print(f"JSON results saved to: {json_path}")

    report_path = generate_report(fake_results, real_results, args.output_dir)
    print(f"Markdown report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())