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
