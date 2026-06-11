"""Tests for ticketpilot.optimizer.reporter."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ticketpilot.evaluation.schemas import EvaluationSummary
from ticketpilot.optimizer.config import OptimizerConfig
from ticketpilot.optimizer.reporter import IterationRecord, OptimizationReporter
from ticketpilot.optimizer.verifier import VerificationResult, compute_composite_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(
    *,
    total_cases: int = 3,
    intent: float = 0.8,
    severity: float = 0.7,
    risk_f1: float = 0.6,
    evidence: float = 0.9,
    no_auto_send: float = 1.0,
    fallback: float = 0.5,
) -> EvaluationSummary:
    return EvaluationSummary(
        total_cases=total_cases,
        aggregate_intent_accuracy=intent,
        aggregate_severity_accuracy=severity,
        aggregate_risk_flag_f1=risk_f1,
        aggregate_evidence_doc_type_recall=evidence,
        aggregate_no_auto_send_compliance=no_auto_send,
        aggregate_fallback_correctness=fallback,
    )


def _make_verification(
    *,
    passed: bool = True,
    composite_delta: float = 0.01,
    improved: list[str] | None = None,
    regressed: list[str] | None = None,
    metric_deltas: dict[str, float] | None = None,
) -> VerificationResult:
    return VerificationResult(
        passed=passed,
        layer1_passed=passed,
        layer2_passed=passed,
        layer3_passed=passed,
        composite_delta=composite_delta,
        improved_cases=improved or [],
        regressed_cases=regressed or [],
        metric_deltas=metric_deltas or {
            "intent": 0.02,
            "severity": 0.01,
            "risk_f1": 0.03,
            "evidence": -0.01,
            "no_auto_send": 0.0,
            "fallback": 0.01,
        },
    )


# ---------------------------------------------------------------------------
# IterationRecord basics
# ---------------------------------------------------------------------------

class TestIterationRecord:
    def test_defaults(self) -> None:
        r = IterationRecord(round_num=1)
        assert r.round_num == 1
        assert r.summary_before is None
        assert r.summary_after is None
        assert r.verification is None
        assert r.fix_description == ""
        assert r.committed is False
        assert r.timestamp  # auto-generated

    def test_custom_values(self) -> None:
        r = IterationRecord(
            round_num=5,
            fix_description="Added keywords",
            committed=True,
            timestamp="2025-01-01T00:00:00Z",
        )
        assert r.round_num == 5
        assert r.committed is True
        assert r.timestamp == "2025-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# OptimizationReporter.generate
# ---------------------------------------------------------------------------

class TestReporterGenerate:
    def test_empty_iterations(self) -> None:
        reporter = OptimizationReporter()
        md = reporter.generate([], baseline=None, final=None)
        assert "# Auto-Optimization Report" in md
        assert "_No iterations recorded._" in md
        assert "_No evaluation data available._" in md

    def test_with_baseline_and_final(self) -> None:
        baseline = _make_summary(intent=0.7, severity=0.7)
        final = _make_summary(intent=0.85, severity=0.8)
        reporter = OptimizationReporter()
        md = reporter.generate([], baseline=baseline, final=final)
        assert "Score Summary" in md
        assert "70.00%" in md  # baseline intent
        assert "85.00%" in md  # final intent

    def test_baseline_only(self) -> None:
        baseline = _make_summary(intent=0.7)
        reporter = OptimizationReporter()
        md = reporter.generate([], baseline=baseline)
        assert "70.00%" in md

    def test_final_only(self) -> None:
        final = _make_summary(intent=0.85)
        reporter = OptimizationReporter()
        md = reporter.generate([], final=final)
        assert "85.00%" in md

    def test_iterations_table_committed(self) -> None:
        v = _make_verification(composite_delta=0.05, improved=["T001"])
        it = IterationRecord(
            round_num=1,
            fix_description="Added refund keywords",
            committed=True,
            verification=v,
        )
        reporter = OptimizationReporter()
        md = reporter.generate([it])
        assert "Iteration Details" in md
        assert "✅ Committed" in md
        assert "+0.0500" in md

    def test_iterations_table_rolled_back(self) -> None:
        v = _make_verification(passed=False, composite_delta=-0.02)
        it = IterationRecord(
            round_num=1,
            fix_description="Bad fix",
            committed=False,
            verification=v,
        )
        reporter = OptimizationReporter()
        md = reporter.generate([it])
        assert "❌ Rolled Back" in md

    def test_committed_details_section(self) -> None:
        v = _make_verification(
            composite_delta=0.03,
            improved=["T001"],
            metric_deltas={"intent": 0.02, "severity": -0.01, "composite": 0.03},
        )
        it = IterationRecord(
            round_num=1,
            fix_description="Improved intent classification",
            committed=True,
            verification=v,
        )
        reporter = OptimizationReporter()
        md = reporter.generate([it])
        assert "Committed Iteration Details" in md
        assert "Round 1" in md
        assert "intent: +0.0200" in md
        assert "severity: -0.0100" in md

    def test_footer_counts(self) -> None:
        v = _make_verification()
        it1 = IterationRecord(round_num=1, committed=True, verification=v)
        it2 = IterationRecord(round_num=2, committed=False, verification=v)
        reporter = OptimizationReporter()
        md = reporter.generate([it1, it2])
        assert "2 iteration(s)" in md
        assert "1 committed" in md

    def test_long_fix_description_truncated(self) -> None:
        long_desc = "A" * 100
        v = _make_verification()
        it = IterationRecord(round_num=1, fix_description=long_desc, verification=v)
        reporter = OptimizationReporter()
        md = reporter.generate([it])
        assert "…" in md
        assert long_desc not in md  # truncated

    def test_composite_score_in_summary_table(self) -> None:
        baseline = _make_summary(intent=0.8, severity=0.8, risk_f1=0.8, evidence=0.8, no_auto_send=0.8, fallback=0.8)
        final = _make_summary(intent=0.9, severity=0.9, risk_f1=0.9, evidence=0.9, no_auto_send=0.9, fallback=0.9)
        reporter = OptimizationReporter()
        md = reporter.generate([], baseline=baseline, final=final)
        assert "Composite Score" in md
        old_c = compute_composite_score(baseline)
        new_c = compute_composite_score(final)
        assert f"{old_c:.4f}" in md
        assert f"{new_c:.4f}" in md


# ---------------------------------------------------------------------------
# OptimizationReporter.save
# ---------------------------------------------------------------------------

class TestReporterSave:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        report_path = tmp_path / "reports" / "optimization" / "report.md"
        config = OptimizerConfig(report_md=report_path)
        reporter = OptimizationReporter(config)
        md = reporter.generate([], baseline=_make_summary())
        saved = reporter.save(md)
        assert saved == report_path
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Auto-Optimization Report" in content

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "report.md"
        config = OptimizerConfig(report_md=deep_path)
        reporter = OptimizationReporter(config)
        md = reporter.generate([], baseline=_make_summary())
        reporter.save(md)
        assert deep_path.exists()

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        report_path = tmp_path / "report.md"
        report_path.write_text("old content", encoding="utf-8")
        config = OptimizerConfig(report_md=report_path)
        reporter = OptimizationReporter(config)
        md = reporter.generate([], baseline=_make_summary())
        reporter.save(md)
        content = report_path.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "# Auto-Optimization Report" in content


# ---------------------------------------------------------------------------
# _pct helper
# ---------------------------------------------------------------------------

class TestPctHelper:
    def test_both_values(self) -> None:
        reporter = OptimizationReporter()
        b = _make_summary(intent=0.75)
        f = _make_summary(intent=0.85)
        result = reporter._pct(b, f, "aggregate_intent_accuracy")
        assert "75.00%" in result
        assert "85.00%" in result
        assert "+10.00%" in result

    def test_baseline_only(self) -> None:
        reporter = OptimizationReporter()
        b = _make_summary(intent=0.6)
        result = reporter._pct(b, None, "aggregate_intent_accuracy")
        assert "60.00%" in result
        assert "→" not in result

    def test_final_only(self) -> None:
        reporter = OptimizationReporter()
        f = _make_summary(intent=0.9)
        result = reporter._pct(None, f, "aggregate_intent_accuracy")
        assert "90.00%" in result

    def test_neither(self) -> None:
        reporter = OptimizationReporter()
        result = reporter._pct(None, None, "aggregate_intent_accuracy")
        assert result == "—"
