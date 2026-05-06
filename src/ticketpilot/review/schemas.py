"""Pydantic models for human review decisions."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewAction(str, Enum):
    """Actions a human reviewer can take on a draft reply."""

    APPROVE = "approve"
    EDIT = "edit"
    ESCALATE = "escalate"
    REJECT = "reject"


class ReviewDecision(BaseModel):
    """Audit-oriented record of a human review action.

    Captures a snapshot of the ticket, draft, and decision state at review
    time so the record is self-contained for later analysis.

    Includes optional draft audit fields for evidence-grounded draft
    generation (Phase 11). These fields are None for old records and
    populated by the pipeline integration (Phase 11.6) when available.
    """

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    ticket_id: str
    ticket_text: str
    action: ReviewAction
    edited_text: str | None = None
    decision_reason: str = ""
    original_draft_text: str
    confidence: float = 0.0
    had_unsupported_claims: bool = False
    was_high_risk: bool = False
    intent: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    citations_summary: list[dict] = Field(default_factory=list)
    evidence_used_count: int = 0
    review_trigger_reasons: list[str] = Field(default_factory=list)
    reviewer_label: str = ""
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Draft audit fields (Phase 11, optional for backward compat) ---
    # Provider identity
    provider_name: str | None = Field(default=None, description="LLM provider name (e.g. 'fake')")
    model_name: str | None = Field(default=None, description="Model name used by provider")

    # Citation validation (structural)
    citation_validation_valid: bool | None = Field(
        default=None,
        description="Whether cited_evidence_ids passed structural validation"
    )
    valid_cited_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence chunk IDs that exist in evidence candidates"
    )
    invalid_cited_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence chunk IDs that do not exist in evidence candidates"
    )
    missing_citation_required: bool | None = Field(
        default=None,
        description="Whether draft has substantive content without citations"
    )

    # Claim guard (content-level)
    guard_passed: bool | None = Field(
        default=None,
        description="Whether all claim guard checks passed"
    )
    guard_uncited_claims: bool | None = Field(
        default=None,
        description="Whether draft has substantive content without [chunk_id] citations"
    )
    guard_forbidden_promise: bool | None = Field(
        default=None,
        description="Whether forbidden promise patterns were detected in draft"
    )
    guard_forbidden_details: list[str] = Field(
        default_factory=list,
        description="Specific forbidden pattern labels detected (e.g. 'refund_amount')"
    )
    guard_risk_not_acknowledged: bool | None = Field(
        default=None,
        description="Whether high-risk flags are not acknowledged in draft"
    )

    # Human review propagation
    human_review_forced: bool | None = Field(
        default=None,
        description="Whether human review was forced by validation/guard"
    )
    human_review_reasons: list[str] = Field(
        default_factory=list,
        description="Sorted unique reasons for human review enforcement"
    )
    escalation_reason: str | None = Field(
        default=None,
        description="Why human review was triggered (e.g. 'guard: forbidden_promise')"
    )
