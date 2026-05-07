"""Unit tests for chat adapter — pipeline-to-chat display transformation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ticketpilot.chat import (
    ChatContext,
    ChatDisplay,
    ChatMessage,
    ChatRole,
    chat_display_to_context_metadata,
    evidence_to_display_items,
    ticket_output_to_chat_display,
    update_context_from_message,
)
from ticketpilot.drafting.claim_guard import GuardFailureType, GuardResult
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_evidence_candidate(
    chunk_id: str,
    doc_type: DocType = DocType.POLICY,
    title: str | None = None,
    score: float = 0.95,
    content: str = "退货政策规定，7天内可申请退货。",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid.UUID(chunk_id),
        doc_id=uuid.uuid4(),
        doc_type=doc_type,
        source_id=uuid.uuid4(),
        source_table="knowledge_chunks",
        content=content,
        score=score,
        rank=1,
        title=title,
    )


def _make_ticket_output(
    text: str = "我要退款，订单号12345",
    severity: RiskSeverity = RiskSeverity.LOW,
    risk_flags: list[RiskFlag] | None = None,
    must_human_review: bool = False,
    evidence: list[EvidenceCandidate] | None = None,
) -> TicketOutput:
    return TicketOutput(
        ticket_id=str(uuid.uuid4()),
        raw_ticket=RawTicket(original_text=text, submitted_at=datetime.now(timezone.utc)),
        normalized_ticket=NormalizedTicket(
            text=text,
            language="zh",
            order_numbers=["12345"],
            cleaned_at=datetime.now(timezone.utc),
        ),
        classification=ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=datetime.now(timezone.utc),
        ),
        risk_assessment=RiskAssessment(
            flags=set(risk_flags or []),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=datetime.now(timezone.utc),
        ),
        output_at=datetime.now(timezone.utc),
        evidence_candidates=evidence or [],
    )


def _make_guard_result(
    guard_passed: bool = True,
    failure_reasons: list[GuardFailureType] | None = None,
) -> GuardResult:
    return GuardResult(
        guard_passed=guard_passed,
        failure_reasons=failure_reasons or [],
    )


def _make_draft_reply(
    draft_text: str = "根据退货政策，7天内可申请退货。",
    cited_evidence_ids: list[str] | None = None,
    must_human_review: bool = False,
    escalation_reason: str | None = None,
) -> DraftReply:
    return DraftReply(
        ticket_id=str(uuid.uuid4()),
        draft_text=draft_text,
        cited_evidence_ids=cited_evidence_ids or [],
        must_human_review=must_human_review,
        escalation_reason=escalation_reason,
    )


class _FakeDraftGenResult:
    """Fake DraftGenerationResult for testing without full generator import."""

    def __init__(
        self,
        draft: DraftReply,
        guard_result: GuardResult,
    ):
        self.draft = draft
        self.guard_result = guard_result


# ---------------------------------------------------------------------------
# evidence_to_display_items
# ---------------------------------------------------------------------------

class TestEvidenceToDisplayItems:
    def test_maps_chunk_id_doc_type_title_score(self) -> None:
        ev = _make_evidence_candidate(
            "11111111-1111-1111-1111-111111111111",
            DocType.POLICY,
            "退货政策",
            0.95,
        )
        items = evidence_to_display_items([ev])
        assert len(items) == 1
        assert items[0].chunk_id == "11111111-1111-1111-1111-111111111111"
        assert items[0].doc_type == "POLICY"
        assert items[0].title == "退货政策"
        assert items[0].score == 0.95

    def test_content_preview_truncates_long_content(self) -> None:
        # 200 ASCII chars ensure truncation at 120 char limit
        long_content = "A" * 200
        ev = _make_evidence_candidate(
            "22222222-2222-2222-2222-222222222222",
            DocType.FAQ,
            "FAQ",
            0.80,
            content=long_content,
        )
        items = evidence_to_display_items([ev], preview_chars=120)
        assert len(items) == 1
        # Truncation: 120 chars + "..."
        assert len(items[0].content_preview or "") == 123
        assert items[0].content_preview.endswith("...")

    def test_empty_evidence_returns_empty_list(self) -> None:
        items = evidence_to_display_items([])
        assert items == []

    def test_multiple_evidences(self) -> None:
        ev1 = _make_evidence_candidate("33333333-3333-3333-3333-333333333333", DocType.FAQ, "FAQ标题", 0.90)
        ev2 = _make_evidence_candidate("44444444-4444-4444-4444-444444444444", DocType.CASE, "案例标题", 0.75)
        items = evidence_to_display_items([ev1, ev2])
        assert len(items) == 2
        assert items[0].chunk_id == "33333333-3333-3333-3333-333333333333"
        assert items[1].chunk_id == "44444444-4444-4444-4444-444444444444"

    def test_no_mutation_of_input(self) -> None:
        ev = _make_evidence_candidate(
            "55555555-5555-5555-5555-555555555555",
            DocType.POLICY,
            "原始标题",
            0.95,
        )
        original_chunk_id = str(ev.chunk_id)
        original_title = ev.title
        evidence_to_display_items([ev])
        assert str(ev.chunk_id) == original_chunk_id
        assert ev.title == original_title


# ---------------------------------------------------------------------------
# ticket_output_to_chat_display (no draft)
# ---------------------------------------------------------------------------

class TestTicketOutputToChatDisplayNoDraft:
    def test_creates_display_without_draft(self) -> None:
        output = _make_ticket_output(text="我要退款")
        display = ticket_output_to_chat_display(output)
        assert isinstance(display, ChatDisplay)
        assert display.user_message == "我要退款"
        assert display.ai_message is None
        assert display.draft_text is None
        assert display.guard_passed is None

    def test_risk_badge_set(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.HIGH)
        display = ticket_output_to_chat_display(output)
        assert display.risk_badge == "HIGH"

    def test_evidence_panel_set(self) -> None:
        ev = _make_evidence_candidate("66666666-6666-6666-6666-666666666666", DocType.POLICY, "退货政策", 0.95)
        output = _make_ticket_output(evidence=[ev])
        display = ticket_output_to_chat_display(output)
        assert len(display.evidence_panel) == 1
        assert display.evidence_panel[0].chunk_id == "66666666-6666-6666-6666-666666666666"

    def test_no_evidence_human_review_required_true(self) -> None:
        output = _make_ticket_output(evidence=[])
        display = ticket_output_to_chat_display(output)
        assert display.human_review_required is True

    def test_no_evidence_escalation_reason_set(self) -> None:
        output = _make_ticket_output(evidence=[])
        display = ticket_output_to_chat_display(output)
        assert display.escalation_reason is not None

    def test_risk_flags_extracted(self) -> None:
        output = _make_ticket_output(risk_flags=[RiskFlag.COMPLAINT_RISK, RiskFlag.COMPENSATION_RISK])
        display = ticket_output_to_chat_display(output)
        assert "complaint_risk" in display.risk_flags
        assert "compensation_risk" in display.risk_flags


# ---------------------------------------------------------------------------
# ticket_output_to_chat_display (with draft)
# ---------------------------------------------------------------------------

class TestTicketOutputToChatDisplayWithDraft:
    def test_guard_pass_false_human_review_required(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[])
        guard = _make_guard_result(guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE])
        draft = _make_draft_reply(must_human_review=True)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is True
        assert display.guard_passed is False
        assert "FORBIDDEN_PROMISE" in display.failure_reasons

    def test_failure_reasons_maps_to_string_list(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[])
        guard = _make_guard_result(
            guard_passed=False,
            failure_reasons=[
                GuardFailureType.FORBIDDEN_PROMISE,
                GuardFailureType.MISSING_RISK_ESCALATION,
            ],
        )
        draft = _make_draft_reply()
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert "FORBIDDEN_PROMISE" in display.failure_reasons
        assert "MISSING_RISK_ESCALATION" in display.failure_reasons

    def test_citation_ids_map_to_citation_ids_field(self) -> None:
        ev = _make_evidence_candidate("77777777-7777-7777-7777-777777777777", DocType.POLICY)
        output = _make_ticket_output(evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(
            draft_text="根据政策可以退款[{id}]。".format(id="77777777-7777-7777-7777-777777777777"),
            cited_evidence_ids=["77777777-7777-7777-7777-777777777777"],
        )
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert "77777777-7777-7777-7777-777777777777" in display.citation_ids

    def test_high_severity_always_human_review_required(self) -> None:
        ev = _make_evidence_candidate("88888888-8888-8888-8888-888888888888", DocType.POLICY)
        output = _make_ticket_output(severity=RiskSeverity.HIGH, evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(must_human_review=False)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is True

    def test_ai_message_from_draft(self) -> None:
        output = _make_ticket_output(text="我要退款")
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(draft_text="根据退货政策，7天内可申请退货。")
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.ai_message == "根据退货政策，7天内可申请退货。"
        assert display.draft_text == "根据退货政策，7天内可申请退货。"

    def test_guard_pass_true_human_review_false_for_low_severity(self) -> None:
        ev = _make_evidence_candidate("99999999-9999-9999-9999-999999999999", DocType.POLICY)
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(must_human_review=False)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is False
        assert display.guard_passed is True

    def test_draft_must_human_review_triggers_human_review(self) -> None:
        ev = _make_evidence_candidate("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", DocType.POLICY)
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(must_human_review=True)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is True

    def test_escalation_reason_from_draft(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(guard_passed=False, failure_reasons=[GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM])
        draft = _make_draft_reply(escalation_reason="draft: unsupported_claims")
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.escalation_reason == "draft: unsupported_claims"

    def test_escalation_reason_from_guard_when_not_set(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE])
        draft = _make_draft_reply(escalation_reason=None)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.escalation_reason == "guard: FORBIDDEN_PROMISE"


# ---------------------------------------------------------------------------
# chat_display_to_context_metadata
# ---------------------------------------------------------------------------

class TestChatDisplayToContextMetadata:
    def test_returns_expected_keys(self) -> None:
        display = ChatDisplay(
            user_message="退款",
            risk_badge="HIGH",
            risk_flags=["COMPENSATION_RISK"],
            evidence_panel=[],
            human_review_required=True,
        )
        metadata = chat_display_to_context_metadata(display)
        assert "risk_flags" in metadata
        assert "severity" in metadata
        assert "evidence_ids" in metadata
        assert "citation_ids" in metadata
        assert "human_review_required" in metadata

    def test_guard_passed_included_when_not_none(self) -> None:
        display = ChatDisplay(guard_passed=True)
        metadata = chat_display_to_context_metadata(display)
        assert "guard_passed" in metadata
        assert metadata["guard_passed"] is True

    def test_guard_passed_not_included_when_none(self) -> None:
        display = ChatDisplay(guard_passed=None)
        metadata = chat_display_to_context_metadata(display)
        assert "guard_passed" not in metadata

    def test_handoff_reason_from_escalation(self) -> None:
        display = ChatDisplay(escalation_reason="no evidence found")
        metadata = chat_display_to_context_metadata(display)
        assert "handoff_reason" in metadata
        assert metadata["handoff_reason"] == "no evidence found"

    def test_evidence_ids_from_evidence_panel(self) -> None:
        from ticketpilot.chat import EvidenceDisplayItem
        display = ChatDisplay(
            evidence_panel=[
                EvidenceDisplayItem(chunk_id="111", doc_type="Policy"),
                EvidenceDisplayItem(chunk_id="222", doc_type="FAQ"),
            ]
        )
        metadata = chat_display_to_context_metadata(display)
        assert metadata["evidence_ids"] == ["111", "222"]
        assert metadata["citation_ids"] == []


# ---------------------------------------------------------------------------
# Integration: adapter + update_context_from_message
# ---------------------------------------------------------------------------

class TestAdapterContextIntegration:
    def test_metadata_can_be_consumed_by_update_context(self) -> None:
        ev = _make_evidence_candidate("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", DocType.POLICY, "退货政策", 0.95)
        output = _make_ticket_output(
            text="我要退款",
            severity=RiskSeverity.MEDIUM,
            risk_flags=[RiskFlag.COMPENSATION_RISK],
            evidence=[ev],
        )
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(cited_evidence_ids=["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"])
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        metadata = chat_display_to_context_metadata(display)

        ctx = ChatContext()
        msg = ChatMessage(role=ChatRole.AI, text="draft", metadata=metadata)
        new_ctx = update_context_from_message(ctx, msg)

        assert new_ctx.latest_severity == "MEDIUM"
        assert "compensation_risk" in new_ctx.latest_risk_flags  # lowercase from f.value
        assert len(new_ctx.latest_evidence_ids) == 1
        assert new_ctx.human_review_required is False

    def test_no_mutation_of_input_ticket_output(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.HIGH)
        original_severity = output.risk_assessment.severity
        ticket_output_to_chat_display(output)
        assert output.risk_assessment.severity == original_severity

    def test_no_mutation_of_input_draft_result(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE])
        draft = _make_draft_reply()
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)
        original_guard_passed = gen_result.guard_result.guard_passed
        ticket_output_to_chat_display(output, gen_result)
        assert gen_result.guard_result.guard_passed == original_guard_passed

    def test_deterministic_output_for_same_input(self) -> None:
        ev = _make_evidence_candidate("cccccccc-cccc-cccc-cccc-cccccccccccc", DocType.POLICY)
        output = _make_ticket_output(
            text="我要退款",
            severity=RiskSeverity.LOW,
            evidence=[ev],
        )
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(draft_text="根据政策可以退款。")
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display1 = ticket_output_to_chat_display(output, gen_result)
        display2 = ticket_output_to_chat_display(output, gen_result)
        assert display1.user_message == display2.user_message
        assert display1.risk_badge == display2.risk_badge
        assert display1.human_review_required == display2.human_review_required
        assert display1.guard_passed == display2.guard_passed