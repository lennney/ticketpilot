"""Pydantic models for evidence-grounded draft reply generation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.ticket import TicketOutput


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

    @model_validator(mode="after")
    def _enforce_human_review_triggers(self) -> "DraftReply":
        """Auto-set must_human_review when triggers are present."""
        if self.unsupported_claims:
            self.must_human_review = True
        if self.escalation_reason:
            self.must_human_review = True
        
        # Confidence-based routing
        # > 0.8: autonomous (no human review)
        # 0.6-0.8: suggest human review
        # < 0.6: must human review
        if self.confidence < 0.6:
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
    def confidence_level(self) -> str:
        """Get confidence level category.
        
        Returns:
            'high' if confidence > 0.8 (autonomous)
            'medium' if 0.6 <= confidence <= 0.8 (suggest review)
            'low' if confidence < 0.6 (must review)
        """
        if self.confidence > 0.8:
            return "high"
        elif self.confidence >= 0.6:
            return "medium"
        else:
            return "low"

    @property
    def routing_decision(self) -> str:
        """Get routing decision based on confidence.
        
        Returns:
            'autonomous' if high confidence
            'suggest_review' if medium confidence
            'human_review' if low confidence
        """
        level = self.confidence_level
        if level == "high":
            return "autonomous"
        elif level == "medium":
            return "suggest_review"
        else:
            return "human_review"


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
