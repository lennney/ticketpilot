"""JSONL-based persistence for review decisions."""

import json
from pathlib import Path

from ticketpilot.review.schemas import ReviewDecision


class ReviewStore:
    """Append-only JSONL persistence for ReviewDecision records."""

    def __init__(self, path: str = "reviews.jsonl"):
        self.path = Path(path)

    def save(self, decision: ReviewDecision) -> None:
        """Append a single review decision to the JSONL file.

        Creates the parent directory if it does not exist.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(decision.model_dump_json() + "\n")

    def load_all(self) -> list[ReviewDecision]:
        """Load all review decisions from the JSONL file.

        Returns an empty list if the file does not exist or is empty.
        Invalid JSON lines are silently skipped.
        """
        if not self.path.exists():
            return []

        decisions: list[ReviewDecision] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    decisions.append(ReviewDecision.model_validate(data))
                except (json.JSONDecodeError, ValueError):
                    continue
        return decisions

    def count(self) -> int:
        """Return the number of stored review decisions."""
        return len(self.load_all())
