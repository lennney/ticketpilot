"""Optimization engine — main loop for the auto-optimizer.

Orchestrates the iterative cycle:
    evaluate → diagnose → fix top candidates → verify → commit/rollback → record

Each round attempts to improve the composite score by applying safe,
incremental fixes ranked by estimated gain.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import os
from typing import Any

from ticketpilot.evaluation.schemas import EvalPrediction, EvaluationSummary
from ticketpilot.optimizer.config import (
    MAX_SINGLE_METRIC_DROP,
    MIN_CASES_FIXED,
    OptimizerConfig,
)
from ticketpilot.optimizer.diagnostics import (
    DiagnosticsEngine,
    Diagnosis,
    TYPE_INTENT_MISMATCH,
)
from ticketpilot.optimizer.evaluator import OptimizerEvaluator
from ticketpilot.optimizer.fixer import Fixer
from ticketpilot.optimizer.scoring import (
    compute_composite,
    score_dict,
    extract_correct_ids,
)
from ticketpilot.optimizer.tradeoff import analyze_keyword_tradeoff
from ticketpilot.optimizer.llm_reviewer import review_keyword
from ticketpilot.optimizer.git_ops import commit
from ticketpilot.optimizer.history import OptimizationHistory
from ticketpilot.optimizer.reporter import IterationRecord, OptimizationReporter

logger = logging.getLogger(__name__)


def _print(msg: str) -> None:
    """Print to stdout immediately (for user-visible output)."""
    print(msg, flush=True)


# How many top diagnoses to try per round
TOP_N_FIXES = 5

# 提前终止：连续 N 轮无改进则停止
CONSECUTIVE_NO_IMPROVEMENT_LIMIT = 3

# Persistent debug log path
_DEBUG_LOG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "reports"
    / "optimization"
    / "debug_log.jsonl"
)


def _debug_log(entry: dict[str, Any]) -> None:
    """Write a JSONL entry to the persistent debug log.

    Appends to ``reports/optimization/debug_log.jsonl``.
    Thread-safe for single-process writes.
    """
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


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
            llm_api_key=os.getenv("OPTIMIZER_LLM_API_KEY", ""),
            llm_base_url=os.getenv("OPTIMIZER_LLM_BASE_URL", ""),
            llm_model=os.getenv("OPTIMIZER_LLM_MODEL", ""),
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
        dataset_count = (
            len(self.evaluator.dataset.tickets)
            if hasattr(self.evaluator, "dataset")
            and hasattr(self.evaluator.dataset, "tickets")
            else "?"
        )
        _print(f"✅ Loaded {dataset_count} eval tickets")

        # Log run start
        _debug_log(
            {
                "event": "run_start",
                "max_rounds": self.config.max_rounds,
                "diagnose_only": self.config.diagnose_only,
                "dry_run": self.config.dry_run,
                "resume": self.config.resume,
                "has_llm_key": bool(self.config.llm_api_key),
                "weights": dict(self.config.weights),
                "dataset_size": dataset_count,
            }
        )

        # Initialize history
        self.history.init(clear=not self.config.resume)

        # Get baseline
        _print("\n─── Baseline Evaluation ───")
        logger.info("Running baseline evaluation...")
        baseline_summary = self.evaluator.get_baseline()
        baseline_composite = compute_composite(baseline_summary, self.config.weights)
        baseline_correct = extract_correct_ids(baseline_summary)
        scores = score_dict(baseline_summary)
        _print(
            f"Baseline composite: {baseline_composite:.4f} ({len(baseline_correct)}/101 correct)"
        )
        _print(
            f"  intent={scores['intent']:.2%}  severity={scores['severity']:.2%}  risk_f1={scores['risk_f1']:.2%}  evidence={scores['evidence']:.2%}  no_auto_send={scores['no_auto_send']:.2%}  fallback={scores['fallback']:.2%}"
        )
        logger.info(
            "Baseline composite: %.4f (%d correct cases)",
            baseline_composite,
            len(baseline_correct),
        )

        # Record baseline
        self.history.record(
            {
                "iteration": 0,
                "composite": baseline_composite,
                "correct_cases": len(baseline_correct),
                "total_cases": baseline_summary.total_cases,
                "metrics": score_dict(baseline_summary),
                "timestamp": _now_iso(),
                "description": "baseline",
            }
        )

        # Log baseline
        _debug_log(
            {
                "event": "baseline",
                "composite": round(baseline_composite, 4),
                "correct_cases": len(baseline_correct),
                "total_cases": baseline_summary.total_cases,
                "metrics": scores,
                "rounds_per_metric": {
                    k: round(v / (scores.get(k, 0.01) or 0.01), 4)
                    for k, v in self.config.weights.items()
                },
            }
        )

        # Diagnose-only mode
        if self.config.diagnose_only:
            diagnoses = self.diagnostics.analyze(
                baseline_summary, self.evaluator.dataset.tickets
            )
            _print("\n═══ Diagnose-Only Mode ═══")
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

        # 最佳状态追踪
        best_composite = baseline_composite
        best_iteration = 0
        self._best_composite = best_composite  # 供 _run_one_round 记录 history 使用

        # 提前终止：连续 N 轮无改进则停止
        consecutive_no_improvement = 0

        for iteration in range(1, self.config.max_rounds + 1):
            _print(
                f"\n═══ Round {iteration}/{self.config.max_rounds} ═══ (composite={current_composite:.4f})"
            )
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
                current_composite = compute_composite(
                    current_summary, self.config.weights
                )
                current_correct_ids = extract_correct_ids(current_summary)
                any_improvement = True

                # 更新最佳状态
                if current_composite > best_composite:
                    best_composite = current_composite
                    best_iteration = iteration
                    self._best_composite = best_composite
                    consecutive_no_improvement = 0
                else:
                    consecutive_no_improvement += 1

                _print(
                    f"✓ Round {iteration}: improved → composite={current_composite:.4f} ({len(current_correct_ids)} correct)"
                )
                logger.info(
                    "Round %d: improved → composite=%.4f (%d correct)",
                    iteration,
                    current_composite,
                    len(current_correct_ids),
                )
            else:
                consecutive_no_improvement += 1
                _print(
                    f"✗ Round {iteration}: no improvement ({consecutive_no_improvement}/{CONSECUTIVE_NO_IMPROVEMENT_LIMIT} consecutive)"
                )
                logger.info("Round %d: no improvement", iteration)

            # Check early termination (perfect score)
            if current_composite >= 1.0:
                _print("🎯 Perfect composite score achieved, stopping.")
                logger.info("Perfect composite score achieved, stopping.")
                break

            # 提前终止：连续 N 轮无改进
            if consecutive_no_improvement >= CONSECUTIVE_NO_IMPROVEMENT_LIMIT:
                _print(
                    f"🛑 Stopping: {CONSECUTIVE_NO_IMPROVEMENT_LIMIT} consecutive rounds without improvement"
                )
                logger.info(
                    "Early stop: %d consecutive rounds without improvement",
                    CONSECUTIVE_NO_IMPROVEMENT_LIMIT,
                )
                break

        # Final summary
        delta = current_composite - baseline_composite
        best_delta = best_composite - baseline_composite
        _print("\n═══ Optimization Complete ═══")
        _print(
            f"Composite: {baseline_composite:.4f} → {current_composite:.4f} ({delta:+.4f})"
        )
        if best_iteration > 0:
            _print(
                f"Best composite: {best_composite:.4f} ({best_delta:+.4f}) @ round {best_iteration}"
            )
        logger.info("Optimization complete. Final composite: %.4f", current_composite)

        # Generate report
        _print("\n─── Report Generation ───")
        self._generate_report(baseline_summary, current_summary, any_improvement)

        # Log final summary
        _debug_log(
            {
                "event": "run_complete",
                "composite_start": round(baseline_composite, 4),
                "composite_end": round(current_composite, 4),
                "composite_best": round(best_composite, 4),
                "delta": round(delta, 4),
                "best_iteration": best_iteration,
                "max_rounds": self.config.max_rounds,
                "any_improvement": any_improvement,
            }
        )

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
            logger.info("  #%s: composite=%.4f — %s", iteration, composite, desc)
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
            self.history.record(
                {
                    "iteration": iteration,
                    "composite": compute_composite(old_summary, self.config.weights),
                    "correct_cases": len(old_correct_ids),
                    "total_cases": old_summary.total_cases,
                    "metrics": score_dict(old_summary),
                    "timestamp": _now_iso(),
                    "description": "no diagnoses",
                    "fixes_tried": 0,
                    "fixes_accepted": 0,
                }
            )
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

        # Log all diagnoses for this round
        _debug_log(
            {
                "event": "round_diagnoses",
                "iteration": iteration,
                "total_diagnoses": len(diagnoses),
                "diagnoses": [
                    {
                        "type": d.type,
                        "fix_type": d.suggested_fix_type,
                        "gain": round(d.fix_gain, 4),
                        "affected": len(d.affected_cases),
                        "description": d.description,
                        "expected": {k: str(v) for k, v in d.expected_values.items()},
                        "keywords": d.suggested_keywords[:5],
                    }
                    for d in diagnoses[:10]  # top 10 to avoid bloating
                ],
            }
        )

        accepted_any = False
        fixes_tried = 0
        fixes_accepted = 0

        # 获取当前的 predictions（用于增量评测）
        current_predictions = dict(self.evaluator.predictions or {})

        for diag in candidates:
            # NEW: LLM-review branch for intent_mismatch with keyword candidates
            if diag.type == TYPE_INTENT_MISMATCH:
                candidates_kw = diag.details.get("keyword_candidates", [])
                if candidates_kw:
                    kw_accepted = self._run_keyword_review_loop(
                        diag,
                        candidates_kw,
                        iteration,
                        old_summary,
                        current_predictions,
                    )
                    if kw_accepted:
                        fixes_accepted += 1
                        accepted_any = True
                        current_predictions = dict(
                            self.evaluator.predictions or current_predictions
                        )
                        continue  # skip old verifier for this diag

            fixes_tried += 1
            _print(
                f"Trying fix: [{diag.type}] {diag.suggested_fix_type} (gain={diag.fix_gain:.4f})"
            )
            logger.info(
                "  Trying fix: [%s] %s (gain=%.4f)",
                diag.type,
                diag.suggested_fix_type,
                diag.fix_gain,
            )

            fix_result = self.fixer.apply_fix(diag)

            if not fix_result.success:
                _print(
                    f"✗ Fix failed: {fix_result.fix_type} — {fix_result.error or fix_result.description}"
                )
                logger.warning(
                    "  Fix failed: %s — %s",
                    fix_result.fix_type,
                    fix_result.error or fix_result.description,
                )
                _debug_log(
                    {
                        "event": "fix_failure",
                        "iteration": iteration,
                        "diagnosis_type": diag.type,
                        "fix_type": fix_result.fix_type,
                        "error": fix_result.error or fix_result.description,
                        "gain_estimated": round(diag.fix_gain, 4),
                    }
                )
                continue

            # 增量验证：只重评受影响工单
            affected_ids = set(diag.affected_cases) if diag.affected_cases else None

            # Verify improvement
            improved, new_summary, new_composite = self._verify_fix(
                old_summary,
                old_correct_ids,
                affected_cases=affected_ids,
                old_predictions=current_predictions,
            )

            if improved:
                # 更新 predictions 缓存，后续修复基于最新状态
                current_predictions = dict(
                    self.evaluator.predictions or current_predictions
                )
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

                _debug_log(
                    {
                        "event": "fix_accepted",
                        "iteration": iteration,
                        "diagnosis_type": diag.type,
                        "fix_type": diag.suggested_fix_type,
                        "composite_before": round(
                            compute_composite(old_summary, self.config.weights), 4
                        ),
                        "composite_after": round(new_composite, 4),
                        "delta": round(
                            new_composite
                            - compute_composite(old_summary, self.config.weights),
                            4,
                        ),
                        "gain_estimated": round(diag.fix_gain, 4),
                        "commit_sha": sha[:8],
                    }
                )

                self.history.record(
                    {
                        "iteration": iteration,
                        "composite": new_composite,
                        "best_composite": self._best_composite,  # NEW
                        "correct_cases": len(extract_correct_ids(new_summary)),
                        "total_cases": new_summary.total_cases,
                        "metrics": score_dict(new_summary),
                        "timestamp": _now_iso(),
                        "description": f"accepted: {diag.suggested_fix_type}",
                        "fix_type": diag.suggested_fix_type,
                        "diagnosis_type": diag.type,
                        "commit_sha": sha,
                        "fix_gain_actual": new_composite
                        - compute_composite(old_summary, self.config.weights),
                    }
                )
            else:
                # Rollback
                self.fixer.rollback()
                _print(f"✗ Rolled back: no improvement after {diag.suggested_fix_type}")
                logger.info("  Reverted fix (no improvement)")
                _debug_log(
                    {
                        "event": "fix_rolled_back",
                        "iteration": iteration,
                        "diagnosis_type": diag.type,
                        "fix_type": diag.suggested_fix_type,
                        "gain_estimated": round(diag.fix_gain, 4),
                    }
                )
                self.history.record(
                    {
                        "iteration": iteration,
                        "composite": compute_composite(
                            old_summary, self.config.weights
                        ),
                        "correct_cases": len(old_correct_ids),
                        "total_cases": old_summary.total_cases,
                        "metrics": score_dict(old_summary),
                        "timestamp": _now_iso(),
                        "description": f"reverted: {diag.suggested_fix_type}",
                        "fix_type": diag.suggested_fix_type,
                        "diagnosis_type": diag.type,
                    }
                )

        final_composite = (
            compute_composite(old_summary, self.config.weights)
            if not accepted_any
            else None  # will use last known value
        )
        if final_composite is None:
            # At least one fix was accepted; re-evaluate to get current state
            final_summary = self.evaluator.run_full_evaluation()
            final_composite = compute_composite(final_summary, self.config.weights)

        self.history.save_state(
            {
                "iteration": iteration,
                "composite": final_composite,
            }
        )

        return accepted_any

    # ------------------------------------------------------------------
    # LLM review loop (internal to _run_one_round)
    # ------------------------------------------------------------------

    def _run_keyword_review_loop(
        self,
        diag: Diagnosis,
        candidates_kw: list[str],
        iteration: int,
        old_summary: EvaluationSummary,
        current_predictions: dict,
    ) -> bool:
        """Try LLM-reviewed keyword additions for an intent_mismatch diagnosis.

        Returns True if at least one keyword was approved and applied.
        """
        tickets = self.evaluator.dataset.tickets
        golden = self.evaluator.dataset.golden

        for keyword in candidates_kw:
            _print(
                f"  Simulating keyword '{keyword}' for {diag.expected_values.get('intent', '?')}..."
            )

            tradeoff = analyze_keyword_tradeoff(
                diag,
                keyword,
                tickets,
                golden,
                current_predictions=current_predictions,
            )

            if tradeoff.net_gain <= 0:
                _print(f"    \u2717 Net gain {tradeoff.net_gain} \u2264 0, skipping")
                continue

            # Get sample texts
            sample_fixed = [
                tickets[cid].original_text
                for cid in tradeoff.fixed_case_ids[:3]
                if cid in tickets
            ]
            sample_harmed = [
                tickets[cid].original_text
                for cid in tradeoff.harmed_case_ids[:3]
                if cid in tickets
            ]

            _print(
                f"    \U0001f4cb LLM reviewing '{keyword}': fix {len(tradeoff.fixed_case_ids)}, harm {len(tradeoff.harmed_case_ids)}, net={tradeoff.net_gain}"
            )

            try:
                review = review_keyword(
                    tradeoff, sample_fixed, sample_harmed, self.config
                )
            except ValueError as e:
                _print(f"    \u2717 LLM review failed: {e}")
                continue

            if review.get("decision") == "APPROVE":
                _print(f"    \u2705 LLM APPROVED: {tradeoff.description}")
                result = self.fixer.apply_fix_keyword(
                    intent=tradeoff.target_intent,
                    keyword=keyword,
                )
                if result.success:
                    # Run verification
                    affected_ids = set(diag.affected_cases or [])
                    improved, new_summary, new_composite = self._verify_fix(
                        old_summary,
                        set(),  # use full eval for keyword changes
                        affected_cases=affected_ids,
                        old_predictions=current_predictions,
                    )

                    if improved:
                        msg = (
                            f"optimizer round {iteration}: LLM-approved keyword '{keyword}' "
                            f"for {tradeoff.target_intent} (composite={new_composite:.4f})"
                        )
                        sha = commit(message=msg)
                        current_predictions = dict(
                            self.evaluator.predictions or current_predictions
                        )

                        _print(f"    \u2705 Committed: {msg} \u2192 {sha[:8]}")

                        self.history.record(
                            {
                                "iteration": iteration,
                                "composite": new_composite,
                                "best_composite": self._best_composite,
                                "correct_cases": len(extract_correct_ids(new_summary)),
                                "total_cases": new_summary.total_cases,
                                "metrics": score_dict(new_summary),
                                "timestamp": _now_iso(),
                                "description": f"LLM keyword: {keyword} \u2192 {tradeoff.target_intent}",
                                "fix_type": "intent_keyword_llm",
                                "diagnosis_type": diag.type,
                                "commit_sha": sha,
                                "fix_gain_actual": new_composite
                                - compute_composite(old_summary, self.config.weights),
                            }
                        )
                        return True
                    else:
                        self.fixer.rollback()
                        _print(
                            f"    \u2717 No improvement after applying '{keyword}', rolled back"
                        )
                else:
                    _print(
                        f"    \u2717 apply_fix_keyword failed: {result.error or result.description}"
                    )
            else:
                _print(
                    f"    \u2717 LLM REJECTED: {review.get('reasoning', 'no reason')[:100]}"
                )

        return False

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

        md = reporter.generate(
            iter_records, baseline=baseline_summary, final=final_summary
        )
        path = reporter.save(md)
        _print(f"✅ Report saved to {path}")

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify_fix(
        self,
        old_summary: EvaluationSummary,
        old_correct_ids: set[str],
        affected_cases: set[str] | None = None,
        old_predictions: dict[str, EvalPrediction] | None = None,
    ) -> tuple[bool, EvaluationSummary, float]:
        """Re-evaluate after applying a fix and check for improvement.

        Uses incremental evaluation when affected_cases and old_predictions
        are provided.

        A fix is accepted if:
        1. Composite score improved, AND
        2. No single metric dropped by more than MAX_SINGLE_METRIC_DROP, AND
        3. At least MIN_CASES_FIXED new correct cases (net gain).

        Returns:
            (improved, new_summary, new_composite)
        """
        if affected_cases and old_predictions is not None:
            new_summary = self.evaluator.run_partial_evaluation(
                affected_case_ids=affected_cases,
                previous_predictions=old_predictions,
            )
        else:
            new_summary = self.evaluator.run_full_evaluation()
        new_composite = compute_composite(new_summary, self.config.weights)
        old_composite = compute_composite(old_summary, self.config.weights)

        # Check composite improved
        if new_composite <= old_composite:
            return False, new_summary, new_composite

        # Check no single metric regressed too much
        old_scores = score_dict(old_summary)
        new_scores = score_dict(new_summary)
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
        new_correct_ids = extract_correct_ids(new_summary)
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
# Module-level helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    """Return current UTC time as ISO string."""
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat()
