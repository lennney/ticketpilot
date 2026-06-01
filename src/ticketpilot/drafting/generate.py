"""Standalone draft generation function composing provider + validator.

Supports FakeDraftProvider (default), OpenAICompatibleProvider (DeepSeek, etc.),
and DraftAgent (agentic loop with tool use).
Reads TICKETPILOT_LLM_PROVIDER and TICKETPILOT_AGENT_MODE from .env.local.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.provider import (
    NO_EVIDENCE_FALLBACK_TEXT,
    FakeDraftProvider,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.ticket import TicketOutput

logger = logging.getLogger(__name__)

# Load .env.local
_env_local = Path(__file__).resolve().parent.parent.parent / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local)


def _get_llm_provider():
    """Create LLM provider based on env config. Returns None for fake mode."""
    provider_type = os.environ.get("TICKETPILOT_LLM_PROVIDER", "fake")

    if provider_type == "fake":
        return None

    if provider_type == "openai_compatible":
        from ticketpilot.drafting.llm_provider import OpenAICompatibleProvider

        base_url = os.environ.get("TICKETPILOT_LLM_BASE_URL", "https://api.deepseek.com")
        api_key = os.environ.get("TICKETPILOT_LLM_API_KEY", "")
        model = os.environ.get("TICKETPILOT_LLM_MODEL", "deepseek-chat")
        timeout = int(os.environ.get("TICKETPILOT_LLM_TIMEOUT_SECONDS", "30"))
        max_tokens = int(os.environ.get("TICKETPILOT_LLM_MAX_TOKENS", "512"))
        temperature = float(os.environ.get("TICKETPILOT_LLM_TEMPERATURE", "0.3"))

        if not api_key:
            logger.warning("TICKETPILOT_LLM_API_KEY not set, falling back to FakeDraftProvider")
            return None

        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    logger.warning("Unknown TICKETPILOT_LLM_PROVIDER=%s, falling back to fake", provider_type)
    return None


def _use_agent_mode() -> bool:
    """Check if agentic mode is enabled via env var."""
    return os.environ.get("TICKETPILOT_AGENT_MODE", "").lower() in ("true", "1", "yes")


def _run_agent_draft(ticket_output: TicketOutput) -> DraftReply | None:
    """Try generating draft via DraftAgent. Returns None on failure."""
    from ticketpilot.drafting.draft_agent import DraftAgent

    api_key = os.environ.get("TICKETPILOT_LLM_API_KEY", "")
    if not api_key:
        logger.warning(
            "TICKETPILOT_AGENT_MODE enabled but TICKETPILOT_LLM_API_KEY not set, "
            "falling back to standard provider"
        )
        return None

    try:
        agent = DraftAgent()
        reply = agent.generate_draft(
            normalized_text=ticket_output.normalized_ticket.text,
            issue_type=ticket_output.classification.intent.value,
            risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
            severity=ticket_output.risk_assessment.severity.value,
            must_human_review=ticket_output.risk_assessment.must_human_review,
            evidence_candidates=ticket_output.evidence_candidates,
        )
        reply.ticket_id = ticket_output.ticket_id

        # Validate citations
        validator = CitationValidator()
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

    except Exception as e:
        logger.error("DraftAgent failed: %s, falling back to standard provider", e)
        return None


def generate_draft(ticket_output: TicketOutput) -> DraftReply:
    """Generate an evidence-grounded draft reply from a processed ticket.

    Selection priority:
    1. If TICKETPILOT_AGENT_MODE=true and API key is set: use DraftAgent
    2. If TICKETPILOT_LLM_PROVIDER=openai_compatible: use OpenAICompatibleProvider
    3. Otherwise: use deterministic FakeDraftProvider

    Args:
        ticket_output: Complete ticket processing output with evidence.

    Returns:
        DraftReply with citations, confidence, and guard flags.
    """

    # Agent mode takes priority when enabled
    if _use_agent_mode():
        agent_reply = _run_agent_draft(ticket_output)
        if agent_reply is not None:
            return agent_reply
        # Fall through to standard provider if agent fails

    llm_provider = _get_llm_provider()

    if llm_provider is not None:
        # Real LLM path — uses OpenAICompatibleProvider
        try:
            reply = llm_provider.generate_draft(
                normalized_text=ticket_output.normalized_ticket.text,
                issue_type=ticket_output.classification.intent.value,
                risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
                severity=ticket_output.risk_assessment.severity.value,
                must_human_review=ticket_output.risk_assessment.must_human_review,
                evidence_candidates=ticket_output.evidence_candidates,
            )
            reply.ticket_id = ticket_output.ticket_id

            # Still validate citations
            validator = CitationValidator()
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

        except Exception as e:
            logger.error("LLM draft generation failed: %s, falling back to fake", e)

    # Fake/deterministic path
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
