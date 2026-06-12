"""Intent classifier for ticket text."""

import re
from datetime import datetime, timezone

from ticketpilot.schema.ticket import ClassificationResult, IntentClass
from ticketpilot.classification.rules import INTENT_RULES
from ticketpilot.config import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_STRONG_INDICATOR,
    WEAK_CONFIDENCE,
)


class IntentClassifier:
    """Classifies ticket intent using keyword matching."""

    def __init__(self) -> None:
        """Initialize the classifier with intent rules."""
        self.rules = INTENT_RULES

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify ticket intent from text.

        Args:
            text: Normalized ticket text

        Returns:
            ClassificationResult with intent and confidence
        """
        if not text:
            return ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=WEAK_CONFIDENCE,
                classified_at=datetime.now(timezone.utc),
            )

        # Phase 1: Check for strong indicators (complaint escalation, etc.)
        for rule in self.rules:
            if rule.intent == IntentClass.OTHER:
                continue
            if rule.strong_indicator:
                if re.search(rule.strong_indicator, text):
                    return ClassificationResult(
                        intent=rule.intent,
                        confidence=CONFIDENCE_STRONG_INDICATOR,
                        classified_at=datetime.now(timezone.utc),
                    )

        # Phase 2: Score-based intent classification
        scores = self._score_intents(text)

        if not scores:
            return ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=WEAK_CONFIDENCE,
                classified_at=datetime.now(timezone.utc),
            )

        # Sort by score desc, then rule priority (position in INTENT_RULES) for ties
        priority_order = {rule.intent.value: i for i, rule in enumerate(self.rules)}
        ranked = sorted(
            scores.items(),
            key=lambda x: (-x[1], priority_order.get(x[0], 999)),
        )
        top_intent_str, top_score = ranked[0]

        if top_score <= 0:
            return ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=WEAK_CONFIDENCE,
                classified_at=datetime.now(timezone.utc),
            )

        matched_intent = IntentClass(top_intent_str)
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = (top_score - second_score) / top_score

        if margin >= 0.5:
            confidence = CONFIDENCE_HIGH
        elif margin >= 0.25:
            confidence = CONFIDENCE_MEDIUM
        else:
            confidence = WEAK_CONFIDENCE

        return ClassificationResult(
            intent=matched_intent,
            confidence=confidence,
            classified_at=datetime.now(timezone.utc),
        )

    def _score_intents(self, text: str) -> dict[str, float]:
        """Score each intent (except OTHER) by keyword matches with exclusion penalties.

        Each keyword match adds ``len(keyword)`` to the intent's score.
        Each exclusion match subtracts ``len(excl)`` from the intent's score.
        Final score is floored at ``0.0`` (never negative).

        Returns dict mapping intent value strings (e.g. ``\"refund\"``) to their
        cumulative scores. OTHER is excluded (always score 0).
        """
        scores: dict[str, float] = {}
        for rule in self.rules:
            if rule.intent == IntentClass.OTHER:
                continue
            score = 0.0
            for keyword in rule.keywords:
                if keyword in text:
                    score += float(len(keyword))
            if rule.exclusions:
                for excl in rule.exclusions:
                    if excl in text:
                        score -= float(len(excl))
            scores[rule.intent.value] = max(0.0, score)
        return scores
