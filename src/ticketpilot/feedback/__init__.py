"""Feedback loop for continuous calibration improvement.

Collects human review decisions, builds calibration curves,
and suggests optimal confidence thresholds.
"""

from ticketpilot.feedback.calibrator import (
    CalibrationBucket,
    CalibrationCurve,
    IsotonicCalibrator,
    ReliabilityDiagram,
)
from ticketpilot.feedback.collector import FeedbackCollector, FeedbackRecord
from ticketpilot.feedback.threshold_advisor import ThresholdAdvisor, ThresholdSuggestion

__all__ = [
    "CalibrationBucket",
    "CalibrationCurve",
    "FeedbackCollector",
    "FeedbackRecord",
    "IsotonicCalibrator",
    "ReliabilityDiagram",
    "ThresholdAdvisor",
    "ThresholdSuggestion",
]
