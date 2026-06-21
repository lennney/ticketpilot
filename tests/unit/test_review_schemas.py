"""Unit tests for ReviewDecision schema and ReviewAction enum."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ticketpilot.review.schemas import ReviewAction, ReviewDecision


class TestReviewAction:
    """ReviewAction enum validation."""

    def test_has_four_values(self):
        values = list(ReviewAction)
        assert len(values) == 4
        assert ReviewAction.APPROVE in values
        assert ReviewAction.EDIT in values
        assert ReviewAction.ESCALATE in values
        assert ReviewAction.REJECT in values

    def test_is_string_enum(self):
        assert ReviewAction.APPROVE.value == "approve"
        assert ReviewAction.EDIT.value == "edit"
        assert ReviewAction.ESCALATE.value == "escalate"
        assert ReviewAction.REJECT.value == "reject"

    def test_approve_equals_string(self):
        assert ReviewAction.APPROVE == "approve"

    def test_reject_equals_string(self):
        assert ReviewAction.REJECT == "reject"


class TestReviewDecision:
    """ReviewDecision Pydantic model validation."""

    def test_valid_approve_decision(self):
        decision = ReviewDecision(
            ticket_id="ticket-001",
            ticket_text="我要退款",
            action=ReviewAction.APPROVE,
            original_draft_text="您好，关于退款问题...",
            confidence=0.8,
            had_unsupported_claims=False,
            was_high_risk=False,
            intent="refund",
            risk_flags=[],
        )
        assert decision.review_id is not None
        assert len(decision.review_id) > 0
        assert decision.action == ReviewAction.APPROVE
        assert decision.confidence == 0.8
        assert decision.edited_text is None

    def test_edit_decision_with_edited_text(self):
        decision = ReviewDecision(
            ticket_id="ticket-002",
            ticket_text="订单未收到",
            action=ReviewAction.EDIT,
            original_draft_text="您好，关于物流问题...",
            edited_text="您好，关于物流问题，我们已经为您查询。",
            decision_reason="补充了物流查询信息",
            confidence=0.6,
        )
        assert decision.action == ReviewAction.EDIT
        assert decision.edited_text == "您好，关于物流问题，我们已经为您查询。"
        assert decision.decision_reason == "补充了物流查询信息"

    def test_escalate_decision_with_reason(self):
        decision = ReviewDecision(
            ticket_id="ticket-003",
            ticket_text="律师函警告",
            action=ReviewAction.ESCALATE,
            original_draft_text="根据现有信息...",
            decision_reason="涉及法律风险，需法务团队处理",
            was_high_risk=True,
            risk_flags=["LEGAL_RISK"],
        )
        assert decision.action == ReviewAction.ESCALATE
        assert decision.decision_reason == "涉及法律风险，需法务团队处理"
        assert decision.was_high_risk is True
        assert "LEGAL_RISK" in decision.risk_flags

    def test_reject_decision_with_reason(self):
        decision = ReviewDecision(
            ticket_id="ticket-004",
            ticket_text="要求赔偿",
            action=ReviewAction.REJECT,
            original_draft_text="您好，关于赔偿问题...",
            decision_reason="赔偿金额超出权限，需重新评估",
            had_unsupported_claims=True,
        )
        assert decision.action == ReviewAction.REJECT
        assert decision.decision_reason == "赔偿金额超出权限，需重新评估"
        assert decision.had_unsupported_claims is True

    def test_defaults(self):
        decision = ReviewDecision(
            ticket_id="ticket-005",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="测试草稿",
        )
        assert decision.edited_text is None
        assert decision.decision_reason == ""
        assert decision.had_unsupported_claims is False
        assert decision.was_high_risk is False
        assert decision.risk_flags == []
        assert decision.citations_summary == []
        assert decision.evidence_used_count == 0
        assert decision.review_trigger_reasons == []
        assert decision.reviewer_label == ""
        assert isinstance(decision.reviewed_at, datetime)

    def test_json_serialization_roundtrip(self):
        decision = ReviewDecision(
            ticket_id="ticket-006",
            ticket_text="我要退款",
            action=ReviewAction.APPROVE,
            original_draft_text="您好，关于退款问题...",
            confidence=0.85,
            had_unsupported_claims=False,
            was_high_risk=False,
            intent="refund",
            risk_flags=[],
            citations_summary=[{"chunk_id": "abc", "doc_type": "FAQ"}],
            evidence_used_count=1,
            review_trigger_reasons=["no_evidence", "generation_error"],
            reviewer_label="reviewer-zhang",
        )
        json_str = decision.model_dump_json()
        restored = ReviewDecision.model_validate_json(json_str)
        assert restored.review_id == decision.review_id
        assert restored.ticket_id == decision.ticket_id
        assert restored.action == decision.action
        assert restored.confidence == decision.confidence
        assert restored.citations_summary == decision.citations_summary
        assert restored.evidence_used_count == decision.evidence_used_count
        assert restored.review_trigger_reasons == decision.review_trigger_reasons
        assert restored.reviewer_label == "reviewer-zhang"

    def test_rejects_invalid_action(self):
        with pytest.raises(ValidationError):
            ReviewDecision(
                ticket_id="ticket-007",
                ticket_text="测试",
                action="invalid_action",
                original_draft_text="测试",
            )

    def test_preserves_ticket_id(self):
        decision = ReviewDecision(
            ticket_id="ticket-008",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="测试草稿",
        )
        assert decision.ticket_id == "ticket-008"

    def test_evidence_used_count_default(self):
        decision = ReviewDecision(
            ticket_id="ticket-009",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="测试草稿",
        )
        assert decision.evidence_used_count == 0


class TestReviewDecisionAuditFields:
    """Tests for optional draft audit fields (Phase 11.7)."""

    def test_provider_name_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-010",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )
        assert decision.provider_name == "openai"
        assert decision.model_name == "gpt-4o-mini"

    def test_provider_name_defaults_to_none(self):
        decision = ReviewDecision(
            ticket_id="ticket-011",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
        )
        assert decision.provider_name is None
        assert decision.model_name is None

    def test_citation_validation_fields_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-012",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            citation_validation_valid=True,
            valid_cited_evidence_ids=["id1", "id2"],
            invalid_cited_evidence_ids=["id3"],
            missing_citation_required=False,
        )
        assert decision.citation_validation_valid is True
        assert decision.valid_cited_evidence_ids == ["id1", "id2"]
        assert decision.invalid_cited_evidence_ids == ["id3"]
        assert decision.missing_citation_required is False

    def test_citation_validation_defaults(self):
        decision = ReviewDecision(
            ticket_id="ticket-013",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
        )
        assert decision.citation_validation_valid is None
        assert decision.valid_cited_evidence_ids == []
        assert decision.invalid_cited_evidence_ids == []
        assert decision.missing_citation_required is None

    def test_guard_passed_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-014",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            guard_passed=True,
        )
        assert decision.guard_passed is True

    def test_guard_uncited_claims_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-015",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            guard_uncited_claims=False,
        )
        assert decision.guard_uncited_claims is False

    def test_guard_forbidden_promise_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-016",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            guard_forbidden_promise=True,
            guard_forbidden_details=["refund_amount", "compensation_amount"],
        )
        assert decision.guard_forbidden_promise is True
        assert decision.guard_forbidden_details == [
            "refund_amount",
            "compensation_amount",
        ]

    def test_guard_forbidden_details_defaults_empty(self):
        decision = ReviewDecision(
            ticket_id="ticket-017",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
        )
        assert decision.guard_forbidden_details == []

    def test_guard_risk_not_acknowledged_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-018",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            guard_risk_not_acknowledged=True,
        )
        assert decision.guard_risk_not_acknowledged is True

    def test_human_review_forced_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-019",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            human_review_forced=True,
        )
        assert decision.human_review_forced is True

    def test_human_review_reasons_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-020",
            ticket_text="测试",
            action=ReviewAction.ESCALATE,
            original_draft_text="草稿",
            decision_reason="需要法务审核",
            human_review_reasons=["fallback:no_evidence", "guard_failed"],
        )
        assert decision.human_review_reasons == ["fallback:no_evidence", "guard_failed"]

    def test_human_review_reasons_defaults_empty(self):
        decision = ReviewDecision(
            ticket_id="ticket-021",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
        )
        assert decision.human_review_reasons == []

    def test_escalation_reason_optional(self):
        decision = ReviewDecision(
            ticket_id="ticket-022",
            ticket_text="测试",
            action=ReviewAction.ESCALATE,
            original_draft_text="草稿",
            decision_reason="升级处理",
            escalation_reason="guard: forbidden_promise",
        )
        assert decision.escalation_reason == "guard: forbidden_promise"

    def test_full_audit_fields_populated(self):
        """All 15 audit fields can be set simultaneously."""
        decision = ReviewDecision(
            ticket_id="ticket-023",
            ticket_text="我要退款",
            action=ReviewAction.ESCALATE,
            original_draft_text="草稿",
            decision_reason="禁止承诺",
            provider_name="fake",
            model_name="draft-v1",
            citation_validation_valid=False,
            valid_cited_evidence_ids=["id1"],
            invalid_cited_evidence_ids=["id2", "id3"],
            missing_citation_required=True,
            guard_passed=False,
            guard_uncited_claims=True,
            guard_forbidden_promise=True,
            guard_forbidden_details=["refund_amount"],
            guard_risk_not_acknowledged=False,
            human_review_forced=True,
            human_review_reasons=[
                "fallback:no_evidence",
                "citation_validation_failed",
                "guard_failed",
                "forbidden_promise",
            ],
            escalation_reason="guard: forbidden_promise",
        )
        assert decision.provider_name == "fake"
        assert decision.model_name == "draft-v1"
        assert decision.citation_validation_valid is False
        assert decision.valid_cited_evidence_ids == ["id1"]
        assert decision.invalid_cited_evidence_ids == ["id2", "id3"]
        assert decision.missing_citation_required is True
        assert decision.guard_passed is False
        assert decision.guard_uncited_claims is True
        assert decision.guard_forbidden_promise is True
        assert decision.guard_forbidden_details == ["refund_amount"]
        assert decision.guard_risk_not_acknowledged is False
        assert decision.human_review_forced is True
        assert len(decision.human_review_reasons) == 4
        assert decision.escalation_reason == "guard: forbidden_promise"

    def test_json_roundtrip_preserves_audit_fields(self):
        """Audit fields survive JSON serialization roundtrip."""
        decision = ReviewDecision(
            ticket_id="ticket-024",
            ticket_text="测试",
            action=ReviewAction.APPROVE,
            original_draft_text="草稿",
            provider_name="openai",
            model_name="gpt-4o-mini",
            citation_validation_valid=True,
            valid_cited_evidence_ids=["id1"],
            guard_passed=True,
            human_review_reasons=["fallback:no_evidence"],
        )
        json_str = decision.model_dump_json()
        restored = ReviewDecision.model_validate_json(json_str)
        assert restored.provider_name == "openai"
        assert restored.model_name == "gpt-4o-mini"
        assert restored.citation_validation_valid is True
        assert restored.valid_cited_evidence_ids == ["id1"]
        assert restored.guard_passed is True
        assert restored.human_review_reasons == ["fallback:no_evidence"]

    def test_backward_compatibility_with_old_record(self):
        """Old records without audit fields deserialize without error."""
        # Simulate an old record (Phase 11.6 and before)
        old_json = """{
            "review_id": "550e8400-e29b-41d4-a716-446655440000",
            "ticket_id": "ticket-old",
            "ticket_text": "我要退款",
            "action": "approve",
            "original_draft_text": "您好...",
            "confidence": 0.8,
            "had_unsupported_claims": false,
            "was_high_risk": false,
            "intent": "refund",
            "risk_flags": [],
            "citations_summary": [],
            "evidence_used_count": 1,
            "review_trigger_reasons": [],
            "reviewer_label": "",
            "reviewed_at": "2026-05-06T10:00:00"
        }"""
        restored = ReviewDecision.model_validate_json(old_json)
        assert restored.ticket_id == "ticket-old"
        assert restored.action == ReviewAction.APPROVE
        # All audit fields default to None/[]
        assert restored.provider_name is None
        assert restored.model_name is None
        assert restored.citation_validation_valid is None
        assert restored.valid_cited_evidence_ids == []
        assert restored.invalid_cited_evidence_ids == []
        assert restored.missing_citation_required is None
        assert restored.guard_passed is None
        assert restored.guard_uncited_claims is None
        assert restored.guard_forbidden_promise is None
        assert restored.guard_forbidden_details == []
        assert restored.guard_risk_not_acknowledged is None
        assert restored.human_review_forced is None
        assert restored.human_review_reasons == []
        assert restored.escalation_reason is None
