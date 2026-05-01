"""Pydantic models for evidence-grounded draft reply generation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ticketpilot.retrieval.schema.knowledge import DocType


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
    """Generated draft reply with evidence citations and guard flags."""

    ticket_id: str
    draft_text: str
    citations: list[Citation] = Field(default_factory=list)
    evidence_used: list[Citation] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    must_human_review: bool = False
    fallback_reason: str | None = None
    generation_trace: dict | None = None


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
