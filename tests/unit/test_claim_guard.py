"""Unit tests for claim guard — citation coverage, forbidden promises,
evidence sufficiency, risk-aware check, and overall guard result."""

from __future__ import annotations

import uuid
from datetime import datetime

from ticketpilot.drafting.claim_guard import (
    GuardFailureType,
    GuardResult,
    _assess_evidence_sufficiency,
    _check_forbidden_promises,
    _check_risk_acknowledgment,
    _extract_chunk_ids,
    _has_substantive_content,
    _is_safe_fallback,
    check_claim_guard,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import RiskAssessment, RiskFlag, RiskSeverity
from ticketpilot.retrieval.schema.knowledge import DocType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ev(
    chunk_id: uuid.UUID | None = None,
    content: str = "根据平台政策，符合退货条件的商品可在签收后7天内申请退货。",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=chunk_id or uuid.uuid4(),
        doc_id=uuid.uuid4(),
        doc_type=DocType.POLICY,
        source_id=uuid.uuid4(),
        source_table="knowledge_records",
        content=content,
        score=0.95,
        rank=1,
        title="退货政策",
    )


def _draft(text: str, **kwargs) -> DraftReply:
    return DraftReply(
        ticket_id="TICKET-001",
        draft_text=text,
        **kwargs,
    )


def _risk(
    flags: set[RiskFlag] | None = None, must_review: bool = False
) -> RiskAssessment:
    return RiskAssessment(
        flags=flags or set(),
        severity=RiskSeverity.MEDIUM,
        must_human_review=must_review,
        assessed_at=datetime.utcnow(),
    )


_CHUNK_A = uuid.uuid4()
_CHUNK_B = uuid.uuid4()
_CHUNK_C = uuid.uuid4()

# ---------------------------------------------------------------------------
# GuardResult schema defaults
# ---------------------------------------------------------------------------


class TestGuardFailureType:
    """GuardFailureType enum has all 8 taxonomy values."""

    def test_all_eight_types_exist(self) -> None:
        """All 8 taxonomy types exist; canonical name is UNCITED_SUBSTANTIVE_CLAIM."""
        types = {m.name for m in GuardFailureType}
        assert "UNSUPPORTED_POLICY_CLAIM" in types
        assert "FORBIDDEN_PROMISE" in types
        assert "MISSING_RISK_ESCALATION" in types
        assert "SAFE_ESCALATION_STATEMENT" in types
        assert "MANUAL_REVIEW_ACKNOWLEDGEMENT" in types
        assert "EVIDENCE_INSUFFICIENT_FALLBACK" in types
        assert "AMBIGUOUS_GUARD_CASE" in types
        assert "UNCITED_SUBSTANTIVE_CLAIM" in types
        # Serialized value still "UNCITED_SUBSTANTIVE_CLAIM" (stable for persistence)
        assert (
            GuardFailureType("UNCITED_SUBSTANTIVE_CLAIM").name
            == "UNCITED_SUBSTANTIVE_CLAIM"
        )
        assert (
            GuardFailureType("UNCITED_SUBSTANTIVE_CLAIM").value
            == "UNCITED_SUBSTANTIVE_CLAIM"
        )


class TestGuardResultDefaults:
    """GuardResult default field values."""

    def test_defaults(self) -> None:
        result = GuardResult()
        assert result.citation_coverage == 1.0
        assert result.has_uncited_claims is False
        assert result.has_forbidden_promise is False
        assert result.forbidden_promise_details == []
        assert result.evidence_sufficiency == "sufficient"
        assert result.risk_flags_respected is True
        assert result.guard_passed is True
        assert result.failure_reasons == []

    def test_guard_passed_false_when_checks_fail(self) -> None:
        result = GuardResult(
            citation_coverage=0.5,
            has_uncited_claims=True,
            has_forbidden_promise=True,
            risk_flags_respected=False,
            guard_passed=False,
        )
        assert result.guard_passed is False


class TestFailureReasonsTaxonomy:
    """failure_reasons taxonomy populated by check_claim_guard."""

    def test_clean_draft_empty_failure_reasons(self) -> None:
        """Fully correct draft: guard_passed=True, failure_reasons=[]."""
        ev = _ev(chunk_id=_CHUNK_A)
        text = f"尊敬的客户，根据政策[{str(_CHUNK_A)}]，可以退货。"
        draft = _draft(text)
        result = check_claim_guard(draft, [ev])
        assert result.guard_passed is True
        assert result.failure_reasons == []

    def test_uncited_claim_maps_to_uncited_substantive_claim(self) -> None:
        """has_uncited_claims=True -> UNCITED_SUBSTANTIVE_CLAIM."""
        text = "尊敬的客户，关于您反馈的退货问题，根据平台政策可以为您办理。"
        draft = _draft(text)
        result = check_claim_guard(draft, [_ev()])
        assert result.guard_passed is False
        assert result.has_uncited_claims is True
        assert GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM in result.failure_reasons

    def test_forbidden_promise_maps_to_forbidden_promise(self) -> None:
        """has_forbidden_promise=True -> FORBIDDEN_PROMISE."""
        text = "我们会在3天内解决您的问题。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is False
        assert result.has_forbidden_promise is True
        assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons

    def test_missing_risk_escalation_maps_correctly(self) -> None:
        """risk_flags_respected=False -> MISSING_RISK_ESCALATION."""
        text = "尊敬的用户，我们会尽快处理您的问题。"
        draft = _draft(text)
        ra = _risk(flags={RiskFlag.LEGAL_RISK})
        result = check_claim_guard(draft, [], ra)
        assert result.guard_passed is False
        assert result.risk_flags_respected is False
        assert GuardFailureType.MISSING_RISK_ESCALATION in result.failure_reasons

    def test_multiple_failures_all_in_failure_reasons(self) -> None:
        """Multiple failures each map to correct taxonomy type."""
        text = "尊敬的用户，退款500元。"
        draft = _draft(text)
        ra = _risk(flags={RiskFlag.LEGAL_RISK})
        result = check_claim_guard(draft, [], ra)
        assert result.guard_passed is False
        assert result.has_forbidden_promise is True
        assert result.has_uncited_claims is True
        assert result.risk_flags_respected is False
        assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons
        assert GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM in result.failure_reasons
        assert GuardFailureType.MISSING_RISK_ESCALATION in result.failure_reasons

    def test_safe_fallback_guard_passed_empty_failure_reasons(self) -> None:
        """Safe-fallback: guard_passed=True, failure_reasons=[].
        safe fallback signal is deferred to future phase
        (guard_signals / reporting); failure_reasons is failure-only."""
        text = "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is True
        assert result.failure_reasons == []

    def test_greeting_only_empty_failure_reasons(self) -> None:
        """Greeting-only draft: guard_passed=True, failure_reasons=[]."""
        draft = _draft("尊敬的客户，您好！")
        result = check_claim_guard(draft, [])
        assert result.guard_passed is True
        assert result.failure_reasons == []

    def test_partial_citation_maps_to_unsupported_policy(self) -> None:
        """citation_coverage < 1.0 (partial citation missing) -> UNSUPPORTED_POLICY_CLAIM."""
        ev = _ev(chunk_id=_CHUNK_A)
        text = f"政策A[{str(_CHUNK_A)}]和政策B[{str(_CHUNK_B)}]。"
        draft = _draft(text)
        result = check_claim_guard(draft, [ev])
        assert result.guard_passed is False
        assert result.citation_coverage == 0.5
        # Partial citation coverage maps to UNSUPPORTED_POLICY_CLAIM
        assert GuardFailureType.UNSUPPORTED_POLICY_CLAIM in result.failure_reasons
        # Not the other named check failures
        assert GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM not in result.failure_reasons
        assert GuardFailureType.FORBIDDEN_PROMISE not in result.failure_reasons
        assert GuardFailureType.MISSING_RISK_ESCALATION not in result.failure_reasons

    def test_safe_escalation_statement_included_when_present(self) -> None:
        """SAFE_ESCALATION_STATEMENT added when safe escalation language detected and guard fails."""
        text = "尊敬的用户，退款500元。此问题需要人工审核。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is False
        assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons
        assert GuardFailureType.SAFE_ESCALATION_STATEMENT in result.failure_reasons

    def test_manual_review_acknowledgement_included_when_present(self) -> None:
        """MANUAL_REVIEW_ACKNOWLEDGEMENT added when manual review acknowledged and guard fails."""
        text = "尊敬的用户，退款500元。需人工审核。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is False
        assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons
        assert GuardFailureType.MANUAL_REVIEW_ACKNOWLEDGEMENT in result.failure_reasons

    def test_safe_escalation_not_included_when_not_present(self) -> None:
        """SAFE_ESCALATION_STATEMENT absent when guard fails without escalation language."""
        text = "尊敬的用户，退款500元。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is False
        assert GuardFailureType.SAFE_ESCALATION_STATEMENT not in result.failure_reasons

    def test_manual_review_not_included_when_not_present(self) -> None:
        """MANUAL_REVIEW_ACKNOWLEDGEMENT absent when guard fails without review acknowledgement."""
        text = "尊敬的用户，退款500元。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is False
        assert (
            GuardFailureType.MANUAL_REVIEW_ACKNOWLEDGEMENT not in result.failure_reasons
        )


# ---------------------------------------------------------------------------
# _extract_chunk_ids
# ---------------------------------------------------------------------------


class TestExtractChunkIds:
    """Extracting [UUID] references from draft text."""

    def test_empty_text_returns_empty(self) -> None:
        assert _extract_chunk_ids("") == []

    def test_no_brackets_returns_empty(self) -> None:
        text = "尊敬的客户，您好。"
        assert _extract_chunk_ids(text) == []

    def test_single_uuid_extracted(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        text = f"根据条款[{uid}]，可以办理。"
        result = _extract_chunk_ids(text)
        assert result == [uid]

    def test_multiple_uuids_extracted(self) -> None:
        a = "550e8400-e29b-41d4-a716-446655440000"
        b = "660e8400-e29b-41d4-a716-446655440001"
        text = f"引用[{a}]和[{b}]。"
        result = _extract_chunk_ids(text)
        assert result == [a, b]

    def test_invalid_uuid_in_brackets_skipped(self) -> None:
        text = "引用[not-a-uuid]和[also-not]"
        assert _extract_chunk_ids(text) == []

    def test_mixed_valid_and_invalid(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        text = f"有效[{uid}]和无效[bad-id]"
        result = _extract_chunk_ids(text)
        assert result == [uid]

    def test_uuid_normalized_to_lowercase(self) -> None:
        uid = "550E8400-E29B-41D4-A716-446655440000"
        text = f"[{uid}]"
        result = _extract_chunk_ids(text)
        assert result == [uid.lower()]

    def test_no_false_positive_on_regular_brackets(self) -> None:
        text = "请参考[1]和[2]"
        assert _extract_chunk_ids(text) == []


# ---------------------------------------------------------------------------
# _is_safe_fallback
# ---------------------------------------------------------------------------


class TestIsSafeFallback:
    """Safe-fallback detection for uncited-claim exemption."""

    def test_empty_text_is_fallback(self) -> None:
        assert _is_safe_fallback("") is True

    def test_exact_safe_fallback_text(self) -> None:
        text = "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert _is_safe_fallback(text) is True

    def test_partial_safe_pattern(self) -> None:
        assert _is_safe_fallback("建议转人工处理") is True
        assert _is_safe_fallback("证据不足") is True
        assert _is_safe_fallback("无法确认具体政策条款") is True

    def test_substantive_text_not_fallback(self) -> None:
        text = "根据平台政策[550e8400-e29b-41d4-a716-446655440000]，可以退货。"
        assert _is_safe_fallback(text) is False


# ---------------------------------------------------------------------------
# _has_substantive_content
# ---------------------------------------------------------------------------


class TestHasSubstantiveContent:
    """Subtantive content detection beyond greetings."""

    def test_greeting_only_not_substantive(self) -> None:
        assert _has_substantive_content("尊敬的客户，您好！") is False

    def test_greeting_with_short_text_not_substantive(self) -> None:
        # Over threshold: >10 chars after greeting stripped
        assert _has_substantive_content("您好") is False

    def test_substantive_chinese_text(self) -> None:
        text = "尊敬的客户，关于您反馈的退货问题，根据平台政策可为您办理。"
        assert _has_substantive_content(text) is True

    def test_empty_text_not_substantive(self) -> None:
        assert _has_substantive_content("") is False

    def test_only_whitespace_not_substantive(self) -> None:
        assert _has_substantive_content("   ") is False


# ---------------------------------------------------------------------------
# _check_forbidden_promises
# ---------------------------------------------------------------------------


class TestForbiddenPromises:
    """Forbidden promise pattern detection."""

    def test_refund_amount_detected(self) -> None:
        has, details = _check_forbidden_promises("可以为您退款500元。")
        assert has is True
        assert "refund_amount" in details

    def test_compensation_amount_detected(self) -> None:
        has, details = _check_forbidden_promises("我们将赔偿200元。")
        assert has is True
        assert "compensation_amount" in details

    def test_legal_action_guarantee_detected(self) -> None:
        has, details = _check_forbidden_promises("我们一定会起诉对方。")
        assert has is True
        assert "legal_action_guarantee" in details

    def test_account_changed_detected(self) -> None:
        has, details = _check_forbidden_promises("已为您修改密码，请妥善保管。")
        assert has is True
        assert "account_changed" in details

    def test_account_frozen_detected(self) -> None:
        has, details = _check_forbidden_promises("账号已冻结，请联系客服。")
        assert has is True
        assert "account_frozen" in details

    def test_resolution_timeline_detected(self) -> None:
        has, details = _check_forbidden_promises("我们将在3天内解决您的问题。")
        assert has is True
        assert "resolution_timeline" in details

    def test_guaranteed_timeline_detected(self) -> None:
        has, details = _check_forbidden_promises("保证7天到账。")
        assert has is True
        assert "guaranteed_timeline" in details

    def test_liability_admission_detected(self) -> None:
        has, details = _check_forbidden_promises("本次问题承认责任在于我方。")
        assert has is True
        assert "liability_admission" in details

    def test_wo_fault_liability_detected(self) -> None:
        has, details = _check_forbidden_promises("经核实，确认是我方过错。")
        assert has is True
        assert "liability_admission" in details

    def test_clean_draft_passes(self) -> None:
        text = "尊敬的客户，关于您的问题，建议您联系人工客服处理。"
        has, details = _check_forbidden_promises(text)
        assert has is False
        assert details == []

    def test_multiple_promises_all_reported(self) -> None:
        text = "我们赔偿200元，并会在3天内解决。"
        has, details = _check_forbidden_promises(text)
        assert has is True
        assert "compensation_amount" in details
        assert "resolution_timeline" in details
        # Also check that numbers don't trigger without valid prefixes
        assert "refund_amount" not in details


# ---------------------------------------------------------------------------
# _assess_evidence_sufficiency
# ---------------------------------------------------------------------------


class TestEvidenceSufficiency:
    """Evidence sufficiency assessment."""

    def test_no_evidence_is_insufficient(self) -> None:
        assert _assess_evidence_sufficiency(None) == "insufficient"

    def test_empty_list_is_insufficient(self) -> None:
        assert _assess_evidence_sufficiency([]) == "insufficient"

    def test_with_evidence_is_sufficient(self) -> None:
        assert _assess_evidence_sufficiency([_ev()]) == "sufficient"

    def test_multiple_evidence_is_sufficient(self) -> None:
        evs = [_ev(), _ev(), _ev()]
        assert _assess_evidence_sufficiency(evs) == "sufficient"


# ---------------------------------------------------------------------------
# _check_risk_acknowledgment
# ---------------------------------------------------------------------------


class TestRiskAcknowledgment:
    """Risk-aware check for high-risk flag acknowledgment."""

    def test_no_risk_assessment_passes(self) -> None:
        assert _check_risk_acknowledgment("任何文本", None) is True

    def test_no_risk_flags_passes(self) -> None:
        ra = _risk(flags=set())
        assert _check_risk_acknowledgment("任何文本", ra) is True

    def test_low_risk_flags_passes(self) -> None:
        ra = _risk(flags={RiskFlag.COMPLAINT_RISK, RiskFlag.POLICY_CONFLICT})
        assert _check_risk_acknowledgment("任何文本", ra) is True

    def test_legal_risk_acknowledged(self) -> None:
        ra = _risk(flags={RiskFlag.LEGAL_RISK})
        text = "此案件涉及法律问题，已转人工处理。"
        assert _check_risk_acknowledgment(text, ra) is True

    def test_legal_risk_not_acknowledged_fails(self) -> None:
        ra = _risk(flags={RiskFlag.LEGAL_RISK})
        text = "尊敬的用户，我们会尽快处理您的问题。"
        assert _check_risk_acknowledgment(text, ra) is False

    def test_compensation_risk_acknowledged(self) -> None:
        ra = _risk(flags={RiskFlag.COMPENSATION_RISK})
        text = "此案件涉及赔偿，已升级处理。"
        assert _check_risk_acknowledgment(text, ra) is True

    def test_privacy_risk_acknowledged(self) -> None:
        ra = _risk(flags={RiskFlag.PRIVACY_RISK})
        text = "涉及隐私问题，建议转人工处理。"
        assert _check_risk_acknowledgment(text, ra) is True

    def test_account_security_risk_acknowledged(self) -> None:
        ra = _risk(flags={RiskFlag.ACCOUNT_SECURITY_RISK})
        text = "账号安全问题已转人工处理。"
        assert _check_risk_acknowledgment(text, ra) is True

    def test_multiple_high_risks_all_acknowledged(self) -> None:
        ra = _risk(flags={RiskFlag.LEGAL_RISK, RiskFlag.COMPENSATION_RISK})
        text = "此案件涉及法律和赔偿问题，已转人工处理。"
        assert _check_risk_acknowledgment(text, ra) is True

    def test_escalated_english_pattern(self) -> None:
        ra = _risk(flags={RiskFlag.LEGAL_RISK})
        text = "This case has been escalated for human review."
        assert _check_risk_acknowledgment(text, ra) is True


# ---------------------------------------------------------------------------
# check_claim_guard — integrated checks
# ---------------------------------------------------------------------------


class TestCheckClaimGuard:
    """Integration-level tests for check_claim_guard()."""

    def test_clean_draft_passes(self) -> None:
        """Fully cited draft with evidence and no risks passes."""
        ev = _ev(chunk_id=_CHUNK_A)
        text = f"尊敬的客户，根据政策[{str(_CHUNK_A)}]，可以退货。"
        draft = _draft(text)
        result = check_claim_guard(draft, [ev])
        assert result.guard_passed is True
        assert result.citation_coverage == 1.0
        assert result.has_uncited_claims is False
        assert result.has_forbidden_promise is False
        assert result.risk_flags_respected is True

    def test_greeting_only_passes(self) -> None:
        """Text with only a greeting passes all checks."""
        draft = _draft("尊敬的客户，您好！")
        result = check_claim_guard(draft, [])
        assert result.guard_passed is True
        assert result.citation_coverage == 1.0
        assert result.has_uncited_claims is False

    def test_safe_fallback_passes(self) -> None:
        """Safe-fallback text passes even without evidence."""
        text = "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.guard_passed is True
        assert result.has_uncited_claims is False

    def test_uncited_claim_fails_guard(self) -> None:
        """Substantive content without citations fails guard."""
        text = "尊敬的客户，关于您反馈的退货问题，根据平台政策可以为您办理退货手续。"
        draft = _draft(text)
        result = check_claim_guard(draft, [_ev()])
        assert result.has_uncited_claims is True
        assert result.guard_passed is False

    def test_forbidden_promise_fails_guard(self) -> None:
        """Forbidden promise detection causes guard failure."""
        text = "我们会在3天内解决您的问题。"
        draft = _draft(text)
        result = check_claim_guard(draft, [])
        assert result.has_forbidden_promise is True
        assert result.guard_passed is False

    def test_delegate_greeting_via_call_passes(self) -> None:
        """Ticket with delegated greeting text is handled."""
        ev = _ev(chunk_id=_CHUNK_A)
        text = f"政策[{str(_CHUNK_A)}]。"
        draft = DraftReply(
            ticket_id="TICKET-001",
            draft_text=text,
            provider_id="fake",
            citations=[],
            cited_evidence_ids=[str(_CHUNK_A)],
            unsupported_claims=[],
        )
        result = check_claim_guard(draft, [ev])
        assert result.guard_passed is True

    def test_minimal_greeting_does_not_crash(self) -> None:
        """Minimal greeting text is handled gracefully."""
        draft = _draft("您好")
        result = check_claim_guard(draft, [])
        assert result.guard_passed is True
        assert result.has_uncited_claims is False


# ---------------------------------------------------------------------------
# check_safe_escalation_language (Task 14.3)
# ---------------------------------------------------------------------------


class TestSafeEscalationLanguage:
    """Detect safe escalation language in draft text."""

    def test_detects_rgcl(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("此案件需要人工处理。") is True

    def test_detects_zrgkf(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("建议转人工客服处理。") is True

    def test_detects_xy_rgshenhe(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("此问题需要人工审核。") is True

    def test_detects_rgshencha(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("已提交人工审查。") is True

    def test_detects_shengjizhirengong(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("此案件已升级至人工处理。") is True

    def test_detects_yishengjirengong(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("此案件已升级人工处理。") is True

    def test_no_keywords_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("尊敬的客户，您好。") is False

    def test_empty_text_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language

        assert check_safe_escalation_language("") is False


# ---------------------------------------------------------------------------
# check_manual_review_acknowledgement (Task 14.3)
# ---------------------------------------------------------------------------


class TestManualReviewAcknowledgement:
    """Detect manual review acknowledgement in draft text."""

    def test_detects_rgshenhe(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("需进行人工审核。") is True

    def test_detects_xurengong_review(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("此问题需人工 review。") is True

    def test_detects_rgquerren(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("已人工确认并处理。") is True

    def test_detects_xurengongjieru(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("此案件需人工介入。") is True

    def test_no_keywords_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("尊敬的客户，您好。") is False

    def test_empty_text_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement

        assert check_manual_review_acknowledgement("") is False
