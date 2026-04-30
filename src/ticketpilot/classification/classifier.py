"""Intent classifier for ticket text."""

from datetime import datetime

from ticketpilot.schema.ticket import ClassificationResult, IntentClass
from ticketpilot.classification.rules import INTENT_RULES

# Unified confidence threshold (per blocking issues)
CONFIDENCE_THRESHOLD = 0.7
STRONG_CONFIDENCE = 0.8
WEAK_CONFIDENCE = 0.5


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
                classified_at=datetime.utcnow(),
            )

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
            classified_at=datetime.utcnow(),
        )
