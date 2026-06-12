"""Verification engine for the auto-optimizer.

Runs a 3-layer verification after each optimization round:
  Layer 1: pytest unit tests pass
  Layer 2: re-evaluate and compute composite delta
  Layer 3: safety checks (no metric drop >2%, no regressions, at least 1 improvement)
"""
from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ticketpilot.evaluation.schemas import EvaluationSummary
from ticketpilot.optimizer.config import COMPOSITE_WEIGHTS, MAX_SINGLE_METRIC_DROP, MIN_CASES_FIXED

if TYPE_CHECKING:
    from ticketpilot.optimizer.evaluator import OptimizerEvaluator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Outcome of a verification round."""

    passed: bool
    layer1_passed: bool  # pytest passed
    layer2_passed: bool  # composite score improved
    layer3_passed: bool  # safety checks
    composite_delta: float = 0.0
    metric_deltas: dict[str, float] = field(default_factory=dict)
    regressed_cases: list[str] = field(default_factory=list)
    improved_cases: list[str] = field(default_factory=list)
    message: str = ""
    pytest_output: str = ""
    pytest_returncode: int = -1


# ---------------------------------------------------------------------------
# Composite score helper
# ---------------------------------------------------------------------------

def compute_composite_score(
    summary: EvaluationSummary,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute a weighted composite score from an EvaluationSummary.

    Args:
        summary: The evaluation summary.
        weights: Override weights (defaults to COMPOSITE_WEIGHTS from config).

    Returns:
        Composite score in [0.0, 1.0].
    """
    w = weights or COMPOSITE_WEIGHTS
    score = (
        w.get("intent", 0) * summary.aggregate_intent_accuracy
        + w.get("severity", 0) * summary.aggregate_severity_accuracy
        + w.get("risk_f1", 0) * summary.aggregate_risk_flag_f1
        + w.get("evidence", 0) * summary.aggregate_evidence_doc_type_recall
        + w.get("no_auto_send", 0) * summary.aggregate_no_auto_send_compliance
        + w.get("fallback", 0) * summary.aggregate_fallback_correctness
    )
    return round(score, 6)


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class Verifier:
    """Runs 3-layer verification after an optimization round.

    Usage::

        verifier = Verifier()
        result = verifier.verify(old_summary, old_correct_ids, evaluator=evaluator)
        if not result.passed:
            fixer.rollback()
    """

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent.parent
        self.weights = weights or dict(COMPOSITE_WEIGHTS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self,
        old_summary: EvaluationSummary,
        old_correct_ids: set[str],
        *,
        evaluator: OptimizerEvaluator | None = None,
        new_summary: EvaluationSummary | None = None,
    ) -> VerificationResult:
        """Run all three verification layers and return a combined result.

        Args:
            old_summary: Evaluation summary before the optimization.
            old_correct_ids: Set of case_ids that were correct before.
            evaluator: An OptimizerEvaluator to re-run evaluation (Layer 2).
                       If None, Layer 2/3 are skipped.
            new_summary: Pre-computed new summary (if provided, skips evaluator).

        Returns:
            VerificationResult with per-layer pass/fail and details.
        """
        # Layer 1: pytest
        layer1, pytest_out, pytest_rc = self._layer1_pytest()

        # Layer 2: re-evaluate and compute composite delta
        layer2, new_sum, composite_delta, metric_deltas = self._layer2_evaluate(
            old_summary,
            evaluator=evaluator,
            new_summary=new_summary,
        )

        # Layer 3: safety checks
        layer3, regressed, improved = self._layer3_safety(
            old_summary,
            new_sum,
            old_correct_ids,
        )

        passed = layer1 and layer2 and layer3

        messages: list[str] = []
        if not layer1:
            messages.append(f"Layer 1 FAILED: pytest exited with code {pytest_rc}")
        if not layer2:
            messages.append(
                f"Layer 2 FAILED: composite delta {composite_delta:+.4f} (must be positive)"
            )
        if not layer3:
            if regressed:
                messages.append(
                    f"Layer 3 FAILED: {len(regressed)} case(s) regressed"
                )
            else:
                messages.append("Layer 3 FAILED: no cases improved or safety check failed")

        if passed:
            messages.append(
                f"Verification PASSED: composite {composite_delta:+.4f}, "
                f"{len(improved)} improved, 0 regressed"
            )

        return VerificationResult(
            passed=passed,
            layer1_passed=layer1,
            layer2_passed=layer2,
            layer3_passed=layer3,
            composite_delta=composite_delta,
            metric_deltas=metric_deltas,
            regressed_cases=regressed,
            improved_cases=improved,
            message="; ".join(messages),
            pytest_output=pytest_out,
            pytest_returncode=pytest_rc,
        )

    # ------------------------------------------------------------------
    # Layer 1: pytest
    # ------------------------------------------------------------------

    def _layer1_pytest(self) -> tuple[bool, str, int]:
        """Run ``pytest tests/unit/ -x -q --tb=no`` and return success."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/",
            "-x", "-q", "--tb=no",
        ]
        logger.info("Layer 1: running %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + "\n" + result.stderr
            success = result.returncode == 0
            logger.info("Layer 1: pytest exited %d (%s)", result.returncode, "PASS" if success else "FAIL")
            return success, output, result.returncode
        except subprocess.TimeoutExpired:
            msg = "Layer 1: pytest timed out after 300s"
            logger.error(msg)
            return False, msg, -1
        except Exception as exc:
            msg = f"Layer 1: pytest failed to run: {exc}"
            logger.error(msg)
            return False, msg, -1

    # ------------------------------------------------------------------
    # Layer 2: re-evaluate
    # ------------------------------------------------------------------

    def _layer2_evaluate(
        self,
        old_summary: EvaluationSummary,
        *,
        evaluator: OptimizerEvaluator | None = None,
        new_summary: EvaluationSummary | None = None,
    ) -> tuple[bool, EvaluationSummary | None, float, dict[str, float]]:
        """Re-run evaluation and compute composite delta.

        Returns:
            (layer2_passed, new_summary, composite_delta, metric_deltas)
        """
        # Get the new summary
        if new_summary is None:
            if evaluator is None:
                # No evaluator available — skip layer 2, treat as pass
                logger.warning("Layer 2: no evaluator or new_summary provided, skipping")
                return True, old_summary, 0.0, {}
            try:
                new_summary = evaluator.run_full_evaluation()
            except Exception as exc:
                logger.error("Layer 2: evaluation failed: %s", exc)
                return False, None, 0.0, {}

        old_composite = compute_composite_score(old_summary, self.weights)
        new_composite = compute_composite_score(new_summary, self.weights)
        delta = round(new_composite - old_composite, 6)

        # Per-metric deltas
        metric_deltas = {
            "intent": new_summary.aggregate_intent_accuracy - old_summary.aggregate_intent_accuracy,
            "severity": new_summary.aggregate_severity_accuracy - old_summary.aggregate_severity_accuracy,
            "risk_f1": new_summary.aggregate_risk_flag_f1 - old_summary.aggregate_risk_flag_f1,
            "evidence": new_summary.aggregate_evidence_doc_type_recall - old_summary.aggregate_evidence_doc_type_recall,
            "no_auto_send": new_summary.aggregate_no_auto_send_compliance - old_summary.aggregate_no_auto_send_compliance,
            "fallback": new_summary.aggregate_fallback_correctness - old_summary.aggregate_fallback_correctness,
            "composite": delta,
        }

        passed = delta > 0
        logger.info(
            "Layer 2: composite %.4f → %.4f (delta %+.4f) [%s]",
            old_composite, new_composite, delta, "PASS" if passed else "FAIL",
        )
        return passed, new_summary, delta, metric_deltas

    # ------------------------------------------------------------------
    # Layer 3: safety checks
    # ------------------------------------------------------------------

    def _layer3_safety(
        self,
        old_summary: EvaluationSummary,
        new_summary: EvaluationSummary | None,
        old_correct_ids: set[str],
    ) -> tuple[bool, list[str], list[str]]:
        """Check no metric dropped >2%, no regressions, at least 1 improvement.

        Returns:
            (layer3_passed, regressed_case_ids, improved_case_ids)
        """
        if new_summary is None:
            return False, [], []

        regressed: list[str] = []
        improved: list[str] = []

        for case_id, old_result in old_summary.results.items():
            new_result = new_summary.results.get(case_id)
            if new_result is None:
                continue

            was_correct = case_id in old_correct_ids
            # A case is "correct" if it has no mismatches
            is_correct = len(new_result.mismatches) == 0

            if was_correct and not is_correct:
                regressed.append(case_id)
            elif not was_correct and is_correct:
                improved.append(case_id)

        # Check individual metrics haven't dropped more than threshold
        metric_ok = True
        old_metrics = {
            "intent": old_summary.aggregate_intent_accuracy,
            "severity": old_summary.aggregate_severity_accuracy,
            "risk_f1": old_summary.aggregate_risk_flag_f1,
            "evidence": old_summary.aggregate_evidence_doc_type_recall,
            "no_auto_send": old_summary.aggregate_no_auto_send_compliance,
            "fallback": old_summary.aggregate_fallback_correctness,
        }
        new_metrics = {
            "intent": new_summary.aggregate_intent_accuracy,
            "severity": new_summary.aggregate_severity_accuracy,
            "risk_f1": new_summary.aggregate_risk_flag_f1,
            "evidence": new_summary.aggregate_evidence_doc_type_recall,
            "no_auto_send": new_summary.aggregate_no_auto_send_compliance,
            "fallback": new_summary.aggregate_fallback_correctness,
        }

        for name in old_metrics:
            old_val = old_metrics[name]
            new_val = new_metrics[name]
            if old_val - new_val > MAX_SINGLE_METRIC_DROP:
                logger.warning(
                    "Layer 3: metric '%s' dropped %.4f > %.4f threshold",
                    name, old_val - new_val, MAX_SINGLE_METRIC_DROP,
                )
                metric_ok = False

        no_regressions = len(regressed) == 0
        has_improvement = len(improved) >= MIN_CASES_FIXED

        passed = metric_ok and no_regressions and has_improvement

        logger.info(
            "Layer 3: %d regressed, %d improved, metrics %s [%s]",
            len(regressed), len(improved),
            "OK" if metric_ok else "VIOLATION",
            "PASS" if passed else "FAIL",
        )
        return passed, regressed, improved
