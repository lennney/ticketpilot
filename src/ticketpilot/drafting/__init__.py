"""Evidence-grounded draft reply generation module."""

from ticketpilot.drafting.claim_guard import GuardResult, check_claim_guard
from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.draft_citation_validator import (
    DraftCitationValidationResult,
    validate_draft_citations,
)
from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.generator import DraftGenerationResult, generate_draft as generate_draft_v2
from ticketpilot.drafting.llm_provider import FakeLLMProvider, LLMProvider
from ticketpilot.drafting.pipeline import run_pipeline_with_draft
from ticketpilot.drafting.provider import (
    AbstractDraftProvider,
    FakeDraftProvider,
    NO_EVIDENCE_FALLBACK_TEXT,
)
from ticketpilot.drafting.provider_config import (
    LLMProviderConfig,
    create_llm_provider,
    load_llm_provider_config,
)
from ticketpilot.drafting.schemas import (
    Citation,
    DraftedTicketResult,
    DraftGenerationTrace,
    DraftReply,
)

__all__ = [
    "AbstractDraftProvider",
    "DraftCitationValidationResult",
    "DraftGenerationResult",
    "DraftGenerationTrace",
    "DraftedTicketResult",
    "DraftReply",
    "FakeDraftProvider",
    "FakeLLMProvider",
    "GuardResult",
    "LLMProvider",
    "LLMProviderConfig",
    "Citation",
    "CitationValidator",
    "create_llm_provider",
    "check_claim_guard",
    "generate_draft",
    "generate_draft_v2",
    "load_llm_provider_config",
    "NO_EVIDENCE_FALLBACK_TEXT",
    "run_pipeline_with_draft",
    "validate_draft_citations",
]
