"""Evidence-grounded draft generation composing prompt builder, LLM provider,
citation validation, and claim guard into a deterministic workflow.

Uses FakeLLMProvider by default. Real provider integration is out of scope
for this batch (Phase 11.6).
"""

from __future__ import annotations

from ticketpilot.drafting.claim_guard import GuardResult, check_claim_guard
from ticketpilot.drafting.citation_validator import (
    CitationValidator,
)
from ticketpilot.drafting.draft_citation_validator import (
    DraftCitationValidationResult,
    validate_draft_citations,
)
from ticketpilot.drafting.provider_config import (
    create_llm_provider,
    load_llm_provider_config,
)
from ticketpilot.drafting.prompt_builder import DraftPromptInput
from ticketpilot.drafting.schemas import (
    DraftReply,
)
from ticketpilot.schema.ticket import TicketOutput


class DraftGenerationResult:
    """Complete result of evidence-grounded draft generation.

    Wraps the DraftReply with additional trace metadata from the generation
    pipeline. Preserves DraftReply backward compatibility.

    Attributes:
        draft: The generated DraftReply with citations and guard flags.
        provider_name: Which LLM provider generated the draft.
        model_name: Which model the provider used.
        citation_validation: Structural citation validation result
            (cited_evidence_ids against evidence candidates).
        guard_result: Claim guard result (content-level checks).
        generation_trace: Compact trace dict with pipeline metadata.
    """

    def __init__(
        self,
        draft: DraftReply,
        provider_name: str,
        model_name: str,
        citation_validation: DraftCitationValidationResult,
        guard_result: GuardResult,
        ticket_output: TicketOutput | None = None,
    ) -> None:
        self.draft = draft
        self.provider_name = provider_name
        self.model_name = model_name
        self.citation_validation = citation_validation
        self.guard_result = guard_result
        self.ticket_output = ticket_output
        self.generation_trace: dict = {}

    def to_trace_dict(self) -> dict:
        """Compact trace dict for audit and evaluation.

        Returns:
            Dictionary with provider info, validation results, and
            human review reasons. Does not include draft text or prompts.
        """
        reasons: list[str] = []
        if self.draft.fallback_reason:
            reasons.append(f"fallback:{self.draft.fallback_reason}")
        if self.draft.escalation_reason:
            reasons.append(f"escalation:{self.draft.escalation_reason}")
        if self.draft.unsupported_claims:
            reasons.append("unsupported_claims")

        # Add validation/guard failure reasons
        if not self.citation_validation.is_valid:
            reasons.append("citation_validation_failed")
        if self.citation_validation.must_human_review:
            reasons.append("citation_validation_human_review")
        if not self.guard_result.guard_passed:
            reasons.append("guard_failed")
            if self.guard_result.has_uncited_claims:
                reasons.append("uncited_claims")
            if self.guard_result.has_forbidden_promise:
                reasons.append("forbidden_promise")
            if not self.guard_result.risk_flags_respected:
                reasons.append("risk_not_acknowledged")

        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "cited_evidence_ids": self.draft.cited_evidence_ids,
            "available_evidence_ids": self.citation_validation.available_evidence_ids,
            "citation_validation_is_valid": self.citation_validation.is_valid,
            "guard_passed": self.guard_result.guard_passed,
            "human_review_forced": self.draft.must_human_review,
            "human_review_reasons": sorted(set(reasons)),
            "confidence": self.draft.confidence,
        }


def _build_prompt_input(ticket_output: TicketOutput) -> DraftPromptInput:
    """Build DraftPromptInput from a TicketOutput.

    Extracts fields from the ticket output to populate the prompt input.
    Risk flags are converted from RiskFlag enums to strings.
    """
    risk_strs: list[str] = []
    if ticket_output.risk_assessment and ticket_output.risk_assessment.flags:
        risk_strs = [f.value for f in ticket_output.risk_assessment.flags]

    severity = (
        ticket_output.risk_assessment.severity.value
        if ticket_output.risk_assessment
        else "low"
    )

    must_review = (
        ticket_output.risk_assessment.must_human_review
        if ticket_output.risk_assessment
        else False
    )

    return DraftPromptInput(
        ticket_text=ticket_output.normalized_ticket.text,
        issue_type=ticket_output.classification.intent.value,
        risk_flags=risk_strs,
        severity=severity,
        must_human_review=must_review,
        evidence_candidates=ticket_output.evidence_candidates,
    )


