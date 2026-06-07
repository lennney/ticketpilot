"""Calibration curve, isotonic regression calibrator, and reliability diagram."""

from __future__ import annotations

import json
from pathlib import Path
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

    def ece(self) -> float:
        """Expected Calibration Error — weighted avg of |predicted - actual| per bucket."""
        if not self.buckets:
            return 0.0
        total_count = sum(b.count for b in self.buckets)
        if total_count == 0:
            return 0.0
        weighted_sum = sum(
            b.count * abs(b.avg_predicted_confidence - b.actual_accuracy)
            for b in self.buckets
        )
        return round(weighted_sum / total_count, 4)

    def is_well_calibrated(self, threshold: float = 0.05) -> bool:
        """True if ECE is below the given threshold."""
        return self.ece() < threshold

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "buckets": [b.model_dump() for b in self.buckets],
        }


# ---------------------------------------------------------------------------
# Isotonic Regression Calibrator (PAV — Pool Adjacent Violators)
# ---------------------------------------------------------------------------


class IsotonicCalibrator:
    """Monotonic calibration via Pool Adjacent Violators algorithm.

    Fits a piecewise-constant, non-decreasing function that maps raw
    confidence scores to calibrated probabilities.  No scipy/sklearn
    dependency — pure Python PAV implementation.
    """

    def __init__(self) -> None:
        self._thresholds: list[float] = []
        self._calibrated: list[float] = []

    def fit(self, records: list[FeedbackRecord]) -> IsotonicCalibrator:
        """Fit monotonic calibration from feedback records.

        Sorts by predicted_confidence, computes per-record accuracy
        (was_correct as 0/1), then applies PAV to enforce monotonicity.
        """
        if not records:
            return self

        sorted_recs = sorted(records, key=lambda r: r.predicted_confidence)
        xs = [r.predicted_confidence for r in sorted_recs]
        ys = [1.0 if r.was_correct else 0.0 for r in sorted_recs]

        # PAV algorithm: pool adjacent violators
        pools: list[list[int]] = [[i] for i in range(len(ys))]
        pool_means = list(ys)

        i = 0
        while i < len(pools) - 1:
            if pool_means[i] > pool_means[i + 1]:
                # Merge pools i and i+1
                merged = pools[i] + pools[i + 1]
                merged_mean = sum(ys[j] for j in merged) / len(merged)
                pools[i] = merged
                pool_means[i] = merged_mean
                pools.pop(i + 1)
                pool_means.pop(i + 1)
                # Step back to re-check with previous pool
                if i > 0:
                    i -= 1
            else:
                i += 1

        # Build threshold/calibrated arrays from pools
        self._thresholds = []
        self._calibrated = []
        for pool, mean in zip(pools, pool_means):
            self._thresholds.append(xs[pool[0]])
            self._calibrated.append(round(mean, 6))

        return self

    def calibrate(self, raw_score: float) -> float:
        """Map a raw confidence score to a calibrated probability.

        Uses piecewise-constant interpolation from the fitted PAV function.
        Scores below the first threshold map to the first calibrated value;
        scores above the last threshold map to the last calibrated value.
        """
        if not self._thresholds:
            return raw_score

        # Binary search for the rightmost threshold <= raw_score
        lo, hi = 0, len(self._thresholds) - 1
        result = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._thresholds[mid] <= raw_score:
                result = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return self._calibrated[result]

    def save(self, path: str | Path) -> None:
        """Persist calibration parameters to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "thresholds": self._thresholds,
            "calibrated": self._calibrated,
        }
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: str | Path) -> IsotonicCalibrator:
        """Load calibration parameters from JSON."""
        path = Path(path)
        data = json.loads(path.read_text())
        self._thresholds = data["thresholds"]
        self._calibrated = data["calibrated"]
        return self


# ---------------------------------------------------------------------------
# Reliability Diagram
# ---------------------------------------------------------------------------


class ReliabilityDiagram:
    """Reliability diagram showing predicted vs actual calibration."""

    def __init__(
        self,
        buckets: list[dict],
        total_count: int,
        ece: float,
    ) -> None:
        self._buckets = buckets
        self._total_count = total_count
        self._ece = ece

    @classmethod
    def build(cls, records: list[FeedbackRecord]) -> ReliabilityDiagram:
        """Build a reliability diagram from feedback records."""
        curve = CalibrationCurve.build(records)
        total = sum(b.count for b in curve.buckets)
        buckets = [
            {
                "range": f"{b.predicted_range[0]:.1f}-{b.predicted_range[1]:.1f}",
                "predicted": b.avg_predicted_confidence,
                "actual": b.actual_accuracy,
                "count": b.count,
            }
            for b in curve.buckets
        ]
        return cls(buckets=buckets, total_count=total, ece=curve.ece())

    def to_ascii(self) -> str:
        """Render an ASCII reliability diagram for terminal output."""
        if not self._buckets:
            return "Reliability Diagram (no data)"

        width = 40
        lines = [
            "Reliability Diagram",
            "=" * (width + 30),
            f"{'Bucket':<10} {'Predicted':>9} {'Actual':>9} {'Count':>6}  Bar",
            "-" * (width + 30),
        ]

        for b in self._buckets:
            pred_bar_len = int(b["predicted"] * width)
            act_bar_len = int(b["actual"] * width)
            pred_bar = "█" * pred_bar_len + "░" * (width - pred_bar_len)
            act_bar = "█" * act_bar_len + "░" * (width - act_bar_len)

            lines.append(
                f"{b['range']:<10} {b['predicted']:>9.4f} {b['actual']:>9.4f} {b['count']:>6}  "
                f"P|{pred_bar}|"
            )
            lines.append(
                f"{'':>10} {'':>9} {'':>9} {'':>6}  A|{act_bar}|"
            )

        lines.append("-" * (width + 30))
        lines.append(f"Total samples: {self._total_count}  |  ECE: {self._ece:.4f}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "buckets": self._buckets,
            "total_count": self._total_count,
            "ece": self._ece,
        }
