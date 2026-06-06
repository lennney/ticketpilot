#!/usr/bin/env python3
"""
TicketPilot Pipeline Evaluation — DeepEval + real pipeline.

Pattern (from RAGEval):
  1. collect_samples() — run real pipeline, cache to JSON
  2. run_deepeval()    — LLM-as-judge on cached samples
  3. print_report()    — aggregated metrics + per-case details

Usage:
    python scripts/run_pipeline_eval.py                    # use cached samples
    python scripts/run_pipeline_eval.py --force            # re-run pipeline
    python scripts/run_pipeline_eval.py --limit 20         # only first 20 cases
    python scripts/run_pipeline_eval.py --dataset data/eval/agent_eval_dataset_v2.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ---------------------------------------------------------------------------
# Env setup (DeepSeek as judge)
# ---------------------------------------------------------------------------

def _read_env() -> tuple[str, str]:
    env_path = PROJECT_ROOT / ".env.local"
    key, base = "", "https://api.deepseek.com"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                s = line.strip()
                if s.startswith("TICKETPILOT_LLM_API_KEY="):
                    key = s.split("=", 1)[1]
                elif s.startswith("TICKETPILOT_LLM_BASE_URL="):
                    base = s.split("=", 1)[1]
    return key, base


_API_KEY, _API_BASE = _read_env()
os.environ["OPENAI_API_KEY"] = _API_KEY  # DeepEval needs this set

SAMPLES_CACHE = PROJECT_ROOT / "reports" / "eval" / "pipeline_samples_cache.json"


# ---------------------------------------------------------------------------
# Step 1: Collect samples by running the real pipeline
# ---------------------------------------------------------------------------

def collect_samples(
    dataset_path: str,
    limit: int = 0,
    force: bool = False,
) -> list[dict]:
    """Run the real pipeline on each eval case and cache results."""
    if not force:
        try:
            cached = json.loads(SAMPLES_CACHE.read_text(encoding="utf-8"))
            print(f"[cache] Loaded {len(cached)} cached samples from {SAMPLES_CACHE.name}")
            if limit > 0:
                cached = cached[:limit]
            return cached
        except FileNotFoundError:
            pass

    # Load eval dataset
    with open(dataset_path, encoding="utf-8") as f:
        cases = json.load(f)
    if limit > 0:
        cases = cases[:limit]
    print(f"[collect] Running pipeline on {len(cases)} cases...")

    # Import pipeline components
    from ticketpilot.pipeline import intake_risk_pipeline
    from ticketpilot.schema.ticket import RawTicket
    from ticketpilot.drafting.draft_agent import DraftAgent
    from ticketpilot.retrieval.providers import get_embedding_provider

    # Get real embedding provider
    embedding_provider = get_embedding_provider()
    print(f"[embed] Using embedding provider: {embedding_provider.provider_name}")

    samples = []
    for i, case in enumerate(cases, 1):
        case_id = case.get("case_id", f"CASE-{i}")
        input_text = case["input_text"]
        expected_intent = case.get("expected_intent", "")
        context = case.get("context", [])

        t0 = time.time()
        try:
            raw_ticket = RawTicket(
                original_text=input_text,
                submitted_at=datetime.utcnow(),
            )
            ticket_output = intake_risk_pipeline(raw_ticket, embedding_provider=embedding_provider)

            agent = DraftAgent()
            draft = agent.generate_draft(
                normalized_text=ticket_output.normalized_ticket.text,
                issue_type=ticket_output.classification.intent.value,
                risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
                severity=ticket_output.risk_assessment.severity.value,
                must_human_review=ticket_output.risk_assessment.must_human_review,
                evidence_candidates=ticket_output.evidence_candidates,
            )

            answer = draft.draft_text
            actual_intent = ticket_output.classification.intent.value
            has_citations = bool(draft.citations)
            evidence_texts = [
                ec.content for ec in ticket_output.evidence_candidates[:5]
            ]
            duration_ms = (time.time() - t0) * 1000
            error = None

            print(f"  [{i}/{len(cases)}] {case_id} intent={actual_intent} "
                  f"faith=? rel=? {duration_ms:.0f}ms")
        except Exception as e:
            answer = ""
            actual_intent = ""
            has_citations = False
            evidence_texts = []
            duration_ms = (time.time() - t0) * 1000
            error = str(e)
            print(f"  [{i}/{len(cases)}] {case_id} ERROR: {e}")

        samples.append({
            "case_id": case_id,
            "input_text": input_text,
            "answer": answer,
            "contexts": evidence_texts,
            "ground_truth": context[0] if context else "",
            "expected_intent": expected_intent,
            "actual_intent": actual_intent,
            "has_citations": has_citations,
            "duration_ms": round(duration_ms, 2),
            "error": error,
        })

    # Cache
    SAMPLES_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES_CACHE.write_text(
        json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[cached] {len(cases)} samples → {SAMPLES_CACHE.name}")
    return samples


# ---------------------------------------------------------------------------
# Step 2: Run DeepEval LLM-as-judge
# ---------------------------------------------------------------------------

def run_deepeval(samples: list[dict]) -> list[dict]:
    """Evaluate cached samples with DeepEval metrics."""
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )
    from deepeval.models.llms.openai_model import GPTModel
    from deepeval.test_case import LLMTestCase
    from deepeval.evaluate.configs import AsyncConfig

    print("\n" + "=" * 60)
    print("  DeepEval LLM-as-Judge Evaluation")
    print("=" * 60)

    judge = GPTModel(
        model="deepseek-chat",
        base_url=_API_BASE,
        api_key=_API_KEY,
    )

    metrics = [
        FaithfulnessMetric(threshold=0.7, model=judge, verbose_mode=False),
        AnswerRelevancyMetric(threshold=0.7, model=judge, verbose_mode=False),
        ContextualPrecisionMetric(threshold=0.7, model=judge, verbose_mode=False),
        ContextualRecallMetric(threshold=0.7, model=judge, verbose_mode=False),
    ]

    # Build test cases (skip errored ones)
    test_cases = []
    valid_indices = []
    for i, s in enumerate(samples):
        if s.get("error") or not s.get("answer"):
            continue
        tc = LLMTestCase(
            input=s["input_text"],
            actual_output=s["answer"],
            expected_output=s["ground_truth"] or s["answer"],
            retrieval_context=s["contexts"] if s["contexts"] else [s["answer"]],
        )
        test_cases.append(tc)
        valid_indices.append(i)

    print(f"\n[deepeval] {len(test_cases)} valid test cases (skipped {len(samples) - len(test_cases)} errors)")
    print(f"[deepeval] Judge: deepseek-chat @ {_API_BASE}")
    print(f"[deepeval] Metrics: Faithfulness, Relevancy, Precision, Recall\n")

    results = evaluate(
        test_cases=test_cases,
        metrics=metrics,
        async_config=AsyncConfig(max_concurrent=2, throttle_value=5),
    )

    # Merge scores back into samples
    for j, tr in enumerate(results.test_results):
        idx = valid_indices[j]
        for m in tr.metrics_data:
            if m.name == "Faithfulness":
                samples[idx]["faithfulness"] = round(m.score, 4)
                samples[idx]["faithfulness_pass"] = m.success
            elif m.name == "Answer Relevancy":
                samples[idx]["relevancy"] = round(m.score, 4)
                samples[idx]["relevancy_pass"] = m.success
            elif m.name == "Contextual Precision":
                samples[idx]["context_precision"] = round(m.score, 4)
                samples[idx]["precision_pass"] = m.success
            elif m.name == "Contextual Recall":
                samples[idx]["context_recall"] = round(m.score, 4)
                samples[idx]["recall_pass"] = m.success

    return samples


# ---------------------------------------------------------------------------
# Step 3: Print report + save
# ---------------------------------------------------------------------------

def print_report(samples: list[dict]) -> dict:
    """Print aggregated report and save to file."""
    valid = [s for s in samples if not s.get("error") and s.get("answer")]
    total = len(samples)
    errors = total - len(valid)

    # Intent accuracy
    intent_correct = sum(
        1 for s in valid if s.get("actual_intent") == s.get("expected_intent")
    )
    intent_acc = intent_correct / len(valid) if valid else 0

    # Citation coverage
    with_citations = sum(1 for s in valid if s.get("has_citations"))
    citation_cov = with_citations / len(valid) if valid else 0

    # RAG metrics (averages)
    def _avg(key):
        vals = [s[key] for s in valid if key in s]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    avg_faith = _avg("faithfulness")
    avg_rel = _avg("relevancy")
    avg_prec = _avg("context_precision")
    avg_recall = _avg("context_recall")
    avg_duration = _avg("duration_ms")

    # Pass rates
    def _pass_rate(key):
        vals = [s[key] for s in valid if key in s]
        return round(sum(1 for v in vals if v) / len(vals), 4) if vals else 0.0

    faith_pass = _pass_rate("faithfulness_pass")
    rel_pass = _pass_rate("relevancy_pass")
    prec_pass = _pass_rate("precision_pass")
    recall_pass = _pass_rate("recall_pass")

    # Overall pass (all 4 DeepEval metrics pass)
    all_pass = sum(
        1 for s in valid
        if s.get("faithfulness_pass")
        and s.get("relevancy_pass")
        and s.get("precision_pass")
        and s.get("recall_pass")
    )
    overall_pass_rate = all_pass / len(valid) if valid else 0

    print("\n" + "=" * 60)
    print("  Evaluation Report")
    print("=" * 60)
    print(f"\nDataset: {total} cases ({errors} errors)")
    print(f"Duration: avg {avg_duration:.0f}ms per case\n")

    print("RAG Quality (DeepEval Judge: deepseek-chat)")
    print(f"  Faithfulness:         {avg_faith:.4f}  (pass: {faith_pass:.0%})")
    print(f"  Answer Relevancy:     {avg_rel:.4f}  (pass: {rel_pass:.0%})")
    print(f"  Contextual Precision: {avg_prec:.4f}  (pass: {prec_pass:.0%})")
    print(f"  Contextual Recall:    {avg_recall:.4f}  (pass: {recall_pass:.0%})")

    print(f"\nBusiness Metrics")
    print(f"  Intent Accuracy:      {intent_acc:.1%} ({intent_correct}/{len(valid)})")
    print(f"  Citation Coverage:    {citation_cov:.1%} ({with_citations}/{len(valid)})")
    print(f"  Overall Pass Rate:    {overall_pass_rate:.1%} ({all_pass}/{len(valid)})")

    # Per-case details
    print(f"\nPer-Case Details:")
    print("-" * 60)
    for s in samples:
        if s.get("error"):
            print(f"  ✗ {s['case_id']}: ERROR - {s['error'][:60]}")
            continue
        intent_ok = "✓" if s.get("actual_intent") == s.get("expected_intent") else "✗"
        faith = s.get("faithfulness", -1)
        rel = s.get("relevancy", -1)
        cit = "✓" if s.get("has_citations") else "✗"
        print(f"  {intent_ok} {s['case_id']}: "
              f"intent={s.get('actual_intent','?'):20s} "
              f"faith={faith:.2f} rel={rel:.2f} cit={cit}")

    # Save report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_cases": total,
        "valid_cases": len(valid),
        "error_cases": errors,
        "intent_accuracy": round(intent_acc, 4),
        "citation_coverage": round(citation_cov, 4),
        "overall_pass_rate": round(overall_pass_rate, 4),
        "avg_faithfulness": avg_faith,
        "avg_relevancy": avg_rel,
        "avg_context_precision": avg_prec,
        "avg_context_recall": avg_recall,
        "avg_duration_ms": round(avg_duration, 2),
        "results": samples,
    }

    report_dir = PROJECT_ROOT / "reports" / "eval"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"pipeline_eval_{ts}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[report] Saved to {report_path}")
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TicketPilot Pipeline Evaluation")
    parser.add_argument(
        "--dataset", default="data/eval/agent_eval_dataset_v2.json",
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit cases (0=all)")
    parser.add_argument("--force", action="store_true", help="Force re-collect samples")
    parser.add_argument("--skip-deepeval", action="store_true", help="Skip DeepEval, just collect")
    args = parser.parse_args()

    print("=" * 60)
    print("  TicketPilot Pipeline Evaluation")
    print("=" * 60)

    samples = collect_samples(
        dataset_path=str(PROJECT_ROOT / args.dataset),
        limit=args.limit,
        force=args.force,
    )

    if not args.skip_deepeval:
        samples = run_deepeval(samples)

    print_report(samples)


if __name__ == "__main__":
    main()
