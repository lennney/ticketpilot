"""Evaluation harness for the auto-optimizer.

Runs the TicketPilot pipeline on all eval tickets, computes metrics
against golden expectations, and caches the baseline for comparison.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# Module-level thread pool singleton — reused across all evaluate() calls
_pool: ThreadPoolExecutor | None = None


def _get_pool() -> ThreadPoolExecutor:
    """Return a shared ThreadPoolExecutor (created once, reused)."""
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=4)
    return _pool


from ticketpilot.evaluation.loaders import load_eval_dataset
from ticketpilot.evaluation.metrics import compute_evaluation_summary
from ticketpilot.evaluation.pipeline_predictions import predict_from_pipeline
from ticketpilot.evaluation.schemas import (
    EvalDataset,
    EvalPrediction,
    EvaluationSummary,
    GoldenExpectation,
)
from ticketpilot.optimizer.config import OptimizerConfig

logger = logging.getLogger(__name__)


class OptimizerEvaluator:
    """Runs full pipeline evaluation and caches baseline results.

    Usage::

        evaluator = OptimizerEvaluator(config)
        evaluator.load_dataset()
        summary = evaluator.run_full_evaluation()
        baseline = evaluator.get_baseline()  # same as summary, cached
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()
        self._dataset: EvalDataset | None = None
        self._predictions: dict[str, EvalPrediction] = {}
        self._baseline: EvaluationSummary | None = None

    # ------------------------------------------------------------------
    # Dataset loading
    # ------------------------------------------------------------------

    def load_dataset(self) -> EvalDataset:
        """Load tickets and golden expectations from configured CSV paths.

        Returns:
            The validated EvalDataset (also stored as ``self._dataset``).

        Raises:
            ValueError: If the dataset is invalid (missing mappings, etc.).
        """
        result = load_eval_dataset(self.config.tickets_csv, self.config.golden_csv)
        if not result.is_valid:
            errors = (
                result.missing_golden_for_ticket
                + result.missing_ticket_for_golden
                + result.errors
            )
            raise ValueError("Eval dataset validation failed:\n" + "\n".join(errors))
        self._dataset = result.dataset
        logger.info(
            "Loaded eval dataset: %d tickets, %d golden expectations",
            self._dataset.ticket_count,
            self._dataset.golden_count,
        )
        return self._dataset

    @property
    def dataset(self) -> EvalDataset:
        """Return the loaded dataset, raising if not yet loaded."""
        if self._dataset is None:
            raise RuntimeError("Call load_dataset() first")
        return self._dataset

    # ------------------------------------------------------------------
    # Prediction generation
    # ------------------------------------------------------------------

    def _generate_predictions(self) -> dict[str, EvalPrediction]:
        """Run the pipeline on every ticket in parallel and collect predictions."""
        ds = self.dataset
        predictions: dict[str, EvalPrediction] = {}
        total = ds.ticket_count
        items = list(ds.tickets.items())

        pool = _get_pool()
        futures = {
            pool.submit(predict_from_pipeline, ticket, True): case_id
            for case_id, ticket in items
        }
        for future in as_completed(futures):
            case_id = futures[future]
            try:
                predictions[case_id] = future.result()
            except Exception:
                logger.exception("Pipeline failed for %s", case_id)
                raise

        logger.info("Predictions complete: %d/%d tickets", len(predictions), total)
        return predictions

    # ------------------------------------------------------------------
    # Partial (incremental) evaluation
    # ------------------------------------------------------------------

    def run_partial_evaluation(
        self,
        affected_case_ids: set[str],
        previous_predictions: dict[str, EvalPrediction] | None = None,
    ) -> EvaluationSummary:
        """Run evaluation on only affected tickets, reusing previous predictions
        for the rest.

        Args:
            affected_case_ids: Set of case IDs that need re-prediction.
            previous_predictions: Previous predictions dict. When provided,
                unaffected tickets reuse their previous results.
                When None, runs full evaluation (backward compatible fallback).

        Returns:
            EvaluationSummary with updated per-case and aggregate metrics.
        """
        ds = self.dataset

        # Start with previous predictions (or empty)
        if previous_predictions is not None:
            predictions = dict(previous_predictions)
        else:
            predictions = {}

        # Re-predict affected tickets in parallel
        affected_tickets = [
            (case_id, ds.tickets[case_id])
            for case_id in affected_case_ids
            if case_id in ds.tickets
        ]
        if affected_tickets:
            pool = _get_pool()
            futures = {
                pool.submit(predict_from_pipeline, ticket, True): case_id
                for case_id, ticket in affected_tickets
            }
            for future in as_completed(futures):
                case_id = futures[future]
                try:
                    predictions[case_id] = future.result()
                except Exception:
                    logger.exception("Pipeline failed for %s", case_id)
                    raise

        # If no previous predictions, fill in the rest (also in parallel)
        if previous_predictions is None:
            remaining = [
                (case_id, ticket)
                for case_id, ticket in ds.tickets.items()
                if case_id not in predictions
            ]
            if remaining:
                pool = _get_pool()
                futures = {
                    pool.submit(predict_from_pipeline, ticket, True): case_id
                    for case_id, ticket in remaining
                }
                for future in as_completed(futures):
                    case_id = futures[future]
                    try:
                        predictions[case_id] = future.result()
                    except Exception:
                        logger.exception("Pipeline failed for %s", case_id)
                        raise

        self._predictions = predictions
        summary = compute_evaluation_summary(predictions, ds.golden)
        return summary

    # ------------------------------------------------------------------
    # Full evaluation
    # ------------------------------------------------------------------

    def run_full_evaluation(self) -> EvaluationSummary:
        """Run predictions for all tickets and compute evaluation metrics.

        Returns:
            EvaluationSummary with per-case and aggregate metrics.
        """
        ds = self.dataset
        self._predictions = self._generate_predictions()
        summary = compute_evaluation_summary(self._predictions, ds.golden)
        logger.info(
            "Evaluation complete: %d cases, intent=%.2f%%, severity=%.2f%%, "
            "risk_f1=%.2f%%",
            summary.total_cases,
            summary.aggregate_intent_accuracy * 100,
            summary.aggregate_severity_accuracy * 100,
            summary.aggregate_risk_flag_f1 * 100,
        )
        return summary

    # ------------------------------------------------------------------
    # Baseline caching
    # ------------------------------------------------------------------

    def get_baseline(self) -> EvaluationSummary:
        """Return the baseline evaluation, running it if not cached.

        Subsequent calls return the cached result without re-running.
        """
        if self._baseline is None:
            self._baseline = self.run_full_evaluation()
        return self._baseline

    def clear_baseline(self) -> None:
        """Clear the cached baseline so the next get_baseline() re-runs."""
        self._baseline = None

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def predictions(self) -> dict[str, EvalPrediction]:
        """Return the last prediction dict (empty until first evaluation)."""
        return self._predictions

    def get_golden(self) -> dict[str, GoldenExpectation]:
        """Return the golden expectations dict from the loaded dataset."""
        return self.dataset.golden
