"""Unit tests for review console helper functions.

Tests focus on pure data-transformation functions extracted from
the Streamlit console, not on Streamlit UI widgets.
"""

import os
import tempfile
from datetime import datetime
from uuid import uuid4

import pytest

from ticketpilot.drafting.schemas import (
    Citation,
    DraftedTicketResult,
    DraftReply,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.review.console import (
    DEMO_TICKET_JSON,
    _parse_raw_ticket,
    build_review_decision,
    determine_trigger_reasons,
)
from ticketpilot.review.schemas import ReviewAction
from ticketpilot.review.store import ReviewStore
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)


def _make_result(
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
    fallback_reason: str | None = None,
    unsupported_claims: list[str] | None = None,
    risk_flags: set[RiskFlag] | None = None,
    evidence_count: int = 1,
    confidence: float = 0.8,
    draft_text: str = "您好，关于退款问题...",
) -> DraftedTicketResult:
    """Build a DraftedTicketResult with controllable flags for testing."""
    ticket_id = str(uuid4())
    now = datetime.utcnow()

    evidence = [
        EvidenceCandidate(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid4(),
            source_table="knowledge_faq",
            content="退货需要在7天内申请。",
            score=0.8,
            rank=i + 1,
        )
        for i in range(evidence_count)
    ]

    ticket_output = TicketOutput(
        ticket_id=ticket_id,
        raw_ticket=RawTicket(
            original_text="我要退款",
            submitted_at=now,
        ),
        normalized_ticket=NormalizedTicket(
            text="我要退款",
            language="zh",
            cleaned_at=now,
        ),
        classification=ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=now,
        ),
        risk_assessment=RiskAssessment(
            flags=risk_flags or set(),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=now,
        ),
        output_at=now,
        evidence_candidates=evidence,
    )

    draft_reply = DraftReply(
        ticket_id=ticket_id,
        draft_text=draft_text,
        citations=[
            Citation(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table="knowledge_faq",
                source_id=uuid4(),
                evidence_excerpt="退货需要在7天内申请。",
            )
        ],
        evidence_used=[],
        unsupported_claims=unsupported_claims or [],
        missing_information=[],
        confidence=confidence,
        must_human_review=must_human_review,
        fallback_reason=fallback_reason,
    )

    return DraftedTicketResult(
        ticket_output=ticket_output,
        draft_reply=draft_reply,
    )


class TestParseRawTicket:
    """Tests for _parse_raw_ticket()."""

    def test_valid_json_parses(self):
        """Well-formed RawTicket JSON should parse successfully."""
        ticket = _parse_raw_ticket(DEMO_TICKET_JSON)
        assert isinstance(ticket, RawTicket)
        assert ticket.original_text == "我要退款，订单号是 12345，请帮我处理。"
        assert ticket.customer_id == "cust-001"

    def test_empty_input_raises_value_error(self):
        """Empty input should raise ValueError with Chinese message."""
        with pytest.raises(ValueError, match="请输入工单 JSON"):
            _parse_raw_ticket("")

    def test_whitespace_input_raises_value_error(self):
        """Whitespace-only input should raise ValueError with Chinese message."""
        with pytest.raises(ValueError, match="请输入工单 JSON"):
            _parse_raw_ticket("   \n  \t  ")

    def test_invalid_json_raises_value_error(self):
        """Malformed JSON should raise ValueError with Chinese message."""
        with pytest.raises(ValueError, match="请输入有效 JSON"):
            _parse_raw_ticket("not json at all")

    def test_invalid_json_structure_raises_error(self):
        """Valid JSON that doesn't match RawTicket schema should raise."""
        with pytest.raises(ValueError):
            _parse_raw_ticket('{"foo": "bar"}')

    def test_whitespace_around_valid_json_is_accepted(self):
        """Leading/trailing whitespace around valid JSON should be tolerated."""
        ticket = _parse_raw_ticket(f"  \n  {DEMO_TICKET_JSON}  \n  ")
        assert isinstance(ticket, RawTicket)
        assert ticket.original_text == "我要退款，订单号是 12345，请帮我处理。"


