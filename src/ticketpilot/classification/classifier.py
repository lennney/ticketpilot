"""Intent classifier for ticket text."""

import re
from datetime import datetime, timezone, timezone

from ticketpilot.schema.ticket import ClassificationResult, IntentClass
from ticketpilot.classification.rules import INTENT_RULES
from ticketpilot.config import CONFIDENCE_THRESHOLD, STRONG_CONFIDENCE, WEAK_CONFIDENCE


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
                        confidence=STRONG_CONFIDENCE,
                        classified_at=datetime.now(timezone.utc),
                    )

        # Phase 2: First-match-wins keyword matching
        matched_intent = IntentClass.OTHER
        match_count = 0
        has_strong_match = False

        for rule in self.rules:
            if rule.intent == IntentClass.OTHER:
                # Check if text contains strong indicator for OTHER class
                if rule.strong_indicator and rule.strong_indicator in text:
                    has_strong_match = True
                continue
            for keyword in rule.keywords:
                if keyword in text:
                    match_count += 1
                    matched_intent = rule.intent
                    # Strong match if keyword is 2+ characters
                    if len(keyword) >= 2:
                        has_strong_match = True
                    break  # First-match-wins: exit inner loop on first keyword hit
            if match_count > 0:
                break  # First-match-wins: exit outer loop once a rule matches

        if matched_intent == IntentClass.OTHER or match_count == 0:
            # For OTHER intent, confidence depends on whether strong indicator was found
            confidence = STRONG_CONFIDENCE if has_strong_match else WEAK_CONFIDENCE
        elif has_strong_match:
            confidence = STRONG_CONFIDENCE
        else:
            confidence = WEAK_CONFIDENCE

        return ClassificationResult(
            intent=matched_intent,
            confidence=confidence,
            classified_at=datetime.now(timezone.utc),
        )
