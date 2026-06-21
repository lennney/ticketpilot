"""Draft-level citation validation for DraftReply objects.

Validates cited_evidence_ids against provided evidence candidates,
detects missing citations for substantive content, and checks for
duplicate/invalid citation IDs. This is a deterministic, local-only
validator — no network calls, no LLM API, no semantic analysis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ticketpilot.drafting._safe_fallback import (
    SAFE_FALLBACK_PATTERNS,
    is_safe_fallback,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate

# Backward compatibility: re-export SAFE_FALLBACK_PATTERNS under the old name.
_SAFE_FALLBACK_PATTERNS: list[str] = SAFE_FALLBACK_PATTERNS


class DraftCitationValidationResult(BaseModel):
    """Structured result of citation validation for a DraftReply.

    Attributes:
        is_valid: Whether all citation checks passed.
        valid_cited_evidence_ids: Cited IDs that exist in evidence candidates.
        invalid_cited_evidence_ids: Cited IDs not found in evidence candidates.
        duplicate_cited_evidence_ids: Duplicate entries in cited_evidence_ids.
        missing_citation_required: Whether the draft has substantive content
            but no citations (heuristic, not semantic).
        available_evidence_ids: All valid evidence chunk IDs as strings.
        errors: Validation errors that require attention.
        warnings: Non-blocking validation notes.
        must_human_review: Whether human review is required based on
            validation failure, DraftReply state, or unsupported claims.
    """

    is_valid: bool = True
    valid_cited_evidence_ids: list[str] = Field(default_factory=list)
    invalid_cited_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_cited_evidence_ids: list[str] = Field(default_factory=list)
    missing_citation_required: bool = False
    available_evidence_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    must_human_review: bool = False


_DEFAULT_RESULT = DraftCitationValidationResult()


def validate_draft_citations(
    draft: DraftReply,
    evidence_candidates: list[EvidenceCandidate] | None = None,
) -> DraftCitationValidationResult:
    """Validate a DraftReply's cited_evidence_ids against evidence candidates.

    Performs the following checks in order:
    1. Evidence ID existence — every cited ID must appear in evidence.
    2. Duplicate detection — repeated cited IDs are reported as warnings.
    3. Empty-evidence handling — no evidence + cited IDs = all invalid.
    4. Missing citation heuristic — substantive text without citations.
    5. Unsupported claims propagation — non-empty unsupported_claims
       forces must_human_review.
    6. Human review propagation — never downgrades must_human_review.

    Args:
        draft: The DraftReply to validate.
        evidence_candidates: Evidence candidates retrieved for this ticket.
            May be None or empty.

    Returns:
        A DraftCitationValidationResult with per-check results.
    """
    evidence = evidence_candidates or []
    result = DraftCitationValidationResult()

    # Build set of valid evidence chunk IDs as strings
    available = sorted({str(ev.chunk_id) for ev in evidence})
    result.available_evidence_ids = available

    cited = draft.cited_evidence_ids

    # --- Check 1: Evidence ID existence ---
    if not evidence and cited:
        # No evidence but citations exist — all are invalid
        result.invalid_cited_evidence_ids = sorted(set(cited))
        result.errors.append(
            "No evidence candidates available, but cited_evidence_ids "
            f"contains {len(cited)} ID(s): all are invalid."
        )
        result.is_valid = False
        result.must_human_review = True
    elif evidence and cited:
        valid_set = {str(ev.chunk_id) for ev in evidence}
        for eid in cited:
            if eid in valid_set:
                result.valid_cited_evidence_ids.append(eid)
            else:
                result.invalid_cited_evidence_ids.append(eid)

        result.valid_cited_evidence_ids = sorted(result.valid_cited_evidence_ids)
        result.invalid_cited_evidence_ids = sorted(result.invalid_cited_evidence_ids)

        if result.invalid_cited_evidence_ids:
            ids_str = ", ".join(result.invalid_cited_evidence_ids)
            result.errors.append(
                f"Invalid cited evidence IDs not found in candidates: {ids_str}"
            )
            result.is_valid = False
            result.must_human_review = True
    elif not evidence and not cited:
        # No evidence, no citations — valid structurally, but warn
        result.warnings.append("No evidence candidates available.")
        # Leave is_valid True (structural pass; semantic check happens later)

    # --- Check 2: Duplicate detection ---
    seen: set[str] = set()
    dups: list[str] = []
    for eid in cited:
        if eid in seen:
            dups.append(eid)
        seen.add(eid)
    if dups:
        result.duplicate_cited_evidence_ids = sorted(set(dups))
        ids_str = ", ".join(result.duplicate_cited_evidence_ids)
        result.warnings.append(f"Duplicate cited evidence IDs detected: {ids_str}")
        # Duplicates are warnings, not errors — don't set is_valid=False

    # --- Check 3: Missing citation heuristic ---
    is_fallback = is_safe_fallback(draft.draft_text)
    has_citations = bool(cited) or bool(draft.citations)

    if not is_fallback and not has_citations:
        result.missing_citation_required = True
        result.warnings.append(
            "Draft text contains substantive content but cited_evidence_ids "
            "is empty; citations may be missing."
        )

    if is_fallback and not has_citations:
        # Safe fallback doesn't need citations
        pass

    # --- Check 4: Unsupported claims ---
    if draft.unsupported_claims:
        result.errors.append(
            f"Draft contains {len(draft.unsupported_claims)} unsupported "
            "claim(s); human review required."
        )
        result.must_human_review = True
        result.is_valid = False

    # --- Check 5: Human review propagation ---
    if draft.must_human_review:
        result.must_human_review = True

    return result
