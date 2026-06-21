"""Threshold advisor — suggests optimal confidence thresholds from calibration data."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ticketpilot.confidence.scorer import THRESHOLDS
from ticketpilot.feedback.calibrator import CalibrationCurve


class ThresholdSuggestion(BaseModel):
    """Suggested threshold changes with reasoning."""

    current_thresholds: dict[str, float] = Field(
        description="Active thresholds: high/medium/low"
    )
    suggested_thresholds: dict[str, float] = Field(
        description="Proposed new thresholds"
    )
    reasoning: str = Field(description="Human-readable explanation")
    sample_size: int = Field(ge=0, description="Number of records analyzed")


class ThresholdAdvisor:
    """Analyzes calibration data and suggests threshold adjustments.

    Does NOT auto-apply changes — output is advisory for human review.
    """

    MIN_SAMPLE_SIZE = 10

    def analyze(self, curve: CalibrationCurve) -> ThresholdSuggestion:
        """Produce a ThresholdSuggestion from a CalibrationCurve.

        Strategy:
        - If sample is too small, recommend keeping current thresholds.
        - Otherwise, find the lowest bucket boundary where accuracy >= 0.8
          and use it as the new high threshold. Medium and low scale down
          proportionally.
        """
        total = sum(b.count for b in curve.buckets)
        current = dict(THRESHOLDS)

        if total < self.MIN_SAMPLE_SIZE or not curve.buckets:
            return ThresholdSuggestion(
                current_thresholds=current,
                suggested_thresholds=current,
                reasoning=(
                    f"Insufficient data ({total} records, need {self.MIN_SAMPLE_SIZE}). "
                    "Keeping current thresholds."
                ),
                sample_size=total,
            )

        # Find suggested high threshold from calibration
        suggested_high = curve.suggest_threshold(0.8)

        # Scale medium and low proportionally
        # Original ratios: high=0.8, medium=0.6, low=0.4
        # medium = high * 0.75, low = high * 0.5
        suggested = {
            "high": round(suggested_high, 2),
            "medium": round(suggested_high * 0.75, 2),
            "low": round(suggested_high * 0.5, 2),
        }

        changed = any(abs(suggested[k] - current[k]) > 0.01 for k in current)

        if changed:
            reasoning = (
                f"Based on {total} records: calibration suggests high={suggested['high']}, "
                f"medium={suggested['medium']}, low={suggested['low']}. "
                "Review before applying."
            )
        else:
            reasoning = (
                f"Based on {total} records: current thresholds are well-calibrated. "
                "No change recommended."
            )

        return ThresholdSuggestion(
            current_thresholds=current,
            suggested_thresholds=suggested,
            reasoning=reasoning,
            sample_size=total,
        )
