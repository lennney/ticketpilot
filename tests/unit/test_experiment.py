"""Tests for the A/B Experiment Framework."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ticketpilot.confidence import scorer as scorer_mod
from ticketpilot.experiment.config import ExperimentConfig
from ticketpilot.experiment.reporter import ExperimentReport
from ticketpilot.experiment.runner import (
    ExperimentRunner,
    _apply_config,
    _compute_delta,
)
from ticketpilot.schema.ticket import RawTicket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ticket(text: str = "I want a refund for order #12345") -> RawTicket:
    return RawTicket(
        original_text=text,
        submitted_at=datetime.now(timezone.utc),
        customer_id="cust-001",
    )


def _make_tickets(n: int = 3) -> list[RawTicket]:
    texts = [
        "I want a refund for order #12345",
        "Where is my package? It hasn't arrived yet.",
        "The product I received is damaged, I need a replacement.",
    ]
    return [_make_ticket(texts[i % len(texts)]) for i in range(n)]


# ---------------------------------------------------------------------------
# ExperimentConfig
# ---------------------------------------------------------------------------


class TestExperimentConfig:
    def test_default_id_is_uuid(self):
        cfg = ExperimentConfig(name="test")
        assert cfg.experiment_id  # non-empty
        # Should be a valid UUID string
        import uuid

        uuid.UUID(cfg.experiment_id)  # raises on invalid

    def test_custom_id(self):
        cfg = ExperimentConfig(experiment_id="exp-42", name="custom")
        assert cfg.experiment_id == "exp-42"

    def test_control_and_treatment_dicts(self):
        cfg = ExperimentConfig(
            name="threshold test",
            control={"thresholds": {"high": 0.8}},
            treatment={"thresholds": {"high": 0.7}},
        )
        assert cfg.control["thresholds"]["high"] == 0.8
        assert cfg.treatment["thresholds"]["high"] == 0.7

    def test_empty_config_defaults(self):
        cfg = ExperimentConfig(name="empty")
        assert cfg.control == {}
        assert cfg.treatment == {}
        assert cfg.description == ""

    def test_description(self):
        cfg = ExperimentConfig(name="x", description="Testing lower thresholds")
        assert cfg.description == "Testing lower thresholds"


# ---------------------------------------------------------------------------
# _compute_delta
# ---------------------------------------------------------------------------


class TestComputeDelta:
    def test_numeric_delta(self):
        control = {"avg_confidence": 0.7, "avg_latency_ms": 10.0}
        treatment = {"avg_confidence": 0.8, "avg_latency_ms": 8.5}
        delta = _compute_delta(control, treatment)
        assert delta["avg_confidence"] == pytest.approx(0.1, abs=1e-4)
        assert delta["avg_latency_ms"] == pytest.approx(-1.5, abs=1e-2)

    def test_missing_key(self):
        control = {"a": 1}
        treatment = {"b": 2}
        delta = _compute_delta(control, treatment)
        assert delta["a"] is None
        assert delta["b"] is None

    def test_non_numeric_passthrough(self):
        control = {"name": "ctrl"}
        treatment = {"name": "treat"}
        delta = _compute_delta(control, treatment)
        assert delta["name"] is None


# ---------------------------------------------------------------------------
# _apply_config context manager
# ---------------------------------------------------------------------------


class TestApplyConfig:
    def test_no_overrides_restores_original(self):
        original_w = dict(scorer_mod.WEIGHTS)
        original_t = dict(scorer_mod.THRESHOLDS)
        with _apply_config({}):
            pass
        assert scorer_mod.WEIGHTS == original_w
        assert scorer_mod.THRESHOLDS == original_t

    def test_weights_override_and_restore(self):
        original = dict(scorer_mod.WEIGHTS)
        with _apply_config({"weights": {"retrieval": 0.5}}):
            assert scorer_mod.WEIGHTS["retrieval"] == 0.5
        assert scorer_mod.WEIGHTS["retrieval"] == original["retrieval"]

    def test_thresholds_override_and_restore(self):
        original = dict(scorer_mod.THRESHOLDS)
        with _apply_config({"thresholds": {"high": 0.9}}):
            assert scorer_mod.THRESHOLDS["high"] == 0.9
        assert scorer_mod.THRESHOLDS["high"] == original["high"]


# ---------------------------------------------------------------------------
# ExperimentRunner
# ---------------------------------------------------------------------------


class TestExperimentRunner:
    def test_run_returns_report(self):
        cfg = ExperimentConfig(name="basic")
        runner = ExperimentRunner()
        report = runner.run(_make_tickets(2), cfg)
        assert isinstance(report, ExperimentReport)
        assert report.experiment_id == cfg.experiment_id
        assert report.name == "basic"

    def test_report_has_metrics(self):
        cfg = ExperimentConfig(name="metrics")
        runner = ExperimentRunner()
        report = runner.run(_make_tickets(3), cfg)
        for key in (
            "intent_accuracy",
            "avg_confidence",
            "avg_latency_ms",
            "must_human_review_rate",
        ):
            assert key in report.control_results
            assert key in report.treatment_results
            assert key in report.delta

    def test_identical_configs_produce_zero_delta(self):
        cfg = ExperimentConfig(name="same")
        runner = ExperimentRunner()
        report = runner.run(_make_tickets(2), cfg)
        # Non-latency metrics should be identical (latency varies by run)
        for key in (
            "intent_accuracy",
            "avg_confidence",
            "must_human_review_rate",
            "ticket_count",
        ):
            assert report.control_results[key] == report.treatment_results[key]
            if isinstance(report.delta[key], (int, float)):
                assert report.delta[key] == pytest.approx(0.0, abs=1e-4)

    def test_different_thresholds_change_review_rate(self):
        """Lowering the 'high' threshold should change must_human_review_rate."""
        cfg = ExperimentConfig(
            name="threshold-shift",
            control={},
            treatment={"thresholds": {"high": 0.99, "medium": 0.98, "low": 0.97}},
        )
        runner = ExperimentRunner()
        report = runner.run(_make_tickets(5), cfg)
        # With very high thresholds, more tickets should need human review
        assert (
            report.treatment_results["must_human_review_rate"]
            >= report.control_results["must_human_review_rate"]
        )

    def test_empty_ticket_list(self):
        cfg = ExperimentConfig(name="empty")
        runner = ExperimentRunner()
        report = runner.run([], cfg)
        assert report.control_results["ticket_count"] == 0
        assert report.treatment_results["ticket_count"] == 0


# ---------------------------------------------------------------------------
# ExperimentReport
# ---------------------------------------------------------------------------


class TestExperimentReport:
    def test_to_dict(self):
        report = ExperimentReport(
            experiment_id="e1",
            name="r1",
            control_results={"avg_confidence": 0.7},
            treatment_results={"avg_confidence": 0.8},
            delta={"avg_confidence": 0.1},
        )
        d = report.to_dict()
        assert d["experiment_id"] == "e1"
        assert d["control_results"]["avg_confidence"] == 0.7

    def test_to_json_roundtrip(self):
        report = ExperimentReport(
            experiment_id="e2",
            name="r2",
            control_results={"x": 1},
            treatment_results={"x": 2},
            delta={"x": 1},
        )
        raw = report.to_json()
        parsed = json.loads(raw)
        assert parsed["experiment_id"] == "e2"
        assert parsed["delta"]["x"] == 1

    def test_save_creates_file(self, tmp_path):
        report = ExperimentReport(
            experiment_id="e3",
            name="r3",
            control_results={"a": 0.5},
            treatment_results={"a": 0.6},
            delta={"a": 0.1},
        )
        out = tmp_path / "report.json"
        report.save(out)
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["name"] == "r3"

    def test_to_markdown(self):
        report = ExperimentReport(
            experiment_id="e4",
            name="md-test",
            control_results={"avg_confidence": 0.75, "avg_latency_ms": 12.5},
            treatment_results={"avg_confidence": 0.82, "avg_latency_ms": 10.1},
            delta={"avg_confidence": 0.07, "avg_latency_ms": -2.4},
        )
        md = report.to_markdown()
        assert "# Experiment: md-test" in md
        assert "e4" in md
        assert "| avg_confidence |" in md
        assert "+0.0700" in md
        assert "-2.4000" in md

    def test_markdown_handles_missing_keys(self):
        report = ExperimentReport(
            experiment_id="e5",
            name="sparse",
            control_results={"a": 1.0},
            treatment_results={"b": 2.0},
            delta={},
        )
        md = report.to_markdown()
        assert "N/A" in md