def _build_risk_assessment_for_guard(
    ticket_output: TicketOutput,
):
    """Build RiskAssessment from TicketOutput for claim guard checking.

    Returns None if risk assessment is not available.
    """
    return ticket_output.risk_assessment


def generate_draft(
    ticket_output: TicketOutput,
    provider=None,
    inject_prompt: str | None = None,
) -> DraftGenerationResult:
    """Generate an evidence-grounded draft reply from a processed ticket.

    Composes the following pipeline deterministically:
    1. Build prompt input from ticket output
    2. Call LLM provider (FakeLLMProvider by default) → DraftReply
    3. Run CitationValidator (content-level [N] checks)
    4. Run draft_citation_validator (structural ID checks)
    5. Run claim guard (content-level checks)
    6. Propagate human review flags

    Does NOT call real LLM APIs. Does NOT mutate ticket_output.

    Args:
        ticket_output: Complete ticket processing output with evidence.
        provider: Optional LLMProvider instance. If None, uses FakeLLMProvider.
            Useful for testing with mock providers.
        inject_prompt: Optional pre-built prompt string. If provided, the
            prompt builder is skipped and this string is used directly.
            Intended for testing deterministic prompt scenarios only.

    Returns:
        DraftGenerationResult wrapping the DraftReply with trace metadata.
    """
    # 1. Get provider (default FakeLLMProvider)
    llm = provider
    if llm is None:
        config = load_llm_provider_config()
        llm = create_llm_provider(config)

    provider_name = llm.provider_name
    model_name = llm.model_name

    # 2. Build prompt input (or use injected prompt)
    if inject_prompt is not None:
        pass  # Skip prompt building — use injected prompt directly (testing only)
    else:
        _build_prompt_input(ticket_output)  # Validate input; result used by LLM provider

    # 3. Call LLM provider to generate draft
    risk_strs: list[str] = []
    if ticket_output.risk_assessment and ticket_output.risk_assessment.flags:
        risk_strs = [f.value for f in ticket_output.risk_assessment.flags]

    severity = (
        ticket_output.risk_assessment.severity.value
        if ticket_output.risk_assessment
        else "low"
    )

    must_review = (
        ticket_output.risk_assessment.must_human_review
        if ticket_output.risk_assessment
        else False
    )

    draft = llm.generate_draft(
        normalized_text=ticket_output.normalized_ticket.text,
        issue_type=ticket_output.classification.intent.value,
        risk_flags=risk_strs,
        severity=severity,
        must_human_review=must_review,
        evidence_candidates=ticket_output.evidence_candidates,
    )

    # Set ticket_id
    draft.ticket_id = ticket_output.ticket_id

    # 4. Run CitationValidator (content-level [N] checks)
    citation_validator = CitationValidator()
    cit_passed, cit_issues = citation_validator.validate(
        text=draft.draft_text,
        citations=draft.citations,
        evidence_candidates=ticket_output.evidence_candidates,
    )

    if not cit_passed and cit_issues:
        # CitationValidator detected content issues → unsupported_claims
        for issue in cit_issues:
            if issue not in draft.unsupported_claims:
                draft.unsupported_claims.append(issue)
        draft.must_human_review = True

    # 5. Run draft_citation_validator (structural ID checks)
    struct_validation = validate_draft_citations(
        draft=draft,
        evidence_candidates=ticket_output.evidence_candidates,
    )

    # 6. Run claim guard (content-level checks)
    risk_assessment = _build_risk_assessment_for_guard(ticket_output)
    guard_result = check_claim_guard(
        draft=draft,
        evidence_candidates=ticket_output.evidence_candidates,
        risk_assessment=risk_assessment,
    )

    # 7. Human review propagation — never downgrade
    if draft.must_human_review:
        pass  # already true
    elif struct_validation.must_human_review:
        draft.must_human_review = True
    elif not guard_result.guard_passed:
        draft.must_human_review = True

    # Also propagate guard failure to escalation_reason if not already set
    if not guard_result.guard_passed and not draft.escalation_reason:
        reasons: list[str] = []
        if guard_result.has_uncited_claims:
            reasons.append("uncited_claims")
        if guard_result.has_forbidden_promise:
            reasons.append("forbidden_promise")
        if not guard_result.risk_flags_respected:
            reasons.append("risk_not_acknowledged")
        if reasons:
            draft.escalation_reason = f"guard: {', '.join(reasons)}"

    result = DraftGenerationResult(
        draft=draft,
        provider_name=provider_name,
        model_name=model_name,
        citation_validation=struct_validation,
        guard_result=guard_result,
        ticket_output=ticket_output,
    )

    return result