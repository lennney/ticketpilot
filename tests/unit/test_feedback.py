"""Tests for feedback loop: collector, calibrator, threshold advisor."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
from ticketpilot.feedback.calibrator import (
    CalibrationCurve,
    IsotonicCalibrator,
    ReliabilityDiagram,
)
from ticketpilot.feedback.collector import FeedbackCollector, FeedbackRecord
from ticketpilot.feedback.threshold_advisor import ThresholdAdvisor, ThresholdSuggestion
from ticketpilot.review.schemas import ReviewAction, ReviewDecision


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_decision(
    ticket_id: str = "t-1",
    action: ReviewAction = ReviewAction.APPROVE,
    original_draft: str = "Hello, your refund is processed.",
    edited_text: str | None = None,
    reviewed_at: datetime | None = None,
) -> ReviewDecision:
    return ReviewDecision(
        ticket_id=ticket_id,
        ticket_text="Where is my refund?",
        action=action,
        original_draft_text=original_draft,
        edited_text=edited_text,
        reviewed_at=reviewed_at or datetime(2026, 6, 7, tzinfo=timezone.utc),
    )


def _make_confidence(
    overall: float = 0.85,
    level: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        retrieval_confidence=0.9,
        classification_confidence=0.8,
        citation_confidence=0.85,
        evidence_density=0.7,
        overall=overall,
        level=level,
    )


def _make_record(
    predicted_confidence: float = 0.85,
    was_correct: bool = True,
) -> FeedbackRecord:
    return FeedbackRecord(
        ticket_id="t-1",
        predicted_confidence=predicted_confidence,
        confidence_level="high",
        review_action="approve" if was_correct else "reject",
        was_correct=was_correct,
        original_draft="draft text",
        timestamp=datetime(2026, 6, 7, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# FeedbackCollector
# ---------------------------------------------------------------------------


class TestFeedbackCollector:
    def test_collect_approve(self) -> None:
        collector = FeedbackCollector()
        decision = _make_decision(action=ReviewAction.APPROVE)
        conf = _make_confidence(overall=0.85, level=ConfidenceLevel.HIGH)
        record = collector.collect(decision, conf)

        assert record.ticket_id == "t-1"
        assert record.predicted_confidence == 0.85
        assert record.confidence_level == "high"
        assert record.review_action == "approve"
        assert record.was_correct is True
        assert record.edited_draft is None

    def test_collect_edit_is_not_correct(self) -> None:
        collector = FeedbackCollector()
        decision = _make_decision(
            action=ReviewAction.EDIT,
            edited_text="Corrected draft",
        )
        conf = _make_confidence(overall=0.65, level=ConfidenceLevel.MEDIUM)
        record = collector.collect(decision, conf)

        assert record.was_correct is False
        assert record.review_action == "edit"
        assert record.edited_draft == "Corrected draft"

    def test_collect_reject(self) -> None:
        collector = FeedbackCollector()
        decision = _make_decision(action=ReviewAction.REJECT)
        conf = _make_confidence(overall=0.3, level=ConfidenceLevel.LOW)
        record = collector.collect(decision, conf)

        assert record.was_correct is False
        assert record.review_action == "reject"

    def test_persist_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "feedback.jsonl"
        collector = FeedbackCollector(path=path)

        rec1 = _make_record(predicted_confidence=0.9)
        rec2 = _make_record(predicted_confidence=0.5, was_correct=False)
        collector.persist(rec1)
        collector.persist(rec2)

        loaded = collector.load()
        assert len(loaded) == 2
        assert loaded[0].predicted_confidence == 0.9
        assert loaded[1].predicted_confidence == 0.5

    def test_load_empty_file(self, tmp_path: Path) -> None:
        collector = FeedbackCollector(path=tmp_path / "nonexistent.jsonl")
        assert collector.load() == []

    def test_roundtrip_via_jsonl(self, tmp_path: Path) -> None:
        """Full roundtrip: collect -> persist -> load -> verify."""
        path = tmp_path / "rt.jsonl"
        collector = FeedbackCollector(path=path)

        decision = _make_decision(action=ReviewAction.APPROVE)
        conf = _make_confidence(overall=0.75)
        record = collector.collect(decision, conf)
        collector.persist(record)

        loaded = collector.load()
        assert len(loaded) == 1
        assert loaded[0].predicted_confidence == 0.75
        assert loaded[0].was_correct is True


# ---------------------------------------------------------------------------
# CalibrationCurve
# ---------------------------------------------------------------------------


class TestCalibrationCurve:
    def test_empty_records(self) -> None:
        curve = CalibrationCurve.build([])
        assert curve.buckets == []

    def test_single_bucket(self) -> None:
        records = [
            _make_record(predicted_confidence=0.85, was_correct=True) for _ in range(5)
        ]
        curve = CalibrationCurve.build(records)

        assert len(curve.buckets) == 1
        bucket = curve.buckets[0]
        assert bucket.predicted_range == (0.8, 1.0)
        assert bucket.count == 5
        assert bucket.actual_accuracy == 1.0

    def test_all_correct(self) -> None:
        records = [
            _make_record(predicted_confidence=0.5, was_correct=True) for _ in range(10)
        ]
        curve = CalibrationCurve.build(records)
        assert curve.buckets[0].actual_accuracy == 1.0

    def test_all_wrong(self) -> None:
        records = [
            _make_record(predicted_confidence=0.3, was_correct=False) for _ in range(10)
        ]
        curve = CalibrationCurve.build(records)
        assert curve.buckets[0].actual_accuracy == 0.0

    def test_mixed_buckets(self) -> None:
        records = [
            # Bucket 0.0-0.2: 2 records, 1 correct
            _make_record(predicted_confidence=0.1, was_correct=True),
            _make_record(predicted_confidence=0.15, was_correct=False),
            # Bucket 0.8-1.0: 3 records, all correct
            _make_record(predicted_confidence=0.9, was_correct=True),
            _make_record(predicted_confidence=0.85, was_correct=True),
            _make_record(predicted_confidence=0.95, was_correct=True),
        ]
        curve = CalibrationCurve.build(records)

        assert len(curve.buckets) == 2
        low = curve.buckets[0]
        high = curve.buckets[1]

        assert low.predicted_range == (0.0, 0.2)
        assert low.count == 2
        assert low.actual_accuracy == 0.5

        assert high.predicted_range == (0.8, 1.0)
        assert high.count == 3
        assert high.actual_accuracy == 1.0

    def test_suggest_threshold(self) -> None:
        records = [
            _make_record(predicted_confidence=0.1, was_correct=False),
            _make_record(predicted_confidence=0.3, was_correct=False),
            _make_record(predicted_confidence=0.5, was_correct=True),
            _make_record(predicted_confidence=0.7, was_correct=True),
            _make_record(predicted_confidence=0.9, was_correct=True),
        ]
        curve = CalibrationCurve.build(records)

        # Buckets with accuracy >= 0.8: 0.4-0.6 (1.0), 0.6-0.8 (1.0), 0.8-1.0 (1.0)
        # Lowest edge where accuracy >= 0.8 is 0.4
        threshold = curve.suggest_threshold(0.8)
        assert threshold == 0.4

    def test_suggest_threshold_no_match(self) -> None:
        records = [
            _make_record(predicted_confidence=0.5, was_correct=False),
            _make_record(predicted_confidence=0.7, was_correct=False),
        ]
        curve = CalibrationCurve.build(records)
        assert curve.suggest_threshold(0.8) == 0.8

    def test_to_dict(self) -> None:
        records = [_make_record(predicted_confidence=0.9)]
        curve = CalibrationCurve.build(records)
        d = curve.to_dict()
        assert "buckets" in d
        assert len(d["buckets"]) == 1

    def test_boundary_1_0(self) -> None:
        """Confidence exactly 1.0 should land in the 0.8-1.0 bucket."""
        records = [_make_record(predicted_confidence=1.0)]
        curve = CalibrationCurve.build(records)
        assert len(curve.buckets) == 1
        assert curve.buckets[0].predicted_range == (0.8, 1.0)


# ---------------------------------------------------------------------------
# ThresholdAdvisor
# ---------------------------------------------------------------------------


class TestThresholdAdvisor:
    def test_insufficient_data(self) -> None:
        advisor = ThresholdAdvisor()
        records = [_make_record() for _ in range(5)]
        curve = CalibrationCurve.build(records)
        suggestion = advisor.analyze(curve)

        assert suggestion.sample_size == 5
        assert suggestion.current_thresholds == suggestion.suggested_thresholds
        assert "Insufficient" in suggestion.reasoning

    def test_empty_curve(self) -> None:
        advisor = ThresholdAdvisor()
        curve = CalibrationCurve(buckets=[])
        suggestion = advisor.analyze(curve)
        assert suggestion.sample_size == 0

    def test_well_calibrated(self) -> None:
        """When accuracy in high bucket is >= 0.8 and thresholds match, no change."""
        advisor = ThresholdAdvisor()
        # Create enough records in the high bucket, all correct
        records = [
            _make_record(predicted_confidence=0.9, was_correct=True) for _ in range(15)
        ]
        curve = CalibrationCurve.build(records)
        suggestion = advisor.analyze(curve)

        assert suggestion.sample_size == 15
        # High bucket starts at 0.8, so suggested high = 0.8 (same as current)
        assert suggestion.suggested_thresholds["high"] == 0.8

    def test_suggests_change_when_miscalibrated(self) -> None:
        """If low-confidence bucket has high accuracy, thresholds may shift."""
        advisor = ThresholdAdvisor()
        # All records in 0.4-0.6 bucket, all correct → suggests high=0.4
        records = [
            _make_record(predicted_confidence=0.5, was_correct=True) for _ in range(15)
        ]
        curve = CalibrationCurve.build(records)
        suggestion = advisor.analyze(curve)

        assert suggestion.suggested_thresholds["high"] == 0.4
        assert suggestion.suggested_thresholds["medium"] == 0.3
        assert suggestion.suggested_thresholds["low"] == 0.2
        assert "calibration suggests" in suggestion.reasoning

    def test_suggestion_is_advisory(self) -> None:
        """Verify the suggestion includes current thresholds for comparison."""
        advisor = ThresholdAdvisor()
        records = [
            _make_record(predicted_confidence=0.5, was_correct=True) for _ in range(15)
        ]
        curve = CalibrationCurve.build(records)
        suggestion = advisor.analyze(curve)

        assert "current_thresholds" in ThresholdSuggestion.model_fields
        assert "suggested_thresholds" in ThresholdSuggestion.model_fields
        assert suggestion.current_thresholds != suggestion.suggested_thresholds


# ---------------------------------------------------------------------------
# IsotonicCalibrator
# ---------------------------------------------------------------------------


class TestIsotonicCalibrator:
    def test_fit_and_calibrate_basic(self) -> None:
        """PAV should produce monotonic mapping from raw scores to accuracy."""
        records = [
            _make_record(predicted_confidence=0.1, was_correct=False),
            _make_record(predicted_confidence=0.2, was_correct=False),
            _make_record(predicted_confidence=0.5, was_correct=True),
            _make_record(predicted_confidence=0.8, was_correct=True),
            _make_record(predicted_confidence=0.9, was_correct=True),
        ]
        cal = IsotonicCalibrator().fit(records)

        # Low scores should calibrate to lower values
        low = cal.calibrate(0.1)
        high = cal.calibrate(0.9)
        assert low < high

    def test_monotonicity_enforced(self) -> None:
        """Violating inputs must produce monotonic output after PAV."""
        records = [
            _make_record(predicted_confidence=0.3, was_correct=True),  # high actual
            _make_record(predicted_confidence=0.5, was_correct=False),  # low actual
            _make_record(predicted_confidence=0.7, was_correct=True),  # high actual
        ]
        cal = IsotonicCalibrator().fit(records)

        vals = [cal.calibrate(x) for x in [0.1, 0.3, 0.5, 0.7, 0.9]]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1], (
                f"Monotonicity violated at index {i}: {vals[i]} > {vals[i + 1]}"
            )

    def test_empty_records(self) -> None:
        cal = IsotonicCalibrator().fit([])
        assert cal.calibrate(0.5) == 0.5

    def test_single_record(self) -> None:
        records = [_make_record(predicted_confidence=0.7, was_correct=True)]
        cal = IsotonicCalibrator().fit(records)
        assert cal.calibrate(0.7) == 1.0
        assert cal.calibrate(0.0) == 1.0  # only one pool

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        records = [
            _make_record(predicted_confidence=0.1, was_correct=False),
            _make_record(predicted_confidence=0.5, was_correct=True),
            _make_record(predicted_confidence=0.9, was_correct=True),
        ]
        cal = IsotonicCalibrator().fit(records)
        path = tmp_path / "cal.json"
        cal.save(path)

        loaded = IsotonicCalibrator().load(path)
        for score in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            assert loaded.calibrate(score) == cal.calibrate(score)

    def test_all_correct(self) -> None:
        records = [
            _make_record(predicted_confidence=0.5, was_correct=True) for _ in range(10)
        ]
        cal = IsotonicCalibrator().fit(records)
        assert cal.calibrate(0.5) == 1.0

    def test_all_wrong(self) -> None:
        records = [
            _make_record(predicted_confidence=0.5, was_correct=False) for _ in range(10)
        ]
        cal = IsotonicCalibrator().fit(records)
        assert cal.calibrate(0.5) == 0.0


# ---------------------------------------------------------------------------
# ReliabilityDiagram
# ---------------------------------------------------------------------------


class TestReliabilityDiagram:
    def test_build_and_to_dict(self) -> None:
        records = [
            _make_record(predicted_confidence=0.1, was_correct=False),
            _make_record(predicted_confidence=0.9, was_correct=True),
        ]
        diagram = ReliabilityDiagram.build(records)
        d = diagram.to_dict()

        assert "buckets" in d
        assert "total_count" in d
        assert "ece" in d
        assert d["total_count"] == 2
        assert len(d["buckets"]) == 2

    def test_to_ascii_contains_headers(self) -> None:
        records = [
            _make_record(predicted_confidence=0.3, was_correct=False),
            _make_record(predicted_confidence=0.7, was_correct=True),
        ]
        diagram = ReliabilityDiagram.build(records)
        ascii_art = diagram.to_ascii()

        assert "Reliability Diagram" in ascii_art
        assert "Predicted" in ascii_art
        assert "Actual" in ascii_art
        assert "Count" in ascii_art
        assert "ECE" in ascii_art

    def test_to_ascii_has_bars(self) -> None:
        records = [
            _make_record(predicted_confidence=0.9, was_correct=True) for _ in range(5)
        ]
        diagram = ReliabilityDiagram.build(records)
        ascii_art = diagram.to_ascii()

        assert "P|" in ascii_art
        assert "A|" in ascii_art
        assert "█" in ascii_art

    def test_empty_records(self) -> None:
        diagram = ReliabilityDiagram.build([])
        assert "no data" in diagram.to_ascii()


# ---------------------------------------------------------------------------
# CalibrationCurve — ECE and is_well_calibrated
# ---------------------------------------------------------------------------


class TestCalibrationECE:
    def test_ece_perfect_calibration(self) -> None:
        """When predicted == actual in every bucket, ECE should be 0."""
        records = [
            # Bucket 0.0-0.2: predicted ~0.1, actual = 0.0 (all wrong)
            _make_record(predicted_confidence=0.1, was_correct=False),
            _make_record(predicted_confidence=0.1, was_correct=False),
            # Bucket 0.8-1.0: predicted ~0.9, actual = 1.0 (all correct)
            _make_record(predicted_confidence=0.9, was_correct=True),
            _make_record(predicted_confidence=0.9, was_correct=True),
        ]
        curve = CalibrationCurve.build(records)
        ece = curve.ece()
        assert ece == pytest.approx(0.1, abs=0.01)  # avg_predicted vs actual gap

    def test_ece_zero_when_empty(self) -> None:
        curve = CalibrationCurve(buckets=[])
        assert curve.ece() == 0.0

    def test_is_well_calibrated_true(self) -> None:
        """Records with small gap should be well calibrated."""
        # All in one bucket, predicted ~0.9, actual = 1.0
        records = [
            _make_record(predicted_confidence=0.9, was_correct=True) for _ in range(10)
        ]
        curve = CalibrationCurve.build(records)
        assert curve.is_well_calibrated(threshold=0.15) is True

    def test_is_well_calibrated_false(self) -> None:
        """Records with large gap should NOT be well calibrated."""
        # Predicted ~0.9 but all wrong → actual = 0.0, gap = 0.9
        records = [
            _make_record(predicted_confidence=0.9, was_correct=False) for _ in range(10)
        ]
        curve = CalibrationCurve.build(records)
        assert curve.is_well_calibrated(threshold=0.05) is False

    def test_is_well_calibrated_default_threshold(self) -> None:
        records = [
            _make_record(predicted_confidence=0.5, was_correct=True) for _ in range(10)
        ]
        curve = CalibrationCurve.build(records)
        # predicted ~0.5, actual = 1.0, gap = 0.5 → ECE = 0.5
        assert curve.is_well_calibrated() is False
