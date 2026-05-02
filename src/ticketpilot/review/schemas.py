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
