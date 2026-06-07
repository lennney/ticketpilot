"""Pydantic models for ticket data structures."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.schema.evidence import EvidenceCandidate


class IntentClass(str, Enum):
    """Intent classification categories for tickets."""

    REFUND = "refund"
    RETURN_EXCHANGE = "return_exchange"
    ACCOUNT_ISSUE = "account_issue"
    TECHNICAL_ISSUE = "technical_issue"
    PRODUCT_CONSULTING = "product_consulting"
    LOGISTICS = "logistics"
    COMPLAINT = "complaint"
    OTHER = "other"


class RiskFlag(str, Enum):
    """Risk flags for ticket risk assessment."""

    COMPLAINT_RISK = "complaint_risk"
    COMPENSATION_RISK = "compensation_risk"
    LEGAL_RISK = "legal_risk"
    PRIVACY_RISK = "privacy_risk"
    ACCOUNT_SECURITY_RISK = "account_security_risk"
    POLICY_CONFLICT = "policy_conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LOW_CONFIDENCE = "low_confidence"


class RiskSeverity(str, Enum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RawTicket(BaseModel):
    """Raw ticket input before processing."""

    original_text: str
    submitted_at: datetime
    customer_id: str | None = None


class NormalizedTicket(BaseModel):
    """Normalized ticket after cleaning and entity extraction."""

    text: str
    language: str
    order_numbers: list[str] = Field(default_factory=list)
    product_info: str | None = None
    amount: float | None = None
    cleaned_at: datetime


class ClassificationResult(BaseModel):
    """Result of intent classification."""

    intent: IntentClass
    confidence: float
    classified_at: datetime


class RiskAssessment(BaseModel):
    """Risk assessment result with flags and severity."""

    flags: set[RiskFlag]
    severity: RiskSeverity
    must_human_review: bool
    assessed_at: datetime


class Ticket(BaseModel):
    """Convenience ticket model for direct agent invocation."""

    ticket_id: str
    text: str
    intent: IntentClass = IntentClass.OTHER
    confidence: float = 0.0
    risk_flags: list[RiskFlag] = Field(default_factory=list)


class TicketOutput(BaseModel):
    """Complete ticket processing output combining all stages."""

    ticket_id: str
    raw_ticket: RawTicket
    normalized_ticket: NormalizedTicket
    classification: ClassificationResult
    risk_assessment: RiskAssessment
    output_at: datetime
    evidence_candidates: list[EvidenceCandidate] = Field(default_factory=list)
    retrieval_trace: RetrievalTrace | None = None
