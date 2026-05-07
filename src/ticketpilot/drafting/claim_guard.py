"""Deterministic claim guard for evidence-grounded draft replies.

Provides rule-based checks for citation coverage, forbidden promises,
evidence sufficiency, and risk-aware escalation acknowledgment.
All checks are deterministic — no network calls, no LLM API, no
semantic analysis. Same inputs always produce same outputs.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from ticketpilot.drafting._safe_fallback import is_safe_fallback
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import RiskAssessment, RiskFlag


class GuardFailureType(str, Enum):
    """Granular taxonomy of guard failure types.

    Each type maps to a specific failure mode detected by the claim guard.
    Used for per-failure-type metrics, failure interpretation, and
    targeted improvement strategies. See Phase 14.2 design doc.
    """

    UNSUPPORTED_POLICY_CLAIM = "UNSUPPORTED_POLICY_CLAIM"
    FORBIDDEN_PROMISE = "FORBIDDEN_PROMISE"
    MISSING_RISK_ESCALATION = "MISSING_RISK_ESCALATION"
    SAFE_ESCALATION_STATEMENT = "SAFE_ESCALATION_STATEMENT"
    MANUAL_REVIEW_ACKNOWLEDGEMENT = "MANUAL_REVIEW_ACKNOWLEDGEMENT"
    EVIDENCE_INSUFFICIENT_FALLBACK = "EVIDENCE_INSUFFICIENT_FALLBACK"
    AMBIGUOUS_GUARD_CASE = "AMBIGUOUS_GUARD_CASE"
    # Canonical name is UNCITED_SUBSTANTIVE_CLAIM (correct spelling).
    # Serialized value stays "UNCITED_SUBSTANTIVE_CLAIM" for persistence stability.
    UNCITED_SUBSTANTIVE_CLAIM = "UNCITED_SUBSTANTIVE_CLAIM"


class GuardResult(BaseModel):
    """Result of claim guard checks applied to a draft reply.

    Attributes:
        citation_coverage: Proportion of [chunk_id] references in draft_text
            that correspond to valid EvidenceCandidate IDs (0.0–1.0).
        has_uncited_claims: Whether the draft contains substantive content
            without any [chunk_id] citations (greetings and safe-fallback
            messages are exempt).
        has_forbidden_promise: Whether forbidden promise patterns were detected.
        forbidden_promise_details: Specific forbidden pattern labels matched.
        evidence_sufficiency: "sufficient", "partial", or "insufficient".
        risk_flags_respected: Whether all high-risk flags are acknowledged
            in the draft via escalation language.
        guard_passed: Overall guard result — True when all checks pass.
        failure_reasons: Granular list of GuardFailureType reasons for
            guard failure. Empty when guard_passed is True. failure_reasons
            is failure-only — safe fallback signals are deferred to future
            guard_signals/reporting phases.
    """

    citation_coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    has_uncited_claims: bool = False
    has_forbidden_promise: bool = False
    forbidden_promise_details: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = "sufficient"
    risk_flags_respected: bool = True
    guard_passed: bool = True
    failure_reasons: list[GuardFailureType] = Field(default_factory=list)


# Deterministic forbidden-promise regex patterns: (regex, label)
_FORBIDDEN_PROMISE_PATTERNS: list[tuple[str, str]] = [
    (r"退款\d+元", "refund_amount"),
    (r"赔偿\d+元", "compensation_amount"),
    (r"我们一定会起诉", "legal_action_guarantee"),
    (r"已为您修改密码", "account_changed"),
    (r"账号已冻结", "account_frozen"),
    (r"\d+天内解决", "resolution_timeline"),
    (r"保证\d+天", "guaranteed_timeline"),
    (r"承认责任", "liability_admission"),
    (r"我方过错", "liability_admission"),
]

# High-risk flags that require escalation acknowledgment in the draft
_HIGH_RISK_FLAGS: set[RiskFlag] = {
    RiskFlag.LEGAL_RISK,
    RiskFlag.COMPENSATION_RISK,
    RiskFlag.PRIVACY_RISK,
    RiskFlag.ACCOUNT_SECURITY_RISK,
}

# Escalation acknowledgment patterns that satisfy risk-aware checking
_ESCALATION_PATTERNS: list[str] = [
    "转人工",
    "人工处理",
    "升级处理",
    "human review",
    "escalated",
]

# Greeting prefixes exempt from uncited-claim detection
_GREETING_PATTERNS: list[str] = [
    "尊敬的客户",
    "尊敬的",
    "亲爱的客户",
    "亲爱的",
    "您好",
    "你好",
]


def _extract_chunk_ids(text: str) -> list[str]:
    """Extract all [UUID] chunk_id references from text.

    Returns lowercased UUID strings for consistent matching
    against EvidenceCandidate.chunk_id values.
    """
    pattern = (
        r"\[([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12})\]"
    )
    return [uid.lower() for uid in re.findall(pattern, text)]


def _has_substantive_content(text: str) -> bool:
    """Check if text contains substantive content beyond greetings.

    Strips common greeting patterns and checks for remaining
    meaningful Chinese text. A text with only a greeting and
    closing is not substantive.
    """
    cleaned = text
    for g in _GREETING_PATTERNS:
        cleaned = cleaned.replace(g, "")
    cleaned = cleaned.strip()
    # After removing greetings, check if meaningful Chinese text remains.
    if len(cleaned) <= 3:
        return False
    # Use code-point range for CJK Unified Ideographs (U+4E00..U+9FFF)
    return any(c >= "一" and c <= "鿿" for c in cleaned)


# Backward-compatibility alias so existing imports (e.g., tests) continue to work.
_is_safe_fallback = is_safe_fallback


def _check_forbidden_promises(draft_text: str) -> tuple[bool, list[str]]:
    """Scan draft text for forbidden promise patterns.

    Returns (has_forbidden, sorted_unique_labels).
    """
    labels: list[str] = []
    for pattern, label in _FORBIDDEN_PROMISE_PATTERNS:
        if re.search(pattern, draft_text):
            labels.append(label)
    return bool(labels), sorted(set(labels))


def _assess_evidence_sufficiency(
    evidence_candidates: list[EvidenceCandidate] | None,
) -> str:
    """Assess whether evidence sufficiently covers the request.

    Deterministic rule: evidence exists -> "sufficient",
    no evidence -> "insufficient".
    """
    if not evidence_candidates:
        return "insufficient"
    return "sufficient"


def _check_risk_acknowledgment(
    draft_text: str,
    risk_assessment: RiskAssessment | None,
) -> bool:
    """Check that high-risk flags are acknowledged with escalation language.

    Returns True if no high-risk flags exist, no assessment provided,
    or all high-risk flags are acknowledged in the draft.
    """
    if risk_assessment is None:
        return True
    high_risk = risk_assessment.flags & _HIGH_RISK_FLAGS
    if not high_risk:
        return True
    draft_lower = draft_text.lower()
    return any(p in draft_lower for p in _ESCALATION_PATTERNS)


def check_claim_guard(
    draft: DraftReply,
    evidence_candidates: list[EvidenceCandidate] | None = None,
    risk_assessment: RiskAssessment | None = None,
) -> GuardResult:
    """Run all claim guard checks on a draft reply.

    Applies the following checks in order:
    1. Citation coverage — validates [chunk_id] references in draft_text
       against evidence candidates.
    2. Uncited claim detection — flags substantive content without citations.
    3. Forbidden promise detection — scans for refund, compensation, legal,
       account, timeline, and liability patterns.
    4. Evidence sufficiency — assesses whether evidence is available.
    5. Risk-aware check — verifies high-risk flags are acknowledged.

    Args:
        draft: The draft reply to check.
        evidence_candidates: Evidence candidates retrieved for this ticket.
        risk_assessment: Risk assessment for this ticket.

    Returns:
        GuardResult with per-check results and overall guard_passed.
    """
    evidence = evidence_candidates or []
    draft_text = draft.draft_text

    # 1. Citation coverage — valid [chunk_id] references in draft_text
    chunk_ids = _extract_chunk_ids(draft_text)
    if chunk_ids:
        valid_ids = {str(ev.chunk_id).lower() for ev in evidence}
        valid_count = sum(1 for cid in chunk_ids if cid in valid_ids)
        citation_coverage = valid_count / len(chunk_ids)
    else:
        citation_coverage = 1.0

    # 2. Uncited claim detection
    has_uncited = False
    if not is_safe_fallback(draft_text):
        if not chunk_ids and _has_substantive_content(draft_text):
            has_uncited = True

    # 3. Forbidden promise detection
    has_promise, promise_details = _check_forbidden_promises(draft_text)

    # 4. Evidence sufficiency
    sufficiency = _assess_evidence_sufficiency(evidence)

    # 5. Risk-aware check
    risk_respected = _check_risk_acknowledgment(draft_text, risk_assessment)

    # 6. Overall guard result
    guard_passed = bool(
        citation_coverage == 1.0
        and not has_uncited
        and not has_promise
        and risk_respected
    )

    # 7. Build failure_reasons taxonomy (failure-only)
    # failure_reasons is empty when guard_passed=True.
    # Safe fallback signals are deferred to future guard_signals/reporting phases.
    failure_reasons: list[GuardFailureType] = []
    if not guard_passed:
        if citation_coverage < 1.0:
            failure_reasons.append(GuardFailureType.UNSUPPORTED_POLICY_CLAIM)
        if has_uncited:
            failure_reasons.append(GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM)
        if has_promise:
            failure_reasons.append(GuardFailureType.FORBIDDEN_PROMISE)
        if not risk_respected:
            failure_reasons.append(GuardFailureType.MISSING_RISK_ESCALATION)
        if not failure_reasons:
            failure_reasons.append(GuardFailureType.AMBIGUOUS_GUARD_CASE)

    return GuardResult(
        citation_coverage=citation_coverage,
        has_uncited_claims=has_uncited,
        has_forbidden_promise=has_promise,
        forbidden_promise_details=promise_details,
        evidence_sufficiency=sufficiency,
        risk_flags_respected=risk_respected,
        guard_passed=guard_passed,
        failure_reasons=failure_reasons,
    )
