"""Central confidence thresholds for TicketPilot.

Unified thresholds used across classifier, risk assessor, routing,
quality checks, and escalation engine.
"""

# Strong indicator match (e.g. "12315投诉") — near-certain
CONFIDENCE_STRONG_INDICATOR = 0.9

# High confidence: autonomous response (auto-send)
CONFIDENCE_HIGH = 0.8

# Keyword match with 1 character — weaker signal
CONFIDENCE_KEYWORD_1CHAR = 0.7

# Medium confidence: auto-send with disclaimer / suggest review
CONFIDENCE_MEDIUM = 0.6

# Low confidence: must have human review
CONFIDENCE_LOW = 0.4

# Legacy aliases for backward compatibility
CONFIDENCE_THRESHOLD = CONFIDENCE_MEDIUM
STRONG_CONFIDENCE = CONFIDENCE_HIGH
WEAK_CONFIDENCE = 0.5
