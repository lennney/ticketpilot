"""Feedback collector — records human review outcomes for calibration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ticketpilot.confidence.scorer import ConfidenceBreakdown
    from ticketpilot.review.schemas import ReviewDecision


class FeedbackRecord(BaseModel):
    """A single feedback record linking predicted confidence to human outcome."""

    ticket_id: str
    predicted_confidence: float = Field(ge=0, le=1)
    confidence_level: str  # high/medium/low/critical
    review_action: str  # approve/edit/escalate/reject
    was_correct: bool  # approve=True, reject=False, edit=partial (False)
    original_draft: str
    edited_draft: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackCollector:
    """Collects and persists feedback records from human reviews.

    Usage:
        collector = FeedbackCollector()
        record = collector.collect(decision, confidence_breakdown)
        collector.persist(record)
        all_records = collector.load()
    """

    def __init__(self, path: str | Path = "feedback.jsonl") -> None:
        self._path = Path(path)

    def collect(
        self,
        decision: ReviewDecision,
        confidence: ConfidenceBreakdown,
    ) -> FeedbackRecord:
        """Build a FeedbackRecord from a ReviewDecision and confidence breakdown."""
        was_correct = decision.action.value == "approve"
        return FeedbackRecord(
            ticket_id=decision.ticket_id,
            predicted_confidence=confidence.overall,
            confidence_level=confidence.level.value,
            review_action=decision.action.value,
            was_correct=was_correct,
            original_draft=decision.original_draft_text,
            edited_draft=decision.edited_text,
            timestamp=decision.reviewed_at,
        )

    def persist(self, record: FeedbackRecord) -> None:
        """Append a feedback record to the JSONL file."""
        with self._path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

    def load(self) -> list[FeedbackRecord]:
        """Load all feedback records from the JSONL file."""
        if not self._path.exists():
            return []
        records: list[FeedbackRecord] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(FeedbackRecord.model_validate_json(line))
        return records
