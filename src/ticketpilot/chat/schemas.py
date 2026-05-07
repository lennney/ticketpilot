"""Chat support schemas for TicketPilot AI customer service copilot."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# ReviewDecisionDisplay — lightweight review decision for chat session
# ---------------------------------------------------------------------------


class ReviewDecisionDisplay(BaseModel):
    """Lightweight review decision for chat session display.

    A simplified representation of ReviewDecision (review/schemas.py)
    for passing between Streamlit pages via session state.
    """

    action: str  # approve, edit, escalate, reject
    edited_text: str | None = None
    decision_reason: str = ""
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        valid_actions = {"approve", "edit", "escalate", "reject"}
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v


class ChatState(str, Enum):
    """Chat session state machine states."""

    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    DRAFT_READY = "DRAFT_READY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REVIEWED = "REVIEWED"


class ChatRole(str, Enum):
    """Role of a chat message sender."""

    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single message in a chat session.

    Attributes:
        role: Who sent the message (user, AI, or system).
        text: The message content.
        timestamp: When the message was sent.
        metadata: Optional metadata dict. Can include:
            - turn_id: the turn number of this message
            - detected_order_id: order ID extracted by pipeline
            - issue_type: intent classification result
            - risk_flags: list of risk flag names
            - severity: risk severity level
            - evidence_ids: list of retrieved evidence chunk IDs
            - citation_ids: list of cited evidence chunk IDs
            - guard_passed: whether the draft passed guard checks
            - human_review_required: whether human review is needed
            - handoff_reason: why the ticket was routed to human review
    """

    role: ChatRole
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Reject empty or whitespace-only text."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("text cannot be empty or whitespace-only")
        return stripped


class ChatContext(BaseModel):
    """Lightweight context for multi-turn customer service conversation.

    Tracks the current order, issue type, risk state, and evidence across
    multiple turns. This enables follow-up questions like "that order"
    or "what about shipping cost" without losing context.

    Attributes:
        current_issue_type: Most recent issue type (e.g., "refund", "complaint").
        current_order_id: Most recent order ID (e.g., "12345").
        current_product_name: Product name if mentioned.
        latest_risk_flags: Risk flags from most recent turn.
        latest_severity: Risk severity from most recent turn.
        latest_evidence_ids: Evidence chunk IDs retrieved in most recent turn.
        latest_citation_ids: Cited evidence chunk IDs in most recent draft.
        latest_guard_passed: Guard pass/fail from most recent turn.
        human_review_required: True if any turn triggered human review.
        handoff_reason: Why human review was triggered.
        turn_count: Total number of user messages in this session.
    """

    current_issue_type: str | None = None
    current_order_id: str | None = None
    current_product_name: str | None = None
    latest_risk_flags: list[str] = Field(default_factory=list)
    latest_severity: str | None = None
    latest_evidence_ids: list[str] = Field(default_factory=list)
    latest_citation_ids: list[str] = Field(default_factory=list)
    latest_guard_passed: bool | None = None
    human_review_required: bool = False
    handoff_reason: str | None = None
    turn_count: int = 0


class EvidenceDisplayItem(BaseModel):
    """An evidence item displayed in the chat UI evidence panel.

    Attributes:
        chunk_id: The evidence chunk identifier.
        title: Optional title or label for the evidence.
        doc_type: The document type (FAQ, Policy, Case, etc.).
        score: Optional relevance score from retrieval.
        content_preview: Optional truncated content preview.
    """

    chunk_id: str
    title: str | None = None
    doc_type: str
    score: float | None = None
    content_preview: str | None = None

    @field_validator("chunk_id")
    @classmethod
    def chunk_id_not_empty(cls, v: str) -> str:
        """Reject empty chunk_id."""
        if not v.strip():
            raise ValueError("chunk_id cannot be empty")
        return v.strip()

    @field_validator("doc_type")
    @classmethod
    def doc_type_not_empty(cls, v: str) -> str:
        """Reject empty doc_type."""
        if not v.strip():
            raise ValueError("doc_type cannot be empty")
        return v.strip()


class ChatDisplay(BaseModel):
    """Formatted display data for the chat UI panels.

    Aggregates all information needed to render:
    - risk status panel
    - evidence panel
    - draft panel
    - human review status
    """

    user_message: str = ""
    ai_message: str | None = None
    risk_badge: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    evidence_panel: list[EvidenceDisplayItem] = Field(default_factory=list)
    draft_text: str | None = None
    guard_passed: bool | None = None
    failure_reasons: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    escalation_reason: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    context_summary: str | None = None


