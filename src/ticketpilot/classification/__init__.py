"""Intent classification module."""

from ticketpilot.classification.classifier import IntentClassifier
from ticketpilot.classification.rules import INTENT_RULES

__all__ = ["IntentClassifier", "INTENT_RULES"]
