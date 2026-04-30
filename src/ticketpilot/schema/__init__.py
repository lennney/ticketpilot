"""Ticket schema definitions for TicketPilot."""

from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)

__all__ = [
    "EvidenceCandidate",
    "RawTicket",
    "NormalizedTicket",
    "IntentClass",
    "ClassificationResult",
    "RiskFlag",
    "RiskSeverity",
    "RiskAssessment",
    "TicketOutput",
]