class TestDetermineTriggerReasons:
    """Tests for determine_trigger_reasons()."""

    def test_no_triggers_when_none_apply(self):
        """Low-risk ticket with evidence should have no trigger reasons."""
        result = _make_result()
        reasons = determine_trigger_reasons(result)
        assert reasons == []

    def test_high_risk_trigger_via_must_human_review(self):
        """must_human_review=True should add 'high_risk' reason."""
        result = _make_result(must_human_review=True)
        reasons = determine_trigger_reasons(result)
        assert "high_risk" in reasons
        assert len(reasons) == 1

    def test_high_risk_trigger_via_severity_high(self):
        """HIGH severity alone should add 'high_risk' reason."""
        result = _make_result(severity=RiskSeverity.HIGH)
        reasons = determine_trigger_reasons(result)
        assert "high_risk" in reasons
        assert len(reasons) == 1

    def test_no_evidence_trigger(self):
        """Fallback reason 'no_evidence' should add 'no_evidence' reason."""
        result = _make_result(fallback_reason="no_evidence")
        reasons = determine_trigger_reasons(result)
        assert "no_evidence" in reasons
        assert len(reasons) == 1

    def test_unsupported_claims_trigger(self):
        """Non-empty unsupported_claims should add 'unsupported_claims' reason."""
        result = _make_result(unsupported_claims=["未经验证的声明"])
        reasons = determine_trigger_reasons(result)
        assert "unsupported_claims" in reasons
        assert len(reasons) == 1

    def test_generation_error_trigger(self):
        """Fallback reason 'generation_error' should add 'generation_error' reason."""
        result = _make_result(fallback_reason="generation_error")
        reasons = determine_trigger_reasons(result)
        assert "generation_error" in reasons
        assert len(reasons) == 1

    def test_multiple_trigger_reasons(self):
        """Multiple conditions should all appear in trigger reasons."""
        result = _make_result(
            must_human_review=True,
            severity=RiskSeverity.HIGH,
            fallback_reason="generation_error",
            unsupported_claims=["未经验证的声明"],
        )
        reasons = determine_trigger_reasons(result)
        assert "high_risk" in reasons
        assert "generation_error" in reasons
        assert "unsupported_claims" in reasons
        assert len(reasons) == 3

    def test_high_risk_and_no_evidence_together(self):
        """High risk ticket with no-evidence fallback should have both reasons."""
        result = _make_result(
            must_human_review=True,
            severity=RiskSeverity.HIGH,
            fallback_reason="no_evidence",
        )
        reasons = determine_trigger_reasons(result)
        assert "high_risk" in reasons
        assert "no_evidence" in reasons
        assert len(reasons) == 2

    def test_empty_reasons_for_low_risk_with_evidence(self):
        """Fully normal ticket should have empty trigger reasons."""
        result = _make_result(
            must_human_review=False,
            severity=RiskSeverity.LOW,
            fallback_reason=None,
            unsupported_claims=None,
        )
        reasons = determine_trigger_reasons(result)
        assert reasons == []


