#!/usr/bin/env python3
"""Phase 12 LLM Provider Comparison Runner.

Compares FakeLLMProvider (baseline) against OpenAICompatibleProvider (real).
Local demo / portfolio prototype only - no production benchmark claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ticketpilot.drafting.llm_provider import FakeLLMProvider
from ticketpilot.drafting.provider_config import load_llm_provider_config, create_llm_provider
from ticketpilot.retrieval.schema.knowledge import DocType
from uuid import uuid4


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _make_mock_evidence() -> list:
    """Create mock evidence candidates for testing."""
    from unittest.mock import MagicMock
    ev = MagicMock()
    ev.chunk_id = uuid4()
    ev.doc_id = uuid4()
    ev.doc_type = DocType.FAQ
    ev.source_table = "knowledge_faq"
    ev.source_id = str(ev.doc_id)
    ev.content = "The return policy requires requests within 7 days."
    ev.score = 0.85
    ev.rank = 1
    ev.title = "Return Policy"
    return [ev]


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
            result = provider.generate_draft(
                normalized_text=case["normalized_text"],
                issue_type=case["issue_type"],
                risk_flags=case.get("risk_flags", []),
                severity=case.get("severity", "low"),
                evidence_candidates=evidence,
            )
            results.append({
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "provider": provider_name,
                "draft_text_length": len(result.draft_text),
                "confidence": result.confidence,
                "must_human_review": result.must_human_review,
                "fallback_reason": result.fallback_reason,
                "escalation_reason": result.escalation_reason,
                "has_citations": len(result.citations) > 0,
                "safety_notes_count": len(result.safety_notes),
            })
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

    fake_stats = {
        "total": fake_results["total_cases"],
        "successful": fake_results["successful"],
        "avg_confidence": sum(r.get("confidence", 0) for r in fake_results["results"]) / len(fake_results["results"]) if fake_results["results"] else 0,
        "human_review_count": sum(1 for r in fake_results["results"] if r.get("must_human_review")),
    }

    real_stats = None
    if real_results:
        real_stats = {
            "total": real_results["total_cases"],
            "successful": real_results["successful"],
            "avg_confidence": sum(r.get("confidence", 0) for r in real_results["results"]) / len(real_results["results"]) if real_results["results"] else 0,
            "human_review_count": sum(1 for r in real_results["results"] if r.get("must_human_review")),
        }

    report = f"""# Phase 12: LLM Provider Comparison Report

**Generated**: {datetime.now().isoformat()}
**Scope**: Local demo / portfolio prototype - NOT a production benchmark

## Summary

| Provider | Cases | Success | Avg Confidence | Human Review |
|----------|-------|---------|----------------|--------------|
| FakeLLMProvider | {fake_stats['total']} | {fake_stats['successful']} | {fake_stats['avg_confidence']:.2f} | {fake_stats['human_review_count']} |
"""

    if real_stats:
        report += f"| OpenAICompatibleProvider | {real_stats['total']} | {real_stats['successful']} | {real_stats['avg_confidence']:.2f} | {real_stats['human_review_count']} |\n"
    else:
        report += "| OpenAICompatibleProvider | - | real: not configured | - | - |\n"

    report += """
## Methodology

- Fixture set: 25 synthetic cases covering diverse scenarios
- Both providers receive same evidence (mock) and same case parameters
- Comparison focuses on: response quality, confidence, human review triggers

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
        report += f"- Has Citations: {result.get('has_citations', False)}\n\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 12 LLM Provider Comparison")
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures/phase12_draft_comparison_cases.json"))
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to process")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/eval"), help="Output directory for reports")
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