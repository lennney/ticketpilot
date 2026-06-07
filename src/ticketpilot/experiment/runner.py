"""Experiment runner — executes tickets through two configs and compares."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any

from ticketpilot.confidence import scorer as scorer_mod
from ticketpilot.experiment.config import ExperimentConfig
from ticketpilot.experiment.reporter import ExperimentReport
from ticketpilot.pipeline import intake_risk_pipeline, post_process
from ticketpilot.schema.ticket import RawTicket

logger = logging.getLogger(__name__)

# Keys that can be overridden in the scorer module
_VALID_SCORER_KEYS = {"weights", "thresholds"}


@contextmanager
def _apply_config(overrides: dict[str, Any]):
    """Temporarily patch scorer module-level constants, then restore."""
    if not overrides:
        yield
        return

    saved_weights = dict(scorer_mod.WEIGHTS)
    saved_thresholds = dict(scorer_mod.THRESHOLDS)

    if "weights" in overrides:
        scorer_mod.WEIGHTS.update(overrides["weights"])
    if "thresholds" in overrides:
        scorer_mod.THRESHOLDS.update(overrides["thresholds"])

    try:
        yield
    finally:
        scorer_mod.WEIGHTS.clear()
        scorer_mod.WEIGHTS.update(saved_weights)
        scorer_mod.THRESHOLDS.clear()
        scorer_mod.THRESHOLDS.update(saved_thresholds)


def _run_group(
    tickets: list[RawTicket],
    config_overrides: dict[str, Any],
) -> dict[str, Any]:
    """Run all tickets under one configuration and collect metrics."""
    intents_correct = 0
    total_confidence = 0.0
    total_latency = 0.0
    must_review_count = 0
    count = len(tickets)

    with _apply_config(config_overrides):
        for ticket in tickets:
            start = time.perf_counter()
            output = intake_risk_pipeline(ticket)
            confidence, degraded = post_process(output)
            elapsed = time.perf_counter() - start

            # Classification confidence as a proxy for intent accuracy
            if output.classification.confidence >= 0.5:
                intents_correct += 1

            total_confidence += confidence.overall
            total_latency += elapsed

            if output.risk_assessment.must_human_review:
                must_review_count += 1

    if count == 0:
        return {
            "intent_accuracy": 0.0,
            "avg_confidence": 0.0,
            "avg_latency_ms": 0.0,
            "must_human_review_rate": 0.0,
            "ticket_count": 0,
        }

    return {
        "intent_accuracy": round(intents_correct / count, 4),
        "avg_confidence": round(total_confidence / count, 4),
        "avg_latency_ms": round(total_latency / count * 1000, 2),
        "must_human_review_rate": round(must_review_count / count, 4),
        "ticket_count": count,
    }


def _compute_delta(control: dict[str, Any], treatment: dict[str, Any]) -> dict[str, Any]:
    """Compute treatment - control for numeric keys."""
    delta: dict[str, Any] = {}
    for key in set(control) | set(treatment):
        c_val = control.get(key)
        t_val = treatment.get(key)
        if isinstance(c_val, (int, float)) and isinstance(t_val, (int, float)):
            delta[key] = round(t_val - c_val, 4)
        else:
            delta[key] = None
    return delta


class ExperimentRunner:
    """Runs the same tickets through two configurations and produces a report.

    Usage:
        runner = ExperimentRunner()
        report = runner.run(tickets, config)
        print(report.to_markdown())
    """

    def run(
        self,
        tickets: list[RawTicket],
        config: ExperimentConfig,
    ) -> ExperimentReport:
        """Execute the experiment.

        Args:
            tickets: List of RawTicket objects to process.
            config: ExperimentConfig with control/treatment overrides.

        Returns:
            ExperimentReport with metrics and delta.
        """
        logger.info(
            "Running experiment '%s' (%s) with %d tickets",
            config.name,
            config.experiment_id,
            len(tickets),
        )

        control_results = _run_group(tickets, config.control)
        treatment_results = _run_group(tickets, config.treatment)
        delta = _compute_delta(control_results, treatment_results)

        return ExperimentReport(
            experiment_id=config.experiment_id,
            name=config.name,
            control_results=control_results,
            treatment_results=treatment_results,
            delta=delta,
        )
