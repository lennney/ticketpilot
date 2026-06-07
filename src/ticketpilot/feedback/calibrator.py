"""Calibration curve — bucket-based reliability analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ticketpilot.feedback.collector import FeedbackRecord


# Fixed bucket edges: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
BUCKET_EDGES: list[tuple[float, float]] = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0),
]


class CalibrationBucket(BaseModel):
    """Reliability data for one confidence bucket."""

    predicted_range: tuple[float, float]
    count: int = Field(ge=0)
    actual_accuracy: float = Field(ge=0, le=1)
    avg_predicted_confidence: float = Field(ge=0, le=1)


class CalibrationCurve(BaseModel):
    """Bucket-based calibration curve from feedback records."""

    buckets: list[CalibrationBucket] = Field(default_factory=list)

    @classmethod
    def build(cls, records: list[FeedbackRecord]) -> CalibrationCurve:
        """Build a calibration curve from feedback records.

        Groups records into fixed confidence buckets and computes
        actual accuracy (was_correct ratio) per bucket.
        """
        if not records:
            return cls(buckets=[])

        bucketed: dict[tuple[float, float], list[FeedbackRecord]] = {
            edge: [] for edge in BUCKET_EDGES
        }

        for rec in records:
            for lo, hi in BUCKET_EDGES:
                # Last bucket is inclusive on the right (0.8-1.0)
                if lo <= rec.predicted_confidence < hi or (hi == 1.0 and rec.predicted_confidence == 1.0):
                    bucketed[(lo, hi)].append(rec)
                    break

        buckets: list[CalibrationBucket] = []
        for lo, hi in BUCKET_EDGES:
            group = bucketed[(lo, hi)]
            if not group:
                continue
            correct = sum(1 for r in group if r.was_correct)
            avg_conf = sum(r.predicted_confidence for r in group) / len(group)
            buckets.append(
                CalibrationBucket(
                    predicted_range=(lo, hi),
                    count=len(group),
                    actual_accuracy=round(correct / len(group), 4),
                    avg_predicted_confidence=round(avg_conf, 4),
                )
            )

        return cls(buckets=buckets)

    def suggest_threshold(self, target_accuracy: float) -> float:
        """Find the lowest confidence threshold that achieves target_accuracy.

        Scans buckets from highest to lowest. Returns the lower edge of the
        first bucket whose actual_accuracy >= target_accuracy. Falls back to
        0.8 (high) if no bucket meets the target.
        """
        result = 0.8  # fallback: no bucket meets target
        for bucket in self.buckets:
            if bucket.actual_accuracy >= target_accuracy:
                result = bucket.predicted_range[0]
                break
        return result

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "buckets": [b.model_dump() for b in self.buckets],
        }
