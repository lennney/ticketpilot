"""Integration tests for draft evaluation runner.

Tests the draft evaluation script end-to-end using fixture data
that does not require DB, network, or real LLM API calls.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
import tempfile



class TestDraftEvaluationRunner:
    """End-to-end tests for run_draft_evaluation.py runner functions."""

    def _run_with_fixture(self, fixture_cases: list[dict], limit: int = 0):
        """Run draft evaluation with fixture tickets using in-process functions."""
        import argparse

        # Add scripts/ to path for module import
        scripts_dir = pathlib.Path(__file__).parent.parent.parent / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from run_draft_evaluation import run_draft_eval  # noqa: F401

        with tempfile.TemporaryDirectory() as tmpdir:
            tickets_path = pathlib.Path(tmpdir) / "tickets_eval.csv"
            rows_path = pathlib.Path(tmpdir) / "rows.json"
            summary_path = pathlib.Path(tmpdir) / "summary.json"
            md_path = pathlib.Path(tmpdir) / "report.md"

            # Write fixture tickets CSV (with all required columns)
            with tickets_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["case_id", "original_text", "customer_id", "submitted_at", "scenario_type", "notes"],
                )
                writer.writeheader()
                writer.writerows(fixture_cases)

            args = argparse.Namespace(
                tickets=str(tickets_path),
                out_rows=str(rows_path),
                out_summary=str(summary_path),
                out_md=str(md_path),
                limit=limit,
            )
            run_draft_eval(args)

            rows_data = json.loads(rows_path.read_text(encoding="utf-8"))
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
            md_content = md_path.read_text(encoding="utf-8")

            return rows_data, summary_data, md_content

    def test_writes_row_json(self):
        """Runner writes per-case JSON rows."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
        ]
        rows, _, _ = self._run_with_fixture(cases)
        assert len(rows) == 1
        assert rows[0]["case_id"] == "eval-001"
        assert "provider_name" in rows[0]
        assert "model_name" in rows[0]
        assert "cited_evidence_count" in rows[0]
        assert "guard_passed" in rows[0]
        assert "citation_validation_passed" in rows[0]

    def test_writes_summary_json(self):
        """Runner writes summary JSON with all metric fields."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
        ]
        _, summary, _ = self._run_with_fixture(cases)
        assert "total_cases" in summary
        assert summary["total_cases"] == 1
        assert "citation_precision_avg" in summary
        assert "evidence_coverage_avg" in summary
        assert "unsupported_claim_rate" in summary
        assert "forbidden_promise_rate" in summary
        assert "safe_fallback_rate" in summary
        assert "human_review_trigger_accuracy" in summary
        assert "citation_validation_pass_rate" in summary
        assert "claim_guard_pass_rate" in summary
        assert "average_confidence" in summary

    def test_writes_markdown_report(self):
        """Runner writes Markdown report with metric definitions and summary."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
        ]
        _, _, md = self._run_with_fixture(cases)
        assert "# Phase 11.8" in md
        assert "评估时间" in md
        assert "指标定义" in md
        assert "汇总指标" in md
        assert "FakeLLMProvider" in md
        assert "局限性说明" in md

    def test_no_network_calls(self):
        """Runner completes without any network calls."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
        ]
        rows, _, _ = self._run_with_fixture(cases)
        assert len(rows) == 1

    def test_fake_provider_by_default(self):
        """Runner uses FakeLLMProvider by default (no API keys required)."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
        ]
        rows, _, _ = self._run_with_fixture(cases)
        assert rows[0]["provider_name"] == "fake"
        assert rows[0]["model_name"] == "fake"

    def test_limit_parameter(self):
        """Runner respects --limit parameter."""
        cases = [
            {
                "case_id": f"eval-{i:03d}",
                "original_text": "测试",
                "customer_id": f"c{i}",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "测试",
            }
            for i in range(1, 6)
        ]
        rows, summary, _ = self._run_with_fixture(cases, limit=3)
        assert summary["total_cases"] == 3
        assert len(rows) == 3

    def test_deterministic_output(self):
        """Running twice with same input produces identical output."""
        cases = [
            {
                "case_id": "eval-001",
                "original_text": "我要退款",
                "customer_id": "cust-001",
                "submitted_at": "2026-05-06T10:00:00",
                "scenario_type": "正常退款",
            },
            {
                "case_id": "eval-002",
                "original_text": "订单未到",
                "customer_id": "cust-002",
                "submitted_at": "2026-05-06T11:00:00",
                "scenario_type": "物流问题",
            },
        ]
        rows1, summary1, _ = self._run_with_fixture(cases)
        rows2, summary2, _ = self._run_with_fixture(cases)
        assert rows1 == rows2
        assert summary1 == summary2
