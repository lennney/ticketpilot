"""Intent classifier for ticket text."""

import re
from datetime import datetime, timezone, timezone

from ticketpilot.schema.ticket import ClassificationResult, IntentClass
from ticketpilot.classification.rules import INTENT_RULES
from ticketpilot.config import (
    CONFIDENCE_HIGH,
    CONFIDENCE_KEYWORD_1CHAR,
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

        # Phase 2: First-match-wins keyword matching
        matched_intent = IntentClass.OTHER
        match_count = 0
        found_keyword_in_other = False
        matched_keyword_len = 0

        for rule in self.rules:
            if rule.intent == IntentClass.OTHER:
                # Check if text contains strong indicator for OTHER class
                if rule.strong_indicator and rule.strong_indicator in text:
                    found_keyword_in_other = True
                continue
            for keyword in rule.keywords:
                if keyword in text:
                    match_count += 1
                    matched_intent = rule.intent
                    matched_keyword_len = len(keyword)
                    break  # First-match-wins: exit inner loop on first keyword hit
            if match_count > 0:
                break  # First-match-wins: exit outer loop once a rule matches

        if matched_intent == IntentClass.OTHER or match_count == 0:
            if found_keyword_in_other:
                # Partial match: keyword found but in OTHER context
                confidence = CONFIDENCE_MEDIUM
            else:
                confidence = WEAK_CONFIDENCE
        elif matched_keyword_len >= 2:
            # Strong keyword match (2+ characters)
            confidence = CONFIDENCE_HIGH
        else:
            # Weak keyword match (1 character)
            confidence = CONFIDENCE_KEYWORD_1CHAR

        return ClassificationResult(
            intent=matched_intent,
            confidence=confidence,
            classified_at=datetime.now(timezone.utc),
        )
