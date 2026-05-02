"""Optional pipeline entrypoint composing intake-risk pipeline with draft generation."""

from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.schemas import DraftedTicketResult, DraftReply
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket, TicketOutput


def run_pipeline_with_draft(raw_ticket: RawTicket) -> DraftedTicketResult:
    """Run the full intake-risk pipeline then generate an evidence-grounded draft reply.

    This is an explicit optional workflow. It does not change the default
    ``intake_risk_pipeline()`` contract or modify ``TicketOutput``.

    Args:
        raw_ticket: Raw ticket to process.

    Returns:
        DraftedTicketResult with the processed ticket and its generated draft reply.
    """
    ticket_output: TicketOutput = intake_risk_pipeline(raw_ticket)
    draft_reply: DraftReply = generate_draft(ticket_output)
    return DraftedTicketResult(
        ticket_output=ticket_output,
        draft_reply=draft_reply,
    )
