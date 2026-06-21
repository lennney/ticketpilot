"""Integration tests for pipeline-backed evaluation prediction.

These tests run the full local TicketPilot pipeline (intake -> classify ->
assess risk -> retrieve evidence -> draft) on all evaluation tickets and verify
that the resulting predictions can be scored against golden expectations.

Requires a live database with seed data. Skips if DB is unavailable,
but the quality gate counts skips as failure unless TICKETPILOT_SKIP_DB_TESTS=1.
"""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from ticketpilot.evaluation.loaders import load_eval_dataset
from ticketpilot.evaluation.metrics import (
    compute_evaluation_summary,
)
from ticketpilot.evaluation.pipeline_predictions import predict_from_pipeline
from ticketpilot.evaluation.reporting import (
    write_json_report,
    write_markdown_report,
)

TICKETS_PATH = "data/eval/tickets_eval.csv"
GOLDEN_PATH = "data/eval/golden_expectations.csv"


# Dynamically load case IDs from the actual CSV files
def _load_all_case_ids():
    import csv

    with open(TICKETS_PATH, encoding="utf-8") as f:
        return [row["case_id"] for row in csv.DictReader(f)]


def _load_high_risk_case_ids():
    import csv

    result = set()
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("expected_risk_flags", "").strip():
                result.add(row["case_id"])
    return result


ALL_CASE_IDS = _load_all_case_ids()
HIGH_RISK_CASE_IDS = _load_high_risk_case_ids()


