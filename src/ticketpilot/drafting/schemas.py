"""Pydantic models for evidence-grounded draft reply generation."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ticketpilot.config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.ticket import TicketOutput
from ticketpilot.tracing.provenance import ResponseProvenance


class Citation(BaseModel):
    """A single evidence reference used in a draft reply."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    source_table: str
    source_id: UUID
    evidence_excerpt: str = Field(..., max_length=200)
    claim_supported: bool = False


class DraftReply(BaseModel):
    """Generated draft reply with evidence citations and guard flags.

    Fields:
        ticket_id: Ticket identifier.
        draft_text: The generated reply text.
        citations: Evidence citations included in the draft.
        evidence_used: Evidence items actually used in generation.
        unsupported_claims: Claims in the draft that lack evidence backing.
        missing_information: Information gaps identified during generation.
        confidence: Confidence score between 0.0 and 1.0.
        must_human_review: Whether human review is required.
        fallback_reason: Reason for fallback, if any.
        generation_trace: Optional trace data from the generator.
        provider_id: Identifier of the LLM provider that generated this draft.
        escalation_reason: Why human review was triggered (if applicable).
        safety_notes: Safety-related notes from guard checks.
        cited_evidence_ids: Evidence chunk IDs directly cited in the draft text.
    """

    ticket_id: str
    draft_text: str = Field(..., min_length=1)
    citations: list[Citation] = Field(default_factory=list)
    evidence_used: list[Citation] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    must_human_review: bool = False
    fallback_reason: str | None = None
    generation_trace: dict | None = None
    provider_id: str = ""
    escalation_reason: str | None = None
    safety_notes: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    reflection_passed: bool | None = None
    reflection_issues: list[str] = Field(default_factory=list)
    skill_used: str | None = None
    provenance: ResponseProvenance | None = Field(
        default=None,
        description="Full-chain provenance linking claims to source chunks",
    )

    @model_validator(mode="after")
    def _enforce_human_review_triggers(self) -> "DraftReply":
        """Auto-set must_human_review when triggers are present."""
        if self.unsupported_claims:
            self.must_human_review = True
        if self.escalation_reason:
            self.must_human_review = True
        
        # Confidence-based routing (tiered strategy)
        # > CONFIDENCE_HIGH: auto-send (HIGH)
        # CONFIDENCE_MEDIUM to CONFIDENCE_HIGH: auto-send with disclaimer (MEDIUM)
        # CONFIDENCE_LOW to CONFIDENCE_MEDIUM: must human review (LOW)
        # < CONFIDENCE_LOW: escalate to human (CRITICAL)
        # Note: confidence == 0.0 means "not yet evaluated" (default), skip routing.
        if 0 < self.confidence < CONFIDENCE_LOW:
            self.must_human_review = True
            if not self.escalation_reason:
                self.escalation_reason = f"critical_confidence ({self.confidence:.2f})"
        elif 0 < self.confidence < CONFIDENCE_MEDIUM:
            self.must_human_review = True
            if not self.escalation_reason:
                self.escalation_reason = f"low_confidence ({self.confidence:.2f})"
        
        return self

    @model_validator(mode="after")
    def _validate_cited_evidence_ids(self) -> "DraftReply":
        """Reject empty strings in cited_evidence_ids."""
        for eid in self.cited_evidence_ids:
            if not eid:
                msg = "cited_evidence_ids must not contain empty strings"
                raise ValueError(msg)
        return self

    @property
    def text(self) -> str:
        """Alias for draft_text, used by convenience callers."""
        return self.draft_text

    @property
    def confidence_level(self) -> str:
        """Get confidence level category.
        
        Returns:
            'high' if confidence > CONFIDENCE_HIGH (autonomous)
            'medium' if CONFIDENCE_MEDIUM <= confidence <= CONFIDENCE_HIGH (auto-send with disclaimer)
            'low' if CONFIDENCE_LOW <= confidence < CONFIDENCE_MEDIUM (human review)
            'critical' if confidence < CONFIDENCE_LOW (escalate to human)
        """
        if self.confidence >= CONFIDENCE_HIGH:
            return "high"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "medium"
        elif self.confidence >= CONFIDENCE_LOW:
            return "low"
        else:
            return "critical"

    @property
    def routing_decision(self) -> str:
        """Get routing decision based on confidence.
        
        Returns:
            'autonomous' if high confidence
            'auto_send_cautious' if medium confidence
            'human_review' if low confidence
            'human_escalation' if critical confidence
        """
        level = self.confidence_level
        if level == "high":
            return "autonomous"
        elif level == "medium":
            return "auto_send_cautious"
        elif level == "low":
            return "human_review"
        else:
            return "human_escalation"


class DraftedTicketResult(BaseModel):
    """Wrapper combining a processed ticket with its generated draft reply."""

    ticket_output: TicketOutput
    draft_reply: DraftReply


class DraftGenerationTrace(BaseModel):
    """Full trace of the draft generation stage for audit and debugging."""

    ticket_id: str
    evidence_used: list[Citation] = Field(default_factory=list)
    evidence_count: int = 0
    total_evidence_available: int = 0
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    fallback_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
