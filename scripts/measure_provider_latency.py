#!/usr/bin/env python3
"""Measure real provider latency on Phase 12 eval tickets.

Requires DEEPSEEK_API_KEY in environment. Without it, prints SKIPPED and exits 0.
"""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

EVAL_CSV = Path(__file__).resolve().parent.parent / "data" / "eval" / "tickets_eval.csv"
NUM_CASES = 25


def load_tickets(csv_path: Path, limit: int) -> list[dict]:
    """Load the first `limit` tickets from the eval CSV."""
    tickets: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append(row)
            if len(tickets) >= limit:
                break
    return tickets


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("SKIPPED: no API key")
        sys.exit(0)

    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    from ticketpilot.schema.ticket import RawTicket
    from ticketpilot.pipeline import intake_risk_pipeline
    from ticketpilot.drafting.generator import generate_draft
    from ticketpilot.drafting.llm_provider import OpenAICompatibleProvider
    from datetime import datetime, timezone

    provider = OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )

    tickets_data = load_tickets(EVAL_CSV, NUM_CASES)
    print(f"Loaded {len(tickets_data)} tickets for latency measurement")
    print(f"Provider: {provider.provider_name} / {provider.model_name}")
    print()

    results: list[dict] = []

    for i, row in enumerate(tickets_data):
        raw = RawTicket(
            original_text=row["original_text"],
            submitted_at=datetime.now(timezone.utc),
            customer_id=row.get("customer_id", ""),
        )

        # Pipeline (deterministic, fast)
        start_pipeline = time.perf_counter()
        ticket_output = intake_risk_pipeline(raw)
        pipeline_ms = (time.perf_counter() - start_pipeline) * 1000

        # Draft generation (API call, measured)
        start_draft = time.perf_counter()
        draft_result = generate_draft(ticket_output, provider=provider)
        draft_s = time.perf_counter() - start_draft

        draft = draft_result.draft
        results.append({
            "case_id": row["case_id"],
            "pipeline_ms": round(pipeline_ms, 1),
            "draft_latency_s": round(draft_s, 3),
            "confidence": round(draft.confidence, 3),
            "must_human_review": draft.must_human_review,
        })

        status = "REVIEW" if draft.must_human_review else "OK"
        print(
            f"  [{i+1:2d}/{len(tickets_data)}] {row['case_id']:<20s} "
            f"latency={draft_s:.3f}s  conf={draft.confidence:.3f}  {status}"
        )

    # Summary
    latencies = [r["draft_latency_s"] for r in results]
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    review_count = sum(1 for r in results if r["must_human_review"])

    print()
    print("=" * 60)
    print(f"Average latency: {avg_latency:.3f}s")
    print(f"Median (P50):    {p50:.3f}s")
    print(f"Min / Max:       {min_latency:.3f}s / {max_latency:.3f}s")
    print(f"Total cases:     {len(results)}")
    print(f"Human review:    {review_count}/{len(results)} ({100*review_count/len(results):.0f}%)")
    print(f"Estimated cost per ticket: N/A (token pricing varies by provider)")
    print("=" * 60)


if __name__ == "__main__":
    main()
