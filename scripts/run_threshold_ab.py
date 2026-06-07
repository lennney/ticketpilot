"""A/B threshold tuning experiment.

Compare two confidence threshold configurations:
- Control (current):  HIGH >= 0.78, MEDIUM >= 0.60, LOW >= 0.40
- Treatment (strict): HIGH >= 0.85, MEDIUM >= 0.65, LOW >= 0.45

Metrics:
- auto_send_rate:   HIGH + MEDIUM proportion (higher = more efficient)
- review_rate:      LOW proportion (lower = better, but not zero)
- risk_miss_rate:   CRITICAL tickets that have high-risk flags (must be 0%)
"""

from __future__ import annotations

import csv
import pathlib
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

# Ensure project root is on path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from ticketpilot.confidence import scorer as scorer_mod
from ticketpilot.confidence.scorer import ConfidenceLevel
from ticketpilot.pipeline import intake_risk_pipeline, post_process
from ticketpilot.schema.ticket import RawTicket, RiskFlag, RiskSeverity

EVAL_TICKETS_PATH = pathlib.Path("data/eval/tickets_eval.csv")


def _load_tickets(path: pathlib.Path) -> list[RawTicket]:
    """Load RawTickets from eval CSV."""
    tickets: list[RawTicket] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append(
                RawTicket(
                    original_text=row["original_text"].strip(),
                    submitted_at=datetime.fromisoformat(
                        row["submitted_at"].replace("Z", "+00:00")
                    ),
                    customer_id=row.get("customer_id", "").strip() or None,
                )
            )
    return tickets


@contextmanager
def _apply_thresholds(overrides: dict[str, float]):
    """Temporarily patch scorer thresholds, then restore."""
    saved = dict(scorer_mod.THRESHOLDS)
    scorer_mod.THRESHOLDS.update(overrides)
    try:
        yield
    finally:
        scorer_mod.THRESHOLDS.clear()
        scorer_mod.THRESHOLDS.update(saved)


def _run_variant(
    tickets: list[RawTicket],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Run all tickets under given thresholds and collect metrics."""
    tier_counts: Counter[str] = Counter()
    high_risk_in_critical = 0
    critical_count = 0

    with _apply_thresholds(thresholds):
        for ticket in tickets:
            output = intake_risk_pipeline(ticket)
            confidence, _ = post_process(output)

            tier = confidence.level.value
            tier_counts[tier] += 1

            if confidence.level == ConfidenceLevel.CRITICAL:
                critical_count += 1
                has_high_risk = any(
                    f in (RiskFlag.LEGAL_RISK, RiskFlag.COMPLAINT_RISK, RiskFlag.ACCOUNT_SECURITY_RISK)
                    for f in output.risk_assessment.flags
                )
                if has_high_risk:
                    high_risk_in_critical += 1

    total = len(tickets)
    auto_send = tier_counts.get("high", 0) + tier_counts.get("medium", 0)
    review = tier_counts.get("low", 0)
    risk_miss = high_risk_in_critical

    return {
        "ticket_count": total,
        "tier_distribution": dict(tier_counts),
        "auto_send_rate": round(auto_send / total * 100, 1) if total else 0.0,
        "review_rate": round(review / total * 100, 1) if total else 0.0,
        "risk_miss_rate": round(risk_miss / critical_count * 100, 1) if critical_count else 0.0,
        "risk_miss_count": risk_miss,
        "critical_count": critical_count,
    }


def main() -> None:
    tickets = _load_tickets(EVAL_TICKETS_PATH)
    print(f"Loaded {len(tickets)} eval tickets\n")

    variants = [
        {
            "name": "current",
            "description": "HIGH>=0.78, MEDIUM>=0.6, LOW>=0.4",
            "thresholds": {"high": 0.78, "medium": 0.6, "low": 0.4},
        },
        {
            "name": "strict",
            "description": "HIGH>=0.85, MEDIUM>=0.65, LOW>=0.45",
            "thresholds": {"high": 0.85, "medium": 0.65, "low": 0.45},
        },
    ]

    for variant in variants:
        print(f"Variant: {variant['name']}")
        print(f"  description: {variant['description']}")

        result = _run_variant(tickets, variant["thresholds"])

        print(f"  auto_send_rate: {result['auto_send_rate']}%")
        print(f"  review_rate: {result['review_rate']}%")
        print(f"  risk_miss_rate: {result['risk_miss_rate']}%")
        print(f"  tier_distribution: {result['tier_distribution']}")
        print()


if __name__ == "__main__":
    main()
