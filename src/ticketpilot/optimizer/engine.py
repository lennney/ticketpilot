"""Optimization engine — main loop for the auto-optimizer.

Orchestrates the iterative cycle:
    evaluate → diagnose → fix top candidates → verify → commit/rollback → record

Each round attempts to improve the composite score by applying safe,
incremental fixes ranked by estimated gain.
"""
from __future__ import annotations

import logging
import sys
import time
from typing import Any

from ticketpilot.evaluation.schemas import EvaluationSummary
from ticketpilot.optimizer.config import (
    COMPOSITE_WEIGHTS,
    MAX_SINGLE_METRIC_DROP,
    MIN_CASES_FIXED,
    OptimizerConfig,
)
from ticketpilot.optimizer.diagnostics import DiagnosticsEngine, Diagnosis
from ticketpilot.optimizer.evaluator import OptimizerEvaluator
from ticketpilot.optimizer.fixer import Fixer, FixResult
from ticketpilot.optimizer.git_ops import commit, has_changes, revert
from ticketpilot.optimizer.history import OptimizationHistory
from ticketpilot.optimizer.reporter import IterationRecord, OptimizationReporter

logger = logging.getLogger(__name__)


def _print(msg: str) -> None:
    """Print to stdout immediately (for user-visible output)."""
    print(msg, flush=True)

# How many top diagnoses to try per round
TOP_N_FIXES = 5


