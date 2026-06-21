"""Tests for the JSON and Markdown report writers (reporting.py)."""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from ticketpilot.evaluation.reporting import write_json_report, write_markdown_report
from ticketpilot.evaluation.metrics import compute_evaluation_summary
from ticketpilot.evaluation.schemas import EvalPrediction, GoldenExpectation


@pytest.fixture
def sample_summary():
    """Build a mini EvaluationSummary with 2 cases (1 mismatch)."""
    predictions = {
        "case_001": EvalPrediction(
            case_id="case_001",
            predicted_issue_type="refund",
            predicted_severity="LOW",
            predicted_must_human_review=False,
            predicted_fallback_required=False,
            predicted_no_auto_send=False,
        ),
        "case_002": EvalPrediction(
            case_id="case_002",
            predicted_issue_type="complaint",
            predicted_severity="MEDIUM",
            predicted_must_human_review=False,
            predicted_fallback_required=False,
            predicted_no_auto_send=True,
        ),
    }
    golden = {
        "case_001": GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        ),
        "case_002": GoldenExpectation(
            case_id="case_002",
            expected_issue_type="complaint",
            expected_severity="HIGH",
            expected_must_human_review=True,
            expected_fallback_required=False,
            expected_no_auto_send=True,
        ),
    }
    return compute_evaluation_summary(predictions, golden)


def test_json_report_writer_creates_valid_json(sample_summary):
    """JSON report writer creates valid JSON with expected keys."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        outpath = f.name
    try:
        result = write_json_report(
            sample_summary,
            outpath,
            tickets_path="t.csv",
            golden_path="g.csv",
            predictions_path="p.csv",
        )
        data = json.loads(result)
        assert "generated_at" in data
        assert "total_cases" in data
        assert data["total_cases"] == 2
        assert "aggregate_metrics" in data
        assert "risk_flag_metrics" in data
        assert "per_case_results" in data
        assert "mismatches" in data
        assert "metadata" in data
        assert len(data["per_case_results"]) == 2
        # File should also contain the same content
        file_data = json.loads(pathlib.Path(outpath).read_text(encoding="utf-8"))
        assert file_data["total_cases"] == 2
    finally:
        pathlib.Path(outpath).unlink(missing_ok=True)


def test_markdown_report_contains_expected_sections(sample_summary):
    """Markdown report contains aggregate metrics and limitations."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        outpath = f.name
    try:
        result = write_markdown_report(
            sample_summary,
            outpath,
            tickets_path="t.csv",
            golden_path="g.csv",
            predictions_path="p.csv",
        )
        assert "# Evaluation Report" in result
        assert "## Dataset Summary" in result
        assert "## Aggregate Metrics" in result
        assert "## Risk Flag Metrics" in result
        assert "## Mismatch Summary" in result
        assert "## Limitations" in result
        assert "Small deterministic seed dataset" in result
        assert "No real embedding provider" in result
        assert "Not real-world performance" in result
        assert "case_002" in result
        # File should also contain the same content
        file_content = pathlib.Path(outpath).read_text(encoding="utf-8")
        assert "# Evaluation Report" in file_content
    finally:
        pathlib.Path(outpath).unlink(missing_ok=True)


def test_json_report_keys_structure(sample_summary):
    """JSON report has all expected top-level keys."""
    tmp = tempfile.mktemp(suffix=".json")
    try:
        data = json.loads(write_json_report(sample_summary, tmp))
        assert set(data.keys()) == {
            "generated_at",
            "metadata",
            "total_cases",
            "aggregate_metrics",
            "risk_flag_metrics",
            "per_case_results",
            "mismatches",
        }
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def test_markdown_report_with_no_mismatches():
    """Markdown report shows no mismatches when all correct."""
    pred = {
        "case_001": EvalPrediction(
            case_id="case_001",
            predicted_issue_type="refund",
            predicted_severity="LOW",
            predicted_must_human_review=False,
            predicted_fallback_required=False,
            predicted_no_auto_send=False,
        )
    }
    gold = {
        "case_001": GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        )
    }
    tmp = tempfile.mktemp(suffix=".md")
    try:
        summary = compute_evaluation_summary(pred, gold)
        result = write_markdown_report(summary, tmp)
        assert "No mismatches found" in result
        assert "## Limitations" in result
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def test_markdown_report_has_limitations_section(sample_summary):
    """Markdown report limitations section is present."""
    tmp = tempfile.mktemp(suffix=".md")
    try:
        result = write_markdown_report(sample_summary, tmp)
        assert "## Limitations" in result
        assert "small set of curated deterministic seed data" in result
        assert "fake embeddings" in result
        assert "synthetic/golden data only" in result
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def test_json_report_structure_stable(sample_summary):
    """JSON structure is stable across runs (ignore generated_at)."""
    tmp1 = tempfile.mktemp(suffix=".json")
    tmp2 = tempfile.mktemp(suffix=".json")
    try:
        r1 = json.loads(write_json_report(sample_summary, tmp1))
        r2 = json.loads(write_json_report(sample_summary, tmp2))
        del r1["generated_at"]
        del r2["generated_at"]
        assert r1 == r2
    finally:
        pathlib.Path(tmp1).unlink(missing_ok=True)
        pathlib.Path(tmp2).unlink(missing_ok=True)
