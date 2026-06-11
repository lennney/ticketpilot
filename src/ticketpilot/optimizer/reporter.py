"""Optimization report generator.

Builds a Markdown report from optimization iterations and saves it
to the path configured in OptimizerConfig.report_md.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ticketpilot.evaluation.schemas import EvaluationSummary
from ticketpilot.optimizer.config import OptimizerConfig
from ticketpilot.optimizer.verifier import VerificationResult, compute_composite_score

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Iteration record (lightweight, decoupled from optimizer internals)
# ---------------------------------------------------------------------------

class IterationRecord:
    """A single optimization iteration record for the reporter.

    Attributes:
        round_num: 1-based round number.
        summary_before: EvaluationSummary before the fix.
        summary_after: EvaluationSummary after the fix.
        verification: VerificationResult from verification.
        fix_description: Human-readable description of the fix applied.
        committed: Whether this iteration was committed (kept).
        timestamp: ISO timestamp of the iteration.
    """

    def __init__(
        self,
        *,
        round_num: int,
        summary_before: EvaluationSummary | None = None,
        summary_after: EvaluationSummary | None = None,
        verification: VerificationResult | None = None,
        fix_description: str = "",
        committed: bool = False,
        timestamp: str | None = None,
    ) -> None:
        self.round_num = round_num
        self.summary_before = summary_before
        self.summary_after = summary_after
        self.verification = verification
        self.fix_description = fix_description
        self.committed = committed
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# OptimizationReporter
# ---------------------------------------------------------------------------

class OptimizationReporter:
    """Generates Markdown optimization reports.

    Usage::

        reporter = OptimizationReporter(config)
        md = reporter.generate(iterations, baseline, final)
        reporter.save(md)
    """

    def __init__(self, config: OptimizerConfig | None = None) -> None:
        self.config = config or OptimizerConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        iterations: list[IterationRecord],
        baseline: EvaluationSummary | None = None,
        final: EvaluationSummary | None = None,
    ) -> str:
        """Build a Markdown report from the optimization history.

        Args:
            iterations: List of IterationRecord objects (may be empty).
            baseline: EvaluationSummary before any optimization.
            final: EvaluationSummary after the last committed optimization.

        Returns:
            Markdown string.
        """
        sections: list[str] = []

        # Header
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sections.append(f"# Auto-Optimization Report\n")
        sections.append(f"Generated: {now}\n")

        # Score summary
        sections.append(self._score_summary_table(baseline, final))

        # Iteration detail
        sections.append(self._iteration_table(iterations))

        # Footer
        sections.append("---\n")
        sections.append(
            f"*{len(iterations)} iteration(s), "
            f"{sum(1 for i in iterations if i.committed)} committed.*\n"
        )

        return "\n".join(sections)

    def save(self, md: str) -> Path:
        """Write the report to config.report_md and return the path.

        Creates parent directories if needed.
        """
        path = self.config.report_md
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        logger.info("Report saved to %s", path)
        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_summary_table(
        self,
        baseline: EvaluationSummary | None,
        final: EvaluationSummary | None,
    ) -> str:
        """Build the score summary table comparing baseline → final."""
        lines: list[str] = []
        lines.append("## Score Summary\n")

        if baseline is None and final is None:
            lines.append("_No evaluation data available._\n")
            return "\n".join(lines)

        # Use final or baseline to define rows
        ref = final or baseline
        assert ref is not None

        rows = [
            ("Total Cases", str(ref.total_cases)),
            ("Intent Accuracy", self._pct(baseline, final, "aggregate_intent_accuracy")),
            ("Severity Accuracy", self._pct(baseline, final, "aggregate_severity_accuracy")),
            ("Risk Flag F1", self._pct(baseline, final, "aggregate_risk_flag_f1")),
            ("Evidence Recall", self._pct(baseline, final, "aggregate_evidence_doc_type_recall")),
            ("No-Auto-Send", self._pct(baseline, final, "aggregate_no_auto_send_compliance")),
            ("Fallback Correct", self._pct(baseline, final, "aggregate_fallback_correctness")),
        ]

        # Add composite score if possible
        if baseline and final:
            old_c = compute_composite_score(baseline)
            new_c = compute_composite_score(final)
            delta = new_c - old_c
            rows.append(
                ("Composite Score", f"{old_c:.4f} → {new_c:.4f} ({delta:+.4f})")
            )
        elif baseline:
            old_c = compute_composite_score(baseline)
            rows.append(("Composite Score", f"{old_c:.4f}"))
        elif final:
            new_c = compute_composite_score(final)
            rows.append(("Composite Score", f"{new_c:.4f}"))

        lines.append("| Metric | Baseline → Final |")
        lines.append("|--------|-----------------|")
        for label, value in rows:
            lines.append(f"| {label} | {value} |")
        lines.append("")

        return "\n".join(lines)

    def _iteration_table(self, iterations: list[IterationRecord]) -> str:
        """Build the iteration detail table."""
        lines: list[str] = []
        lines.append("## Iteration Details\n")

        if not iterations:
            lines.append("_No iterations recorded._\n")
            return "\n".join(lines)

        lines.append("| Round | Fix | Composite Δ | Status |")
        lines.append("|------:|-----|------------:|--------|")

        for it in iterations:
            delta_str = "—"
            if it.verification:
                delta_str = f"{it.verification.composite_delta:+.4f}"

            status = "✅ Committed" if it.committed else "❌ Rolled Back"

            # Truncate fix description for table readability
            desc = it.fix_description[:60] + ("…" if len(it.fix_description) > 60 else "")

            lines.append(f"| {it.round_num} | {desc} | {delta_str} | {status} |")

        lines.append("")

        # Per-iteration details (only for committed)
        committed = [it for it in iterations if it.committed and it.verification]
        if committed:
            lines.append("### Committed Iteration Details\n")
            for it in committed:
                v = it.verification
                assert v is not None
                lines.append(f"**Round {it.round_num}** — {it.fix_description}\n")
                lines.append(f"- Composite delta: {v.composite_delta:+.4f}")
                lines.append(f"- Improved cases: {len(v.improved_cases)}")
                lines.append(f"- Regressed cases: {len(v.regressed_cases)}")
                if v.metric_deltas:
                    for mk, mv in v.metric_deltas.items():
                        if mk != "composite":
                            lines.append(f"- {mk}: {mv:+.4f}")
                lines.append("")

        return "\n".join(lines)

    def _pct(
        self,
        baseline: EvaluationSummary | None,
        final: EvaluationSummary | None,
        field_name: str,
    ) -> str:
        """Format a metric as 'baseline → final (delta)' percentage."""
        b_val = getattr(baseline, field_name, None) if baseline else None
        f_val = getattr(final, field_name, None) if final else None

        if b_val is not None and f_val is not None:
            delta = f_val - b_val
            return f"{b_val:.2%} → {f_val:.2%} ({delta:+.2%})"
        if b_val is not None:
            return f"{b_val:.2%}"
        if f_val is not None:
            return f"{f_val:.2%}"
        return "—"