class TestBuildReviewDecision:
    """Tests for build_review_decision()."""

    def test_approve_action(self):
        """APPROVE action should set action correctly and not require extra fields."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.action == ReviewAction.APPROVE
        assert decision.original_draft_text == result.draft_reply.draft_text
        assert decision.edited_text is None
        assert decision.decision_reason == ""

    def test_edit_preserves_original_and_stores_edited(self):
        """EDIT action should keep original_draft_text and store edited_text."""
        result = _make_result()
        edited = "您好，已为您处理退款申请，预计3个工作日内到账。"
        decision = build_review_decision(
            result, ReviewAction.EDIT, edited_text=edited
        )
        assert decision.action == ReviewAction.EDIT
        assert decision.original_draft_text == result.draft_reply.draft_text
        assert decision.edited_text == edited

    def test_escalate_decision_reason(self):
        """ESCALATE action should store the decision_reason."""
        result = _make_result()
        reason = "需要法务团队审核，涉及赔偿条款"
        decision = build_review_decision(
            result, ReviewAction.ESCALATE, decision_reason=reason
        )
        assert decision.action == ReviewAction.ESCALATE
        assert decision.decision_reason == reason

    def test_reject_decision_reason(self):
        """REJECT action should store the decision_reason."""
        result = _make_result()
        reason = "回复内容不准确，需要重新生成"
        decision = build_review_decision(
            result, ReviewAction.REJECT, decision_reason=reason
        )
        assert decision.action == ReviewAction.REJECT
        assert decision.decision_reason == reason

    def test_populates_ticket_fields(self):
        """Decision should carry over ticket_id, ticket_text, intent, confidence."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.ticket_id == result.ticket_output.ticket_id
        assert decision.ticket_text == result.ticket_output.normalized_ticket.text
        assert decision.intent == result.ticket_output.classification.intent.value
        assert decision.confidence == result.draft_reply.confidence

    def test_was_high_risk_from_must_human_review(self):
        """was_high_risk should be True when must_human_review is True."""
        result = _make_result(must_human_review=True)
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.was_high_risk is True

    def test_was_high_risk_from_severity_high(self):
        """was_high_risk should be True when severity is HIGH."""
        result = _make_result(severity=RiskSeverity.HIGH)
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.was_high_risk is True

    def test_was_high_risk_false_for_low_risk(self):
        """was_high_risk should be False for low-risk tickets."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.was_high_risk is False

    def test_had_unsupported_claims_true(self):
        """had_unsupported_claims should be True when draft has unsupported claims."""
        result = _make_result(unsupported_claims=["未经验证的声明"])
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.had_unsupported_claims is True

    def test_had_unsupported_claims_false(self):
        """had_unsupported_claims should be False when no unsupported claims."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.had_unsupported_claims is False

    def test_risk_flags_populated(self):
        """Risk flags from assessment should be carried over as strings."""
        flags = {RiskFlag.COMPENSATION_RISK, RiskFlag.LEGAL_RISK}
        result = _make_result(risk_flags=flags)
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "compensation_risk" in decision.risk_flags
        assert "legal_risk" in decision.risk_flags

    def test_citations_summary_populated(self):
        """Citation chunk_id and doc_type should appear in citations_summary."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert len(decision.citations_summary) == 1
        entry = decision.citations_summary[0]
        assert "chunk_id" in entry
        assert entry["doc_type"] == "FAQ"

    def test_evidence_used_count(self):
        """evidence_used_count should match length of draft.evidence_used."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.evidence_used_count == len(result.draft_reply.evidence_used)

    def test_review_trigger_reasons_high_risk(self):
        """High-risk ticket should have high_risk trigger reason."""
        result = _make_result(must_human_review=True)
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "high_risk" in decision.review_trigger_reasons

    def test_review_trigger_reasons_no_evidence(self):
        """No-evidence fallback should appear in trigger reasons."""
        result = _make_result(fallback_reason="no_evidence")
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "no_evidence" in decision.review_trigger_reasons

    def test_review_trigger_reasons_unsupported_claims(self):
        """Unsupported claims should appear in trigger reasons."""
        result = _make_result(unsupported_claims=["未验证的声明"])
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "unsupported_claims" in decision.review_trigger_reasons

    def test_review_trigger_reasons_generation_error(self):
        """Generation error should appear in trigger reasons."""
        result = _make_result(fallback_reason="generation_error")
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "generation_error" in decision.review_trigger_reasons

    def test_review_id_generated(self):
        """Decision should have a non-empty review_id."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.review_id
        assert len(decision.review_id) > 0

    def test_reviewed_at_is_datetime(self):
        """reviewed_at should be set to a datetime."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert isinstance(decision.reviewed_at, datetime)

    def test_reviewer_label_default_empty(self):
        """reviewer_label should default to empty string."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert decision.reviewer_label == ""


class TestSaveReview:
    """Tests that build_review_decision + ReviewStore persistence work end-to-end."""

    def test_save_approve_decision(self):
        """APPROVE decision can be saved to ReviewStore and loaded back."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].review_id == decision.review_id
            assert loaded[0].action == ReviewAction.APPROVE

    def test_save_edit_decision(self):
        """EDIT decision preserves edited_text through save/load."""
        result = _make_result()
        edited = "您好，已为您处理。"
        decision = build_review_decision(
            result, ReviewAction.EDIT, edited_text=edited
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.EDIT
            assert loaded[0].edited_text == edited
            assert loaded[0].original_draft_text == result.draft_reply.draft_text

    def test_save_escalate_decision(self):
        """ESCALATE decision stores decision_reason through save/load."""
        result = _make_result()
        reason = "需要法务审核"
        decision = build_review_decision(
            result, ReviewAction.ESCALATE, decision_reason=reason
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.ESCALATE
            assert loaded[0].decision_reason == reason

    def test_save_reject_decision(self):
        """REJECT decision stores decision_reason through save/load."""
        result = _make_result()
        reason = "回复内容不准确"
        decision = build_review_decision(
            result, ReviewAction.REJECT, decision_reason=reason
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.REJECT
            assert loaded[0].decision_reason == reason

    def test_multiple_decisions_accumulate(self):
        """Multiple saves should accumulate in the store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            result1 = _make_result()
            result2 = _make_result()
            store.save(build_review_decision(result1, ReviewAction.APPROVE))
            store.save(build_review_decision(result2, ReviewAction.REJECT, decision_reason="不采纳"))
            loaded = store.load_all()
            assert len(loaded) == 2
            assert loaded[0].action == ReviewAction.APPROVE
            assert loaded[1].action == ReviewAction.REJECT

    def test_count_updates_correctly(self):
        """Store count should reflect the number of saved decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            assert store.count() == 0
            result = _make_result()
            store.save(build_review_decision(result, ReviewAction.APPROVE))
            assert store.count() == 1
            store.save(build_review_decision(result, ReviewAction.EDIT, edited_text="edit"))
            assert store.count() == 2


class TestReviewTriggerReasonsScenarios:
    """Scenario-based tests for review_trigger_reasons population."""

    def test_high_risk_trigger_scenario(self):
        """Scenario: high-risk ticket with legal flags."""
        flags = {RiskFlag.LEGAL_RISK, RiskFlag.COMPENSATION_RISK}
        result = _make_result(
            must_human_review=True, severity=RiskSeverity.HIGH, risk_flags=flags
        )
        decision = build_review_decision(result, ReviewAction.ESCALATE, decision_reason="法务介入")
        assert "high_risk" in decision.review_trigger_reasons
        assert decision.was_high_risk is True
        assert "legal_risk" in decision.risk_flags
        assert "compensation_risk" in decision.risk_flags

    def test_no_evidence_scenario(self):
        """Scenario: no evidence found, fallback triggered."""
        result = _make_result(
            evidence_count=0, fallback_reason="no_evidence", confidence=0.0
        )
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "no_evidence" in decision.review_trigger_reasons
        assert decision.evidence_used_count == 0
        assert decision.confidence == 0.0

    def test_unsupported_claims_scenario(self):
        """Scenario: draft contains claims not backed by evidence."""
        result = _make_result(
            unsupported_claims=["客户可申请全额赔偿", "根据公司政策第5条"]
        )
        decision = build_review_decision(result, ReviewAction.EDIT, edited_text="修正后的文本")
        assert "unsupported_claims" in decision.review_trigger_reasons
        assert decision.had_unsupported_claims is True

    def test_generation_error_scenario(self):
        """Scenario: draft generation failed with exception."""
        result = _make_result(
            evidence_count=0,
            fallback_reason="generation_error",
            confidence=0.0,
            draft_text="根据现有信息，无法确认具体政策条款，建议转人工处理。",
        )
        decision = build_review_decision(result, ReviewAction.APPROVE)
        assert "generation_error" in decision.review_trigger_reasons
        assert decision.confidence == 0.0

    def test_all_triggers_scenario(self):
        """Scenario: all compatible trigger conditions present simultaneously.

        Note: ``no_evidence`` and ``generation_error`` are mutually exclusive
        (both come from ``fallback_reason``), so this tests the three that
        can co-occur: high_risk, unsupported_claims, and no_evidence.
        """
        result = _make_result(
            must_human_review=True,
            severity=RiskSeverity.HIGH,
            evidence_count=0,
            fallback_reason="no_evidence",
            unsupported_claims=["未验证声明"],
            confidence=0.0,
            risk_flags={RiskFlag.LEGAL_RISK},
        )
        decision = build_review_decision(result, ReviewAction.ESCALATE, decision_reason="多重问题")
        triggers = decision.review_trigger_reasons
        assert "high_risk" in triggers
        assert "no_evidence" in triggers
        assert "unsupported_claims" in triggers
        assert len(triggers) == 3
        assert decision.was_high_risk is True
        assert decision.had_unsupported_claims is True