class OptimizationEngine:
    """Main optimization loop.

    Args:
        max_rounds: Maximum number of optimization rounds.
        diagnose_only: If ``True``, run diagnostics and report but don't apply fixes.
        dry_run: If ``True``, the fixer will log intended changes without writing files.
        resume: If ``True``, resume from the last saved state instead of starting fresh.
    """

    def __init__(
        self,
        max_rounds: int = 20,
        diagnose_only: bool = False,
        dry_run: bool = False,
        resume: bool = False,
    ) -> None:
        self.config = OptimizerConfig(
            max_rounds=max_rounds,
            diagnose_only=diagnose_only,
            dry_run=dry_run,
            resume=resume,
        )
        self.evaluator = OptimizerEvaluator(self.config)
        self.diagnostics = DiagnosticsEngine(weights=self.config.weights)
        self.fixer = Fixer(dry_run=dry_run)
        self.history = OptimizationHistory(self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Execute the full optimization loop.

        Returns:
            ``True`` if at least one improvement was committed, ``False`` otherwise.
        """
        # Load dataset
        _print("═══ TicketPilot Auto-Optimizer ═══")
        logger.info("Loading evaluation dataset...")
        self.evaluator.load_dataset()
        dataset_count = len(self.evaluator.dataset.tickets) if hasattr(self.evaluator, "dataset") and hasattr(self.evaluator.dataset, "tickets") else "?"
        _print(f"✅ Loaded {dataset_count} eval tickets")

        # Initialize history
        self.history.init(clear=not self.config.resume)

        # Get baseline
        _print("\n─── Baseline Evaluation ───")
        logger.info("Running baseline evaluation...")
        baseline_summary = self.evaluator.get_baseline()
        baseline_composite = self._compute_composite(baseline_summary)
        baseline_correct = self._extract_correct_ids(baseline_summary)
        scores = self._score_dict(baseline_summary)
        _print(f"Baseline composite: {baseline_composite:.4f} ({len(baseline_correct)}/101 correct)")
        _print(f"  intent={scores['intent']:.2%}  severity={scores['severity']:.2%}  risk_f1={scores['risk_f1']:.2%}  evidence={scores['evidence']:.2%}  no_auto_send={scores['no_auto_send']:.2%}  fallback={scores['fallback']:.2%}")
        logger.info(
            "Baseline composite: %.4f (%d correct cases)",
            baseline_composite,
            len(baseline_correct),
        )

        # Record baseline
        self.history.record({
            "iteration": 0,
            "composite": baseline_composite,
            "correct_cases": len(baseline_correct),
            "total_cases": baseline_summary.total_cases,
            "metrics": self._score_dict(baseline_summary),
            "timestamp": _now_iso(),
            "description": "baseline",
        })

        # Diagnose-only mode
        if self.config.diagnose_only:
            diagnoses = self.diagnostics.analyze(
                baseline_summary, self.evaluator.dataset.tickets
            )
            _print(f"\n═══ Diagnose-Only Mode ═══")
            _print(f"Found {len(diagnoses)} issues:")
            for i, d in enumerate(diagnoses, 1):
                _print(f"  {i}. [{d.type}] {d.description} (gain={d.fix_gain:.4f})")
            logger.info("Diagnose-only mode: %d diagnoses found", len(diagnoses))
            for d in diagnoses:
                logger.info("  [%s] %s (gain=%.4f)", d.type, d.description, d.fix_gain)
            return False

        # Main loop
        current_composite = baseline_composite
        current_correct_ids = baseline_correct
        current_summary = baseline_summary
        any_improvement = False

        for iteration in range(1, self.config.max_rounds + 1):
            _print(f"\n═══ Round {iteration}/{self.config.max_rounds} ═══ (composite={current_composite:.4f})")
            logger.info(
                "=== Round %d/%d (composite=%.4f) ===",
                iteration,
                self.config.max_rounds,
                current_composite,
            )

            improved = self._run_one_round(
                iteration, current_summary, current_correct_ids
            )

            if improved:
                # Re-evaluate to get the new state
                current_summary = self.evaluator.run_full_evaluation()
                current_composite = self._compute_composite(current_summary)
                current_correct_ids = self._extract_correct_ids(current_summary)
                any_improvement = True
                _print(f"✓ Round {iteration}: improved → composite={current_composite:.4f} ({len(current_correct_ids)} correct)")
                logger.info(
                    "Round %d: improved → composite=%.4f (%d correct)",
                    iteration,
                    current_composite,
                    len(current_correct_ids),
                )
            else:
                _print(f"✗ Round {iteration}: no improvement")
                logger.info("Round %d: no improvement", iteration)

            # Check early termination (perfect score)
            if current_composite >= 1.0:
                _print("🎯 Perfect composite score achieved, stopping.")
                logger.info("Perfect composite score achieved, stopping.")
                break

        # Final summary
        delta = current_composite - baseline_composite
        _print(f"\n═══ Optimization Complete ═══")
        _print(f"Composite: {baseline_composite:.4f} → {current_composite:.4f} ({delta:+.4f})")
        logger.info(
            "Optimization complete. Final composite: %.4f", current_composite
        )

        # Generate report
        _print("\n─── Report Generation ───")
        self._generate_report(baseline_summary, current_summary, any_improvement)

        return any_improvement

    def show_history(self) -> list[dict[str, Any]]:
        """Display past optimization runs.

        Returns:
            List of iteration records from the history file.
        """
        records = self.history.load()
        if not records:
            logger.info("No optimization history found.")
            return records

        logger.info("=== Optimization History (%d iterations) ===", len(records))
        for rec in records:
            iteration = rec.get("iteration", "?")
            composite = rec.get("composite", 0.0)
            desc = rec.get("description", "")
            logger.info(
                "  #%s: composite=%.4f — %s", iteration, composite, desc
            )
        return records

    # ------------------------------------------------------------------
    # Single round
    # ------------------------------------------------------------------

    def _run_one_round(
        self,
        iteration: int,
        old_summary: EvaluationSummary,
        old_correct_ids: set[str],
    ) -> bool:
        """Execute a single optimization round.

        1. Diagnose current failures
        2. Try the top N fixes (by estimated gain)
        3. Verify each fix improves the score
        4. Commit successful fixes; rollback failures

        Returns:
            ``True`` if at least one fix was accepted in this round.
        """
        diagnoses = self.diagnostics.analyze(
            old_summary, self.evaluator.dataset.tickets
        )

        if not diagnoses:
            _print("⚠ No diagnoses found, nothing to fix.")
            logger.info("Round %d: no diagnoses, nothing to fix.", iteration)
            self.history.record({
                "iteration": iteration,
                "composite": self._compute_composite(old_summary),
                "correct_cases": len(old_correct_ids),
                "total_cases": old_summary.total_cases,
                "metrics": self._score_dict(old_summary),
                "timestamp": _now_iso(),
                "description": "no diagnoses",
                "fixes_tried": 0,
                "fixes_accepted": 0,
            })
            return False

        # Take top N by gain
        candidates = diagnoses[:TOP_N_FIXES]
        top_desc = ", ".join(f"{d.type}" for d in candidates[:3])
        _print(f"⚠ Diagnosed {len(diagnoses)} issues, top: {top_desc}")
        logger.info(
            "Round %d: %d diagnoses, trying top %d",
            iteration,
            len(diagnoses),
            len(candidates),
        )

        accepted_any = False
        fixes_tried = 0
        fixes_accepted = 0

        for diag in candidates:
            fixes_tried += 1
            _print(f"Trying fix: [{diag.type}] {diag.suggested_fix_type} (gain={diag.fix_gain:.4f})")
            logger.info(
                "  Trying fix: [%s] %s (gain=%.4f)",
                diag.type,
                diag.suggested_fix_type,
                diag.fix_gain,
            )

            fix_result = self.fixer.apply_fix(diag)

            if not fix_result.success:
                _print(f"✗ Fix failed: {fix_result.fix_type} — {fix_result.error or fix_result.description}")
                logger.warning(
                    "  Fix failed: %s — %s",
                    fix_result.fix_type,
                    fix_result.error or fix_result.description,
                )
                continue

            # Verify improvement
            improved, new_summary, new_composite = self._verify_fix(
                old_summary, old_correct_ids
            )

            if improved:
                # Commit the fix
                msg = (
                    f"optimizer round {iteration}: {diag.suggested_fix_type} "
                    f"({diag.type}, composite={new_composite:.4f})"
                )
                sha = commit(message=msg)
                fixes_accepted += 1
                accepted_any = True
                _print(f"✅ OK: {msg} → {sha[:8]}")
                logger.info("  Accepted fix, committed %s", sha[:8])

                self.history.record({
                    "iteration": iteration,
                    "composite": new_composite,
                    "correct_cases": len(self._extract_correct_ids(new_summary)),
                    "total_cases": new_summary.total_cases,
                    "metrics": self._score_dict(new_summary),
                    "timestamp": _now_iso(),
                    "description": f"accepted: {diag.suggested_fix_type}",
                    "fix_type": diag.suggested_fix_type,
                    "diagnosis_type": diag.type,
                    "commit_sha": sha,
                    "fix_gain_actual": new_composite - self._compute_composite(old_summary),
                })
            else:
                # Rollback
                self.fixer.rollback()
                _print(f"✗ Rolled back: no improvement after {diag.suggested_fix_type}")
                logger.info("  Reverted fix (no improvement)")
                self.history.record({
                    "iteration": iteration,
                    "composite": self._compute_composite(old_summary),
                    "correct_cases": len(old_correct_ids),
                    "total_cases": old_summary.total_cases,
                    "metrics": self._score_dict(old_summary),
                    "timestamp": _now_iso(),
                    "description": f"reverted: {diag.suggested_fix_type}",
                    "fix_type": diag.suggested_fix_type,
                    "diagnosis_type": diag.type,
                })

        final_composite = (
            self._compute_composite(old_summary)
            if not accepted_any
            else None  # will use last known value
        )
        if final_composite is None:
            # At least one fix was accepted; re-evaluate to get current state
            final_summary = self.evaluator.run_full_evaluation()
            final_composite = self._compute_composite(final_summary)

        self.history.save_state({
            "iteration": iteration,
            "composite": final_composite,
        })

        return accepted_any

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_report(
        self,
        baseline_summary: EvaluationSummary,
        final_summary: EvaluationSummary,
        any_improvement: bool,
    ) -> None:
        """Generate and save an optimization report.

        Builds a Markdown report from the history records and saves it
        to the configured report path.
        """
        reporter = OptimizationReporter(self.config)
        iterations = self.history.load()

        # Build IterationRecord list from history
        iter_records: list[IterationRecord] = []
        for rec in iterations:
            if rec.get("iteration", 0) == 0:
                continue  # Skip baseline
            iter_records.append(
                IterationRecord(
                    round_num=rec.get("iteration", 0),
                    fix_description=rec.get("description", ""),
                    committed=rec.get("commit_sha") is not None,
                    timestamp=rec.get("timestamp"),
                )
            )

        md = reporter.generate(iter_records, baseline=baseline_summary, final=final_summary)
        path = reporter.save(md)
        _print(f"✅ Report saved to {path}")

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify_fix(
        self,
        old_summary: EvaluationSummary,
        old_correct_ids: set[str],
    ) -> tuple[bool, EvaluationSummary, float]:
        """Re-evaluate after applying a fix and check for improvement.

        A fix is accepted if:
        1. Composite score improved, AND
        2. No single metric dropped by more than MAX_SINGLE_METRIC_DROP, AND
        3. At least MIN_CASES_FIXED new correct cases (net gain).

        Returns:
            (improved, new_summary, new_composite)
        """
        new_summary = self.evaluator.run_full_evaluation()
        new_composite = self._compute_composite(new_summary)
        old_composite = self._compute_composite(old_summary)

        # Check composite improved
        if new_composite <= old_composite:
            return False, new_summary, new_composite

        # Check no single metric regressed too much
        old_scores = self._score_dict(old_summary)
        new_scores = self._score_dict(new_summary)
        for metric_name in old_scores:
            drop = old_scores[metric_name] - new_scores[metric_name]
            if drop > MAX_SINGLE_METRIC_DROP:
                logger.warning(
                    "Metric '%s' dropped by %.4f (limit %.4f)",
                    metric_name,
                    drop,
                    MAX_SINGLE_METRIC_DROP,
                )
                return False, new_summary, new_composite

        # Check minimum cases fixed
        new_correct_ids = self._extract_correct_ids(new_summary)
        net_gain = len(new_correct_ids - old_correct_ids)
        net_loss = len(old_correct_ids - new_correct_ids)
        net = net_gain - net_loss
        if net < MIN_CASES_FIXED:
            logger.info(
                "Insufficient net improvement: +%d -%d = %d (need ≥%d)",
                net_gain,
                net_loss,
                net,
                MIN_CASES_FIXED,
            )
            return False, new_summary, new_composite

        return True, new_summary, new_composite

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _compute_composite(self, summary: EvaluationSummary) -> float:
        """Compute the weighted composite score from an evaluation summary.

        Uses the weights from ``COMPOSITE_WEIGHTS``:
            intent * 0.25 + severity * 0.20 + risk_f1 * 0.20
            + evidence * 0.15 + no_auto_send * 0.10 + fallback * 0.10

        Returns:
            Float in [0.0, 1.0].
        """
        scores = self._score_dict(summary)
        return sum(
            scores[metric] * weight
            for metric, weight in self.config.weights.items()
        )

    def _score_dict(self, summary: EvaluationSummary) -> dict[str, float]:
        """Extract the metric dict used for composite scoring.

        Returns:
            Dict mapping metric names to their float values:
            ``intent``, ``severity``, ``risk_f1``, ``evidence``,
            ``no_auto_send``, ``fallback``.
        """
        return {
            "intent": summary.aggregate_intent_accuracy,
            "severity": summary.aggregate_severity_accuracy,
            "risk_f1": summary.aggregate_risk_flag_f1,
            "evidence": summary.aggregate_evidence_doc_type_recall,
            "no_auto_send": summary.aggregate_no_auto_send_compliance,
            "fallback": summary.aggregate_fallback_correctness,
        }

    @staticmethod
    def _extract_correct_ids(summary: EvaluationSummary) -> set[str]:
        """Get the set of case IDs where all metrics are correct.

        A case is "correct" if its intent accuracy, severity accuracy,
        risk flag exact match, fallback correctness, and no_auto_send
        compliance are all ``True``.
        """
        correct: set[str] = set()
        for case_id, case in summary.results.items():
            m = case.metrics
            if (
                m.intent_accuracy
                and m.severity_accuracy
                and m.risk_flag_metrics.exact_match
                and m.fallback_correctness
                and m.no_auto_send_compliance
            ):
                correct.add(case_id)
        return correct


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as ISO string."""
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
