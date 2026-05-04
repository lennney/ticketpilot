"""Tests for the run_eval.py CLI runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
from unittest.mock import patch

import pytest


HAPPY_TICKETS = "data/eval/tickets_eval.csv"
HAPPY_GOLDEN = "data/eval/golden_expectations.csv"
HAPPY_PREDS = "data/eval/sample_predictions.csv"

def _count_tickets():
    import csv
    with open(HAPPY_TICKETS, encoding="utf-8") as f:
        return len(list(csv.DictReader(f)))

EXPECTED_TICKET_COUNT = _count_tickets()


@pytest.fixture
def tmp_json():
    tmp = tempfile.mktemp(suffix=".json")
    yield tmp
    pathlib.Path(tmp).unlink(missing_ok=True)


@pytest.fixture
def tmp_md():
    tmp = tempfile.mktemp(suffix=".md")
    yield tmp
    pathlib.Path(tmp).unlink(missing_ok=True)


def test_cli_happy_path(tmp_json, tmp_md):
    """CLI happy path writes both JSON and Markdown reports."""
    import scripts.run_eval as cli
    args = cli.parse_args([
        "--tickets", HAPPY_TICKETS,
        "--golden", HAPPY_GOLDEN,
        "--predictions", HAPPY_PREDS,
        "--out-json", tmp_json,
        "--out-md", tmp_md,
    ])
    cli.run_eval(args)
    assert pathlib.Path(tmp_json).exists()
    assert pathlib.Path(tmp_md).exists()
    data = json.loads(pathlib.Path(tmp_json).read_text(encoding="utf-8"))
    assert data["total_cases"] == EXPECTED_TICKET_COUNT
    assert len(data["per_case_results"]) == EXPECTED_TICKET_COUNT
    md = pathlib.Path(tmp_md).read_text(encoding="utf-8")
    assert "# Evaluation Report" in md
    assert "## Limitations" in md


def test_cli_invalid_input_exits_nonzero(tmp_json, tmp_md):
    """CLI invalid input exits non-zero."""
    import scripts.run_eval as cli
    with pytest.raises(SystemExit) as exc_info:
        args = cli.parse_args([
            "--tickets", "nonexistent.csv",
            "--golden", HAPPY_GOLDEN,
            "--predictions", HAPPY_PREDS,
            "--out-json", tmp_json,
            "--out-md", tmp_md,
        ])
        cli.run_eval(args)
    assert exc_info.value.code != 0


def test_cli_does_not_call_real_pipeline(tmp_json, tmp_md):
    """CLI does not call real pipeline."""
    import scripts.run_eval as cli
    from ticketpilot.evaluation import loaders, predictions
    mock_result = type("MockLoadResult", (), {
        "is_valid": True,
        "errors": [],
        "missing_golden_for_ticket": [],
        "missing_ticket_for_golden": [],
        "dataset": type("MockDataset", (), {"golden": {}})(),
    })()
    with patch.object(loaders, "load_eval_dataset", return_value=mock_result):
        with patch.object(predictions, "load_predictions", return_value={}):
            with pytest.raises(SystemExit):
                args = cli.parse_args([
                    "--tickets", "t.csv",
                    "--golden", "g.csv",
                    "--predictions", "p.csv",
                    "--out-json", tmp_json,
                    "--out-md", tmp_md,
                ])
                cli.run_eval(args)


def test_cli_deterministic(tmp_json, tmp_md):
    """CLI is deterministic across repeated runs (except generated_at)."""
    import scripts.run_eval as cli
    args = cli.parse_args([
        "--tickets", HAPPY_TICKETS,
        "--golden", HAPPY_GOLDEN,
        "--predictions", HAPPY_PREDS,
        "--out-json", tmp_json,
        "--out-md", tmp_md,
    ])
    cli.run_eval(args)
    first = json.loads(pathlib.Path(tmp_json).read_text(encoding="utf-8"))
    del first["generated_at"]
    tmp2 = tempfile.mktemp(suffix=".json")
    try:
        args2 = cli.parse_args([
            "--tickets", HAPPY_TICKETS,
            "--golden", HAPPY_GOLDEN,
            "--predictions", HAPPY_PREDS,
            "--out-json", tmp2,
            "--out-md", tmp_md,
        ])
        cli.run_eval(args2)
        second = json.loads(pathlib.Path(tmp2).read_text(encoding="utf-8"))
        del second["generated_at"]
        assert first == second
    finally:
        pathlib.Path(tmp2).unlink(missing_ok=True)


def test_cli_extra_prediction_fails(tmp_json, tmp_md):
    """Extra prediction case_id fails validation."""
    import scripts.run_eval as cli
    extra_csv = tempfile.mktemp(suffix=".csv")
    try:
        with open(extra_csv, "w", encoding="utf-8") as f:
            f.write("case_id,predicted_issue_type,predicted_risk_flags,predicted_severity,predicted_must_human_review,predicted_evidence_doc_types,predicted_fallback_required,predicted_no_auto_send" + chr(10))
            f.write("case_001,refund,,LOW,false,FAQ,false,false" + chr(10))
            f.write("case_999,refund,,LOW,false,FAQ,false,false" + chr(10))
        with pytest.raises(SystemExit) as exc_info:
            args = cli.parse_args([
                "--tickets", HAPPY_TICKETS,
                "--golden", HAPPY_GOLDEN,
                "--predictions", extra_csv,
                "--out-json", tmp_json,
                "--out-md", tmp_md,
            ])
            cli.run_eval(args)
        assert exc_info.value.code != 0
    finally:
        pathlib.Path(extra_csv).unlink(missing_ok=True)
