"""Standalone draft generation function composing provider + validator."""

from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.provider import (
    NO_EVIDENCE_FALLBACK_TEXT,
    FakeDraftProvider,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.ticket import TicketOutput


def generate_draft(ticket_output: TicketOutput) -> DraftReply:
    """Generate an evidence-grounded draft reply from a processed ticket.

    Composes FakeDraftProvider and CitationValidator deterministically.
    Does not mutate *ticket_output*.

    Args:
        ticket_output: Complete ticket processing output with evidence.

    Returns:
        DraftReply with citations, confidence, and guard flags.
    """
    provider = FakeDraftProvider()
    validator = CitationValidator()

    try:
        reply = provider.generate(
            evidence_candidates=ticket_output.evidence_candidates,
            risk_assessment=ticket_output.risk_assessment,
            classification=ticket_output.classification,
            normalized_text=ticket_output.normalized_ticket.text,
        )

        reply.ticket_id = ticket_output.ticket_id

        passed, issues = validator.validate(
            text=reply.draft_text,
            citations=reply.citations,
            evidence_candidates=ticket_output.evidence_candidates,
        )

        if not ticket_output.evidence_candidates:
            passed = True
            issues = []

        if not passed:
            reply.unsupported_claims = issues
            reply.must_human_review = True

        return reply

    except Exception:
        return DraftReply(
            ticket_id=ticket_output.ticket_id,
            draft_text=NO_EVIDENCE_FALLBACK_TEXT,
            citations=[],
            evidence_used=[],
            unsupported_claims=["生成回复时发生异常"],
            missing_information=["未找到相关证据"],
            confidence=0.0,
            must_human_review=True,
            fallback_reason="generation_error",
        )
