"""Risk assessor for ticket risk assessment."""

from datetime import datetime, timezone

from ticketpilot.schema.ticket import (
    ClassificationResult,
    NormalizedTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
)
from ticketpilot.risk.rules import RISK_RULES
from ticketpilot.config import CONFIDENCE_MEDIUM as CONFIDENCE_THRESHOLD


class RiskAssessor:
    """Assesses risk flags and severity for tickets."""

    def __init__(self) -> None:
        """Initialize the assessor with risk rules."""
        self.rules = RISK_RULES

    def assess(
        self, normalized_ticket: NormalizedTicket, classification: ClassificationResult
    ) -> RiskAssessment:
        """
        Assess risk for a normalized ticket.

        Args:
            normalized_ticket: Normalized ticket with extracted entities
            classification: Classification result

        Returns:
            RiskAssessment with flags and severity
        """
        flags: set[RiskFlag] = set()

        # Check keyword-based risk flags
        text = normalized_ticket.text
        for rule in self.rules:
            for keyword in rule.keywords:
                if keyword in text:
                    flags.add(rule.flag)
                    break

        # Check insufficient_evidence flag
        # When ticket has no order number, no product info, or vague description
        # Note: empty text (len=0) should NOT trigger insufficient_evidence
        # because there's no content to evaluate - only low_confidence applies
        if (
            len(normalized_ticket.order_numbers) == 0
            and normalized_ticket.product_info is None
            and len(text) > 0
            and len(text) < 10
        ):
            flags.add(RiskFlag.INSUFFICIENT_EVIDENCE)

        # Check low_confidence flag (per blocking issues: unified threshold 0.7)
        if classification.confidence < CONFIDENCE_THRESHOLD:
            flags.add(RiskFlag.LOW_CONFIDENCE)

        # Calculate severity based on substantive flag count
        # Exclude meta-flags (LOW_CONFIDENCE, INSUFFICIENT_EVIDENCE) from count
        substantive_flags = {
            f
            for f in flags
            if f not in (RiskFlag.LOW_CONFIDENCE, RiskFlag.INSUFFICIENT_EVIDENCE)
        }
        substantive_count = len(substantive_flags)

        # Per spec: 0-1 flags = LOW, 2 flags = MEDIUM, 3+ flags = HIGH
        # Special cases: LEGAL_RISK always implies HIGH severity
        # Single COMPENSATION_RISK or ACCOUNT_SECURITY_RISK implies MEDIUM
        if RiskFlag.LEGAL_RISK in substantive_flags:
            severity = RiskSeverity.HIGH
        elif substantive_count >= 3:
            severity = RiskSeverity.HIGH
        elif substantive_count == 2:
            severity = RiskSeverity.MEDIUM
        elif substantive_count == 1 and (
            RiskFlag.COMPENSATION_RISK in substantive_flags
            or RiskFlag.ACCOUNT_SECURITY_RISK in substantive_flags
        ):
            severity = RiskSeverity.MEDIUM
        else:
            severity = RiskSeverity.LOW

        return RiskAssessment(
            flags=flags,
            severity=severity,
            must_human_review=len(flags) > 0,
            assessed_at=datetime.now(timezone.utc),
        )
