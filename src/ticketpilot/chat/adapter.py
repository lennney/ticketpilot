"""Pipeline-to-Chat adapter for TicketPilot AI customer service copilot.

Bridges the pipeline output (TicketOutput + optional DraftGenerationResult)
to the chat UI display format (ChatDisplay). This is a pure transformation
layer — no pipeline execution, no LLM calls, no auto-send.

Boundary: adapter only, no real provider calls in Phase 15.3.
"""

from __future__ import annotations

from ticketpilot.chat.schemas import ChatDisplay, EvidenceDisplayItem
from ticketpilot.drafting.generator import DraftGenerationResult
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import TicketOutput


def evidence_to_display_items(
    evidence_candidates: list[EvidenceCandidate],
    *,
    preview_chars: int = 120,
) -> list[EvidenceDisplayItem]:
    """Map EvidenceCandidate list to EvidenceDisplayItem list for chat UI.

    Args:
        evidence_candidates: List of evidence candidates from pipeline.
        preview_chars: Truncation length for content preview (default 120).

    Returns:
        List of EvidenceDisplayItem ready for ChatDisplay.preserves

        No mutation of input evidence — returns new items only.
    """
    items = []
    for ev in evidence_candidates:
        content_preview: str | None = None
        if ev.content:
            content_preview = ev.content[:preview_chars]
            if len(ev.content) > preview_chars:
                content_preview += "..."

        items.append(
            EvidenceDisplayItem(
                chunk_id=str(ev.chunk_id),
                doc_type=ev.doc_type.value
                if hasattr(ev.doc_type, "value")
                else str(ev.doc_type),
                title=ev.title,
                score=ev.score,
                content_preview=content_preview,
            )
        )
    return items


def ticket_output_to_chat_display(
    ticket_output: TicketOutput,
    draft_result: DraftGenerationResult | None = None,
) -> ChatDisplay:
    """Convert pipeline output to chat UI display format.

    This is a pure transformation — no pipeline execution, no LLM calls.

    Args:
        ticket_output: Complete ticket processing output with evidence.
        draft_result: Optional draft generation result (guard + citation results).

    Returns:
        ChatDisplay ready for Streamlit UI rendering.

    The user_message field is populated from normalized_ticket.text.
    The ai_message field is set from draft_result.draft.draft_text when
    available, or None if no draft has been generated yet.

    No mutation of input ticket_output or draft_result.
    """
    # Map evidence candidates to display items
    evidence_items = evidence_to_display_items(ticket_output.evidence_candidates)

    # Extract risk state
    risk_badge: str | None = None
    risk_flags: list[str] = []
    evidence_exists = len(evidence_items) > 0

    if ticket_output.risk_assessment:
        severity = ticket_output.risk_assessment.severity
        if hasattr(severity, "value"):
            risk_badge = severity.value.upper()
        else:
            risk_badge = str(severity).upper()

        risk_flags = [f.value for f in ticket_output.risk_assessment.flags]

    # Extract draft and guard info
    guard_passed: bool | None = None
    failure_reasons: list[str] = []
    draft_text: str | None = None
    citation_ids: list[str] = []
    escalation_reason: str | None = None

    if draft_result is not None:
        draft: DraftReply = draft_result.draft
        draft_text = draft.draft_text
        citation_ids = list(draft.cited_evidence_ids)

        guard_result = draft_result.guard_result
        guard_passed = guard_result.guard_passed

        failure_reasons = [r.value for r in guard_result.failure_reasons]

        if draft.escalation_reason:
            escalation_reason = draft.escalation_reason
        elif not guard_passed and failure_reasons:
            escalation_reason = f"guard: {', '.join(failure_reasons)}"

    # Determine human_review_required (conservative)
    # Rules:
    # - HIGH severity always True
    # - guard fail always True
    # - no evidence always True
    # - ticket_output.must_human_review True
    # - draft.must_human_review True
    human_review_required = False

    # Severity check
    severity_high = (
        ticket_output.risk_assessment is not None
        and ticket_output.risk_assessment.severity.value == "high"
    )
    if severity_high:
        human_review_required = True

    # Guard failure check
    if guard_passed is False:
        human_review_required = True

    # No evidence check
    if not evidence_exists:
        human_review_required = True
        if escalation_reason is None:
            escalation_reason = "no evidence retrieved"

    # Ticket output pre-existing must_human_review
    ticket_must_hr = (
        ticket_output.risk_assessment.must_human_review
        if ticket_output.risk_assessment
        else False
    )
    if ticket_must_hr:
        human_review_required = True

    # Draft pre-existing must_human_review
    if draft_result is not None and draft_result.draft.must_human_review:
        human_review_required = True

    # Set ai_message from draft
    ai_message: str | None = None
    if draft_result is not None:
        ai_message = draft_result.draft.draft_text

    return ChatDisplay(
        user_message=ticket_output.normalized_ticket.text,
        ai_message=ai_message,
        risk_badge=risk_badge,
        risk_flags=risk_flags,
        evidence_panel=evidence_items,
        draft_text=draft_text,
        guard_passed=guard_passed,
        failure_reasons=failure_reasons,
        human_review_required=human_review_required,
        escalation_reason=escalation_reason,
        citation_ids=citation_ids,
    )


def chat_display_to_context_metadata(display: ChatDisplay) -> dict:
    """Convert ChatDisplay to metadata consumed by update_context_from_message().

    Returns a metadata dict with the keys that update_context_from_message()
    reads: issue_type, risk_flags, severity, evidence_ids, citation_ids,
    guard_passed, human_review_required, handoff_reason.

    Phase 15.3 does not perform natural language parsing — order ID extraction
    is deferred to a future phase.

    Args:
        display: ChatDisplay to convert.

    Returns:
        Metadata dict ready for ChatMessage.metadata.
    """
    evidence_ids = [item.chunk_id for item in display.evidence_panel]

    metadata: dict = {
        "risk_flags": list(display.risk_flags),
        "severity": display.risk_badge,
        "evidence_ids": evidence_ids,
        "citation_ids": list(display.citation_ids),
        "human_review_required": display.human_review_required,
    }

    if display.guard_passed is not None:
        metadata["guard_passed"] = display.guard_passed

    if display.escalation_reason:
        metadata["handoff_reason"] = display.escalation_reason

    return metadata
