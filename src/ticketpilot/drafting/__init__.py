"""Evidence-grounded draft reply generation module."""

from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.provider import (
    AbstractDraftProvider,
    FakeDraftProvider,
    NO_EVIDENCE_FALLBACK_TEXT,
)
from ticketpilot.drafting.schemas import (
    Citation,
    DraftGenerationTrace,
    DraftReply,
)

__all__ = [
    "AbstractDraftProvider",
    "FakeDraftProvider",
    "CitationValidator",
    "generate_draft",
    "Citation",
    "DraftReply",
    "DraftGenerationTrace",
    "NO_EVIDENCE_FALLBACK_TEXT",
]