class ChatSession(BaseModel):
    """A complete chat session with messages, state, and context.

    Supports multi-turn conversations with lightweight context tracking.
    Does not include database persistence or pipeline integration.

    Attributes:
        session_id: Unique identifier for this session.
        messages: All messages in the session (user, AI, system).
        state: Current session state machine state.
        context: Lightweight context for follow-up question support.
        display: Cached display data for UI panels.
        human_review_required: Whether any turn has triggered human review.
        pending_review_session: Snapshot sent to reviewer (not persisted).
        last_review_decision: Most recent decision from reviewer.
    """

    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    state: ChatState = ChatState.IDLE
    context: ChatContext = Field(default_factory=ChatContext)
    display: ChatDisplay | None = None
    human_review_required: bool = False

    # --- Phase 15.6: Human review handoff ---
    pending_review_session: "ChatSession | None" = None
    last_review_decision: ReviewDecisionDisplay | None = None

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        """Reject empty session_id."""
        if not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def append_message(session: ChatSession, message: ChatMessage) -> ChatSession:
    """Return a new ChatSession with message appended and turn_count updated.

    This is a pure function — the original session is not mutated.

    Args:
        session: The current chat session.
        message: The message to append.

    Returns:
        A new ChatSession with the message added and turn_count incremented
        if the message is from a user.
    """
    new_session = ChatSession(
        session_id=session.session_id,
        messages=session.messages + [message],
        state=session.state,
        context=ChatContext(
            current_issue_type=session.context.current_issue_type,
            current_order_id=session.context.current_order_id,
            current_product_name=session.context.current_product_name,
            latest_risk_flags=list(session.context.latest_risk_flags),
            latest_severity=session.context.latest_severity,
            latest_evidence_ids=list(session.context.latest_evidence_ids),
            latest_citation_ids=list(session.context.latest_citation_ids),
            latest_guard_passed=session.context.latest_guard_passed,
            human_review_required=session.context.human_review_required,
            handoff_reason=session.context.handoff_reason,
            turn_count=session.context.turn_count,
        ),
        display=session.display,
        human_review_required=session.human_review_required,
    )

    if message.role == ChatRole.USER:
        new_session.context.turn_count += 1

    return new_session


def update_context_from_message(
    context: ChatContext,
    message: ChatMessage,
) -> ChatContext:
    """Update lightweight context from message metadata only.

    Phase 15.2 does not parse natural language. It only reads
    metadata keys if present:
    - detected_order_id -> current_order_id
    - issue_type -> current_issue_type
    - risk_flags -> latest_risk_flags (append/merge, not replace)
    - severity -> latest_severity
    - evidence_ids -> latest_evidence_ids
    - citation_ids -> latest_citation_ids
    - guard_passed -> latest_guard_passed
    - human_review_required -> human_review_required
    - handoff_reason -> handoff_reason

    Once human_review_required is True, it stays True (can only be
    cleared by a reviewer action in a future phase).

    Args:
        context: The current chat context.
        message: A message whose metadata should update the context.

    Returns:
        A new ChatContext with updated fields from message metadata.
    """
    meta = message.metadata

    new_order = meta.get("detected_order_id")
    new_issue = meta.get("issue_type")
    new_flags = meta.get("risk_flags", [])
    new_severity = meta.get("severity")
    new_evidence = meta.get("evidence_ids", [])
    new_citations = meta.get("citation_ids", [])
    new_guard_passed = meta.get("guard_passed")
    new_hr_required = meta.get("human_review_required")
    new_handoff = meta.get("handoff_reason")

    return ChatContext(
        current_order_id=new_order if new_order else context.current_order_id,
        current_issue_type=new_issue if new_issue else context.current_issue_type,
        current_product_name=context.current_product_name,
        latest_risk_flags=list(set(context.latest_risk_flags + new_flags)),
        latest_severity=new_severity if new_severity else context.latest_severity,
        latest_evidence_ids=new_evidence if new_evidence else context.latest_evidence_ids,
        latest_citation_ids=new_citations if new_citations else context.latest_citation_ids,
        latest_guard_passed=new_guard_passed
        if new_guard_passed is not None
        else context.latest_guard_passed,
        human_review_required=context.human_review_required or bool(new_hr_required),
        handoff_reason=new_handoff if new_handoff else context.handoff_reason,
        turn_count=context.turn_count,
    )
