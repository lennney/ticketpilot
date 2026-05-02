"""Evidence-grounded draft reply generation module."""

from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.pipeline import run_pipeline_with_draft
from ticketpilot.drafting.provider import (
    AbstractDraftProvider,
    FakeDraftProvider,
    NO_EVIDENCE_FALLBACK_TEXT,
)
from ticketpilot.drafting.schemas import (
    Citation,
    DraftedTicketResult,
    DraftGenerationTrace,
    DraftReply,
)

__all__ = [
    "AbstractDraftProvider",
    "FakeDraftProvider",
    "CitationValidator",
    "generate_draft",
    "run_pipeline_with_draft",
    "Citation",
    "DraftReply",
    "DraftedTicketResult",
    "DraftGenerationTrace",
    "NO_EVIDENCE_FALLBACK_TEXT",
]