class TestPipelinePredictions:
    """Integration tests for pipeline-backed EvalPrediction generation."""

    @pytest.fixture(scope="class")
    def db_available(self):
        """Check if database is available."""
        try:
            from ticketpilot.retrieval.db.connection import get_db_connection

            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    @pytest.fixture(scope="class")
    def ensure_seeded(self, db_available):
        """Ensure database is seeded with test data."""
        if not db_available:
            pytest.skip("Database not available")
        try:
            from ticketpilot.retrieval.db.seeding import (
                seed_knowledge_chunks,
                get_chunk_count,
            )

            if get_chunk_count() == 0:
                seed_knowledge_chunks(clear_existing=True)
        except Exception as e:
            pytest.skip(f"Could not seed database: {e}")

    @pytest.fixture(scope="class")
    def dataset(self):
        """Load the evaluation dataset."""
        load_result = load_eval_dataset(TICKETS_PATH, GOLDEN_PATH)
        assert load_result.is_valid, f"Dataset load errors: {load_result.errors}"
        return load_result.dataset

    @pytest.fixture(scope="class")
    def pipeline_predictions(self, db_available, ensure_seeded, dataset):
        """Generate predictions from the pipeline for all eval tickets."""
        if not db_available:
            pytest.skip("Database not available")

        predictions = {}
        for case_id in sorted(dataset.tickets.keys()):
            ticket = dataset.tickets[case_id]
            predictions[case_id] = predict_from_pipeline(ticket)
        return predictions

    # ------------------------------------------------------------------
    # Basic prediction shape
    # ------------------------------------------------------------------

    def test_one_prediction_per_case(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """Pipeline produces exactly one prediction per eval ticket."""
        if not db_available:
            pytest.skip("Database not available")
        assert len(pipeline_predictions) == len(ALL_CASE_IDS)

    def test_no_missing_or_extra_case_ids(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """Every case_id has a prediction and no extra case_ids appear."""
        if not db_available:
            pytest.skip("Database not available")
        predicted_ids = set(pipeline_predictions.keys())
        expected_ids = set(ALL_CASE_IDS)
        missing = expected_ids - predicted_ids
        extra = predicted_ids - expected_ids
        assert not missing, f"Missing predictions for: {sorted(missing)}"
        assert not extra, f"Extra predictions for: {sorted(extra)}"

    def test_prediction_has_all_required_fields(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """Each prediction has all expected EvalPrediction fields."""
        if not db_available:
            pytest.skip("Database not available")
        for pred in pipeline_predictions.values():
            assert pred.case_id in ALL_CASE_IDS
            assert isinstance(pred.predicted_issue_type, str)
            assert isinstance(pred.predicted_risk_flags, frozenset)
            assert isinstance(pred.predicted_severity, str)
            assert isinstance(pred.predicted_must_human_review, bool)
            assert isinstance(pred.predicted_evidence_doc_types, frozenset)
            assert isinstance(pred.predicted_fallback_required, bool)
            assert isinstance(pred.predicted_no_auto_send, bool)
            assert pred.predicted_severity in ("LOW", "MEDIUM", "HIGH")

    # ------------------------------------------------------------------
    # Specific field assertions
    # ------------------------------------------------------------------

    def test_no_auto_send_always_true(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """predicted_no_auto_send is always True per design."""
        if not db_available:
            pytest.skip("Database not available")
        for pred in pipeline_predictions.values():
            assert pred.predicted_no_auto_send is True, (
                f"{pred.case_id}: predicted_no_auto_send should be True"
            )

    def test_high_risk_cases_have_must_human_review_true(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """Cases flagged by pipeline risk assessor get must_human_review=True."""
        if not db_available:
            pytest.skip("Database not available")
        for case_id, pred in pipeline_predictions.items():
            if len(pred.predicted_risk_flags) > 0:
                assert pred.predicted_must_human_review is True, (
                    f"{case_id}: expected must_human_review=True for flagged case"
                )

    def test_no_risk_cases_have_empty_risk_flags(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """Some cases have empty risk flags per pipeline risk assessor."""
        if not db_available:
            pytest.skip("Database not available")
        no_risk_ids = [
            cid
            for cid, p in pipeline_predictions.items()
            if len(p.predicted_risk_flags) == 0
        ]
        assert len(no_risk_ids) > 0, "Expected at least one no-risk case"

    def test_fallback_required_is_boolean(
        self, db_available, ensure_seeded, pipeline_predictions
    ):
        """predicted_fallback_required is always a boolean."""
        if not db_available:
            pytest.skip("Database not available")
        for pred in pipeline_predictions.values():
            assert isinstance(pred.predicted_fallback_required, bool), (
                f"{pred.case_id}: fallback_required should be bool"
            )

    # ------------------------------------------------------------------
    # Scorability by metrics module
    # ------------------------------------------------------------------

    def test_predictions_can_be_scored_by_metrics(
        self, db_available, ensure_seeded, pipeline_predictions, dataset
    ):
        """Pipeline predictions pass validate_predictions and produce metrics."""
        if not db_available:
            pytest.skip("Database not available")
        # This should not raise
        summary = compute_evaluation_summary(pipeline_predictions, dataset.golden)
        assert summary.total_cases == len(ALL_CASE_IDS)
        assert summary.total_cases == len(summary.results)
        # All aggregate metrics should be populated and in range
        assert 0.0 <= summary.aggregate_intent_accuracy <= 1.0
        assert 0.0 <= summary.aggregate_severity_accuracy <= 1.0
        assert 0.0 <= summary.aggregate_evidence_doc_type_recall <= 1.0
        assert 0.0 <= summary.aggregate_no_auto_send_compliance <= 1.0
        assert 0.0 <= summary.aggregate_must_human_review_accuracy <= 1.0
        assert 0.0 <= summary.aggregate_fallback_correctness <= 1.0

    # ------------------------------------------------------------------
    # Report generation for pipeline mode
    # ------------------------------------------------------------------

    def test_pipeline_mode_reports_generated(
        self, db_available, ensure_seeded, pipeline_predictions, dataset
    ):
        """Pipeline mode can generate JSON and Markdown reports."""
        if not db_available:
            pytest.skip("Database not available")

        summary = compute_evaluation_summary(pipeline_predictions, dataset.golden)

        tmp_json = tempfile.mktemp(suffix=".json")
        tmp_md = tempfile.mktemp(suffix=".md")
        try:
            write_json_report(
                summary,
                tmp_json,
                tickets_path=TICKETS_PATH,
                golden_path=GOLDEN_PATH,
                predictions_path="pipeline",
                prediction_mode="pipeline",
            )
            write_markdown_report(
                summary,
                tmp_md,
                tickets_path=TICKETS_PATH,
                golden_path=GOLDEN_PATH,
                predictions_path="pipeline",
                prediction_mode="pipeline",
            )

            # Verify JSON report
            assert pathlib.Path(tmp_json).exists()
            data = json.loads(pathlib.Path(tmp_json).read_text(encoding="utf-8"))
            assert data["total_cases"] == len(ALL_CASE_IDS)
            assert data["metadata"]["prediction_mode"] == "pipeline"
            assert "aggregate_metrics" in data

            # Verify Markdown report
            md = pathlib.Path(tmp_md).read_text(encoding="utf-8")
            assert "# Evaluation Report" in md
            assert "Pipeline mode" in md or "pipeline" in md.lower()
            assert "## Limitations" in md
        finally:
            pathlib.Path(tmp_json).unlink(missing_ok=True)
            pathlib.Path(tmp_md).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # CLI pipeline mode
    # ------------------------------------------------------------------

    def test_cli_pipeline_mode_works(self, db_available, ensure_seeded):
        """CLI --prediction-mode pipeline runs end-to-end."""
        if not db_available:
            pytest.skip("Database not available")

        import scripts.run_eval as cli

        tmp_json = tempfile.mktemp(suffix=".json")
        tmp_md = tempfile.mktemp(suffix=".md")
        try:
            args = cli.parse_args(
                [
                    "--tickets",
                    TICKETS_PATH,
                    "--golden",
                    GOLDEN_PATH,
                    "--prediction-mode",
                    "pipeline",
                    "--out-json",
                    tmp_json,
                    "--out-md",
                    tmp_md,
                ]
            )
            cli.run_eval(args)

            assert pathlib.Path(tmp_json).exists()
            assert pathlib.Path(tmp_md).exists()

            data = json.loads(pathlib.Path(tmp_json).read_text(encoding="utf-8"))
            assert data["total_cases"] == len(ALL_CASE_IDS)
            assert data["metadata"]["prediction_mode"] == "pipeline"
        finally:
            pathlib.Path(tmp_json).unlink(missing_ok=True)
            pathlib.Path(tmp_md).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # CSV mode still works
    # ------------------------------------------------------------------

    def test_cli_csv_prediction_mode_still_works(self, db_available, ensure_seeded):
        """CLI CSV prediction mode still works (regression test)."""
        # CSV mode does not need DB — it loads predictions from file
        import scripts.run_eval as cli

        tmp_json = tempfile.mktemp(suffix=".json")
        tmp_md = tempfile.mktemp(suffix=".md")
        try:
            args = cli.parse_args(
                [
                    "--tickets",
                    TICKETS_PATH,
                    "--golden",
                    GOLDEN_PATH,
                    "--predictions",
                    "data/eval/sample_predictions.csv",
                    "--out-json",
                    tmp_json,
                    "--out-md",
                    tmp_md,
                ]
            )
            cli.run_eval(args)

            assert pathlib.Path(tmp_json).exists()
            assert pathlib.Path(tmp_md).exists()

            data = json.loads(pathlib.Path(tmp_json).read_text(encoding="utf-8"))
            assert data["total_cases"] == len(ALL_CASE_IDS)
            assert data["metadata"]["prediction_mode"] == "csv"
        finally:
            pathlib.Path(tmp_json).unlink(missing_ok=True)
            pathlib.Path(tmp_md).unlink(missing_ok=True)
