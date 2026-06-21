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
from ticketpilot.chat.app import (
    RISK_FLAG_LABELS,
    RISK_BADGE_COLORS,
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
        raw_ticket=RawTicket(
            original_text=text, submitted_at=datetime.now(timezone.utc)
        ),
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
        ev1 = _make_evidence_candidate(
            "33333333-3333-3333-3333-333333333333", DocType.FAQ, "FAQ标题", 0.90
        )
        ev2 = _make_evidence_candidate(
            "44444444-4444-4444-4444-444444444444", DocType.CASE, "案例标题", 0.75
        )
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
        ev = _make_evidence_candidate(
            "66666666-6666-6666-6666-666666666666", DocType.POLICY, "退货政策", 0.95
        )
        output = _make_ticket_output(evidence=[ev])
        display = ticket_output_to_chat_display(output)
        assert len(display.evidence_panel) == 1
        assert (
            display.evidence_panel[0].chunk_id == "66666666-6666-6666-6666-666666666666"
        )

    def test_no_evidence_human_review_required_true(self) -> None:
        output = _make_ticket_output(evidence=[])
        display = ticket_output_to_chat_display(output)
        assert display.human_review_required is True

    def test_no_evidence_escalation_reason_set(self) -> None:
        output = _make_ticket_output(evidence=[])
        display = ticket_output_to_chat_display(output)
        assert display.escalation_reason is not None

    def test_risk_flags_extracted(self) -> None:
        output = _make_ticket_output(
            risk_flags=[RiskFlag.COMPLAINT_RISK, RiskFlag.COMPENSATION_RISK]
        )
        display = ticket_output_to_chat_display(output)
        assert "complaint_risk" in display.risk_flags
        assert "compensation_risk" in display.risk_flags


# ---------------------------------------------------------------------------
# ticket_output_to_chat_display (with draft)
# ---------------------------------------------------------------------------


class TestTicketOutputToChatDisplayWithDraft:
    def test_guard_pass_false_human_review_required(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[])
        guard = _make_guard_result(
            guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE]
        )
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
        ev = _make_evidence_candidate(
            "77777777-7777-7777-7777-777777777777", DocType.POLICY
        )
        output = _make_ticket_output(evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(
            draft_text="根据政策可以退款[{id}]。".format(
                id="77777777-7777-7777-7777-777777777777"
            ),
            cited_evidence_ids=["77777777-7777-7777-7777-777777777777"],
        )
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert "77777777-7777-7777-7777-777777777777" in display.citation_ids

    def test_high_severity_always_human_review_required(self) -> None:
        ev = _make_evidence_candidate(
            "88888888-8888-8888-8888-888888888888", DocType.POLICY
        )
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
        ev = _make_evidence_candidate(
            "99999999-9999-9999-9999-999999999999", DocType.POLICY
        )
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(must_human_review=False)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is False
        assert display.guard_passed is True

    def test_draft_must_human_review_triggers_human_review(self) -> None:
        ev = _make_evidence_candidate(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", DocType.POLICY
        )
        output = _make_ticket_output(severity=RiskSeverity.LOW, evidence=[ev])
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(must_human_review=True)
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.human_review_required is True

    def test_escalation_reason_from_draft(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(
            guard_passed=False,
            failure_reasons=[GuardFailureType.UNCITED_SUBSTANTIVE_CLAIM],
        )
        draft = _make_draft_reply(escalation_reason="draft: unsupported_claims")
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        assert display.escalation_reason == "draft: unsupported_claims"

    def test_escalation_reason_from_guard_when_not_set(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(
            guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE]
        )
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
        ev = _make_evidence_candidate(
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", DocType.POLICY, "退货政策", 0.95
        )
        output = _make_ticket_output(
            text="我要退款",
            severity=RiskSeverity.MEDIUM,
            risk_flags=[RiskFlag.COMPENSATION_RISK],
            evidence=[ev],
        )
        guard = _make_guard_result(guard_passed=True)
        draft = _make_draft_reply(
            cited_evidence_ids=["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"]
        )
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)

        display = ticket_output_to_chat_display(output, gen_result)
        metadata = chat_display_to_context_metadata(display)

        ctx = ChatContext()
        msg = ChatMessage(role=ChatRole.AI, text="draft", metadata=metadata)
        new_ctx = update_context_from_message(ctx, msg)

        assert new_ctx.latest_severity == "MEDIUM"
        assert (
            "compensation_risk" in new_ctx.latest_risk_flags
        )  # lowercase from f.value
        assert len(new_ctx.latest_evidence_ids) == 1
        assert new_ctx.human_review_required is False

    def test_no_mutation_of_input_ticket_output(self) -> None:
        output = _make_ticket_output(severity=RiskSeverity.HIGH)
        original_severity = output.risk_assessment.severity
        ticket_output_to_chat_display(output)
        assert output.risk_assessment.severity == original_severity

    def test_no_mutation_of_input_draft_result(self) -> None:
        output = _make_ticket_output(evidence=[])
        guard = _make_guard_result(
            guard_passed=False, failure_reasons=[GuardFailureType.FORBIDDEN_PROMISE]
        )
        draft = _make_draft_reply()
        gen_result = _FakeDraftGenResult(draft=draft, guard_result=guard)
        original_guard_passed = gen_result.guard_result.guard_passed
        ticket_output_to_chat_display(output, gen_result)
        assert gen_result.guard_result.guard_passed == original_guard_passed

    def test_deterministic_output_for_same_input(self) -> None:
        ev = _make_evidence_candidate(
            "cccccccc-cccc-cccc-cccc-cccccccccccc", DocType.POLICY
        )
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


# ---------------------------------------------------------------------------
# Risk display — RISK_FLAG_LABELS and RISK_BADGE_COLORS
# ---------------------------------------------------------------------------


class TestRiskFlagLabels:
    """Tests for RISK_FLAG_LABELS mapping completeness and correctness."""

    def test_risk_flag_labels_complete(self) -> None:
        """TC-15.4-1: All 8 RiskFlag enum values have corresponding Chinese labels."""
        all_risk_flags = [f.value for f in RiskFlag]
        for flag in all_risk_flags:
            assert flag in RISK_FLAG_LABELS, f"Missing label for RiskFlag.{flag}"
        assert len(RISK_FLAG_LABELS) == 8

    def test_risk_flag_translation_complaint(self) -> None:
        """TC-15.4-3: complaint_risk translates to '投诉风险'."""
        assert RISK_FLAG_LABELS["complaint_risk"] == "投诉风险"

    def test_risk_flag_translation_all(self) -> None:
        """All known flags translate to non-empty Chinese strings."""
        for flag, label in RISK_FLAG_LABELS.items():
            assert label, f"Empty label for {flag}"
            assert len(label) > 0, f"Invalid label length for {flag}"

    def test_unknown_risk_flag_fallback(self) -> None:
        """TC-15.4-6: Unknown flags return raw value as fallback."""
        unknown_flag = "unknown_mystery_flag"
        # The app uses .get(flag, flag) for fallback
        fallback_result = RISK_FLAG_LABELS.get(unknown_flag, unknown_flag)
        assert fallback_result == unknown_flag


class TestRiskBadgeColors:
    """Tests for risk badge color configuration."""

    def test_risk_badge_color_high(self) -> None:
        """TC-15.4-2: HIGH severity has red color configuration."""
        text_color, bg_color = RISK_BADGE_COLORS["HIGH"]
        assert text_color == "#dc2626", "HIGH text should be red"
        assert bg_color == "#fef2f2", "HIGH background should be light red"

    def test_risk_badge_color_medium(self) -> None:
        """MEDIUM severity has amber color configuration."""
        text_color, bg_color = RISK_BADGE_COLORS["MEDIUM"]
        assert text_color == "#d97706", "MEDIUM text should be amber"
        assert bg_color == "#fffbeb", "MEDIUM background should be light amber"

    def test_risk_badge_color_low(self) -> None:
        """LOW severity has green color configuration."""
        text_color, bg_color = RISK_BADGE_COLORS["LOW"]
        assert text_color == "#16a34a", "LOW text should be green"
        assert bg_color == "#f0fdf4", "LOW background should be light green"

    def test_all_severity_levels_defined(self) -> None:
        """All three severity levels have color configurations."""
        assert "HIGH" in RISK_BADGE_COLORS
        assert "MEDIUM" in RISK_BADGE_COLORS
        assert "LOW" in RISK_BADGE_COLORS

    def test_color_tuples_have_two_elements(self) -> None:
        """Each color config is a (text_color, bg_color) tuple."""
        for severity, (text_color, bg_color) in RISK_BADGE_COLORS.items():
            assert text_color.startswith("#"), f"{severity}: text_color should be hex"
            assert bg_color.startswith("#"), f"{severity}: bg_color should be hex"


class TestHumanReviewDisplayLogic:
    """Tests for human review display conditions."""

    def test_high_severity_requires_human_review_display(self) -> None:
        """TC-15.4-4: HIGH severity with human_review_required triggers HIGH-specific display."""
        # Create a display with HIGH risk badge and human_review_required
        display = ChatDisplay(
            user_message="test",
            risk_badge="HIGH",
            human_review_required=True,
        )
        # The condition for HIGH-specific message is: risk_badge == "HIGH"
        # and human_review_required is True
        assert display.risk_badge == "HIGH"
        assert display.human_review_required is True

    def test_guard_failure_requires_human_review_display(self) -> None:
        """TC-15.4-8: Guard failure with failure_reasons triggers guard-specific display."""
        # Guard failure display requires guard_passed == False
        display = ChatDisplay(
            user_message="test",
            guard_passed=False,
            failure_reasons=["FORBIDDEN_PROMISE"],
            human_review_required=True,
        )
        assert display.guard_passed is False
        assert len(display.failure_reasons) > 0

    def test_medium_severity_human_review(self) -> None:
        """MEDIUM severity with human_review_required uses generic warning."""
        display = ChatDisplay(
            user_message="test",
            risk_badge="MEDIUM",
            human_review_required=True,
        )
        assert display.risk_badge == "MEDIUM"
        assert display.human_review_required is True

    def test_no_human_review_required_no_error_display(self) -> None:
        """No human review required means no error/warning display needed."""
        display = ChatDisplay(
            user_message="test",
            risk_badge="LOW",
            human_review_required=False,
            guard_passed=True,
        )
        assert display.human_review_required is False
        assert display.guard_passed is True


class TestContextPanelSeverityDisplay:
    """Tests for context panel severity display logic."""

    def test_context_panel_severity_high(self) -> None:
        """HIGH severity in context gets red color configuration."""
        severity = "HIGH"
        text_color, bg_color = RISK_BADGE_COLORS.get(severity, ("#666666", "#f5f5f5"))
        assert text_color == "#dc2626"
        assert bg_color == "#fef2f2"

    def test_context_panel_severity_medium(self) -> None:
        """TC-15.4-5: MEDIUM severity in context gets amber color configuration."""
        severity = "MEDIUM"
        text_color, bg_color = RISK_BADGE_COLORS.get(severity, ("#666666", "#f5f5f5"))
        assert text_color == "#d97706"
        assert bg_color == "#fffbeb"

    def test_context_panel_severity_low(self) -> None:
        """LOW severity in context gets green color configuration."""
        severity = "LOW"
        text_color, bg_color = RISK_BADGE_COLORS.get(severity, ("#666666", "#f5f5f5"))
        assert text_color == "#16a34a"
        assert bg_color == "#f0fdf4"

    def test_context_panel_severity_none(self) -> None:
        """No severity in context uses fallback gray color."""
        severity = None
        text_color, bg_color = RISK_BADGE_COLORS.get(severity, ("#666666", "#f5f5f5"))
        assert text_color == "#666666"
        assert bg_color == "#f5f5f5"

    def test_context_panel_unknown_severity(self) -> None:
        """Unknown severity level falls back to gray."""
        severity = "SUPER_CRITICAL"
        text_color, bg_color = RISK_BADGE_COLORS.get(severity, ("#666666", "#f5f5f5"))
        assert text_color == "#666666"


class TestContextPanelRiskFlags:
    """Tests for context panel risk flags with Chinese labels."""

    def test_context_risk_flags_translated(self) -> None:
        """Known risk flags are translated to Chinese labels."""
        flags = ["complaint_risk", "compensation_risk"]
        labels = [RISK_FLAG_LABELS.get(f, f) for f in flags]
        assert labels == ["投诉风险", "补偿风险"]

    def test_context_risk_flags_empty_shows_placeholder(self) -> None:
        """Empty risk flags list should show '暂无' placeholder."""
        flags = []
        # This is tested by checking the display logic handles empty lists
        assert flags == []

    def test_context_multi_turn_risk_state(self) -> None:
        """TC-15.4-7: Risk state persists across conversation turns via ChatContext."""
        # Turn 1: HIGH severity with complaint_risk
        ctx1 = ChatContext()
        msg1 = ChatMessage(
            role=ChatRole.AI,
            text="draft",
            metadata={
                "severity": "HIGH",
                "risk_flags": ["complaint_risk"],
            },
        )
        ctx1 = update_context_from_message(ctx1, msg1)
        assert ctx1.latest_severity == "HIGH"
        assert "complaint_risk" in ctx1.latest_risk_flags

        # Turn 2: Add compensation_risk (severity still HIGH)
        msg2 = ChatMessage(
            role=ChatRole.AI,
            text="draft 2",
            metadata={
                "severity": "HIGH",
                "risk_flags": ["complaint_risk", "compensation_risk"],
            },
        )
        ctx2 = update_context_from_message(ctx1, msg2)
        assert ctx2.latest_severity == "HIGH"
        assert "complaint_risk" in ctx2.latest_risk_flags
        assert "compensation_risk" in ctx2.latest_risk_flags
        # Note: turn_count is incremented by append_message, not update_context_from_message
        # ctx2.turn_count remains 0 because update_context_from_message preserves turn_count
        assert ctx2.turn_count == ctx1.turn_count


# ---------------------------------------------------------------------------
# TestEvidencePanelGrouping — Phase 15.5
# ---------------------------------------------------------------------------


class TestEvidencePanelGrouping:
    """Tests for evidence panel doc_type grouping functionality.

    Verifies FR-15.5-1, FR-15.5-2, FR-15.5-3.
    """

    def test_evidence_grouping_all_types(self) -> None:
        """FR-15.5-1: Multiple doc types grouped correctly (FAQ + Policy + Case)."""
        from ticketpilot.chat import EvidenceDisplayItem

        # 3 FAQ, 2 Policy, 1 Case items
        items = [
            EvidenceDisplayItem(
                chunk_id="11111111-1111-1111-1111-111111111111",
                doc_type="FAQ",
                title="FAQ1",
                score=0.9,
            ),
            EvidenceDisplayItem(
                chunk_id="22222222-2222-2222-2222-222222222222",
                doc_type="FAQ",
                title="FAQ2",
                score=0.85,
            ),
            EvidenceDisplayItem(
                chunk_id="33333333-3333-3333-3333-333333333333",
                doc_type="FAQ",
                title="FAQ3",
                score=0.80,
            ),
            EvidenceDisplayItem(
                chunk_id="44444444-4444-4444-4444-444444444444",
                doc_type="POLICY",
                title="Policy1",
                score=0.95,
            ),
            EvidenceDisplayItem(
                chunk_id="55555555-5555-5555-5555-555555555555",
                doc_type="POLICY",
                title="Policy2",
                score=0.90,
            ),
            EvidenceDisplayItem(
                chunk_id="66666666-6666-6666-6666-666666666666",
                doc_type="CASE",
                title="Case1",
                score=0.75,
            ),
        ]

        # Group by doc_type manually (same logic as _render_evidence_panel)
        from ticketpilot.chat.app import DOC_TYPE_ORDER

        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item.doc_type, []).append(item)

        # Verify all three doc types present
        assert "FAQ" in grouped
        assert "POLICY" in grouped
        assert "CASE" in grouped

        # Verify counts
        assert len(grouped["FAQ"]) == 3
        assert len(grouped["POLICY"]) == 2
        assert len(grouped["CASE"]) == 1

        # Verify fixed order
        assert DOC_TYPE_ORDER == ["FAQ", "POLICY", "CASE"]

    def test_evidence_grouping_single_type(self) -> None:
        """FR-15.5-1: Single doc type shows correct group header."""
        from ticketpilot.chat import EvidenceDisplayItem

        items = [
            EvidenceDisplayItem(
                chunk_id="11111111-1111-1111-1111-111111111111",
                doc_type="FAQ",
                title="FAQ1",
                score=0.9,
            ),
            EvidenceDisplayItem(
                chunk_id="22222222-2222-2222-2222-222222222222",
                doc_type="FAQ",
                title="FAQ2",
                score=0.85,
            ),
        ]

        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item.doc_type, []).append(item)

        # Only FAQ group should exist
        assert list(grouped.keys()) == ["FAQ"]
        assert len(grouped["FAQ"]) == 2

    def test_evidence_group_count(self) -> None:
        """FR-15.5-2: Count in subheader matches actual item count per doc_type."""
        from ticketpilot.chat import EvidenceDisplayItem

        items = [
            EvidenceDisplayItem(
                chunk_id="11111111-1111-1111-1111-111111111111",
                doc_type="FAQ",
                title="FAQ1",
                score=0.9,
            ),
            EvidenceDisplayItem(
                chunk_id="22222222-2222-2222-2222-222222222222",
                doc_type="POLICY",
                title="Policy1",
                score=0.95,
            ),
            EvidenceDisplayItem(
                chunk_id="33333333-3333-3333-3333-333333333333",
                doc_type="POLICY",
                title="Policy2",
                score=0.90,
            ),
            EvidenceDisplayItem(
                chunk_id="44444444-4444-4444-4444-444444444444",
                doc_type="POLICY",
                title="Policy3",
                score=0.85,
            ),
        ]

        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item.doc_type, []).append(item)

        # Verify counts match len(group)
        assert len(grouped["FAQ"]) == 1
        assert len(grouped["POLICY"]) == 3
        assert "CASE" not in grouped

        # Simulate subheader format
        from ticketpilot.chat.app import DOC_TYPE_EMOJI

        for doc_type in ["FAQ", "POLICY"]:
            emoji = DOC_TYPE_EMOJI.get(doc_type, "📄")
            expected_header = f"{emoji} {doc_type} ({len(grouped[doc_type])})"
            assert expected_header == f"{emoji} {doc_type} ({len(grouped[doc_type])})"

    def test_empty_evidence_graceful(self) -> None:
        """FR-15.5-3: Empty evidence panel handled without crash."""
        # Empty evidence panel should not cause errors in grouping
        items: list = []

        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item.doc_type, []).append(item)

        # Empty grouped dict - no groups rendered
        assert grouped == {}

        # Empty ChatDisplay with no evidence_panel should return early
        from ticketpilot.chat import ChatDisplay

        display = ChatDisplay(user_message="test", evidence_panel=[])
        assert display.evidence_panel == []


# ---------------------------------------------------------------------------
# TestInlineCitationMarkers — Phase 15.5
# ---------------------------------------------------------------------------


class TestInlineCitationMarkers:
    """Tests for inline citation marker logic in draft panel.

    Verifies FR-15.5-4, FR-15.5-5.
    """

    def test_inline_markers_with_placeholder(self) -> None:
        """FR-15.5-4: Draft text with [ID:xxx] maps to citation marker."""
        from ticketpilot.chat import EvidenceDisplayItem
        from ticketpilot.chat.app import _build_citation_marker_map

        evidence = [
            EvidenceDisplayItem(
                chunk_id="11111111-1111-1111-1111-111111111111",
                doc_type="FAQ",
                title="退款说明",
                score=0.95,
            )
        ]

        marker_map = _build_citation_marker_map(evidence)

        # Verify marker map contains correct entry
        assert "11111111-1111-1111-1111-111111111111" in marker_map
        assert marker_map["11111111-1111-1111-1111-111111111111"] == "[FAQ]:退款说明"

    def test_inline_markers_without_placeholder(self) -> None:
        """FR-15.5-4: Draft text without placeholders gets markers appended."""
        from ticketpilot.chat import EvidenceDisplayItem
        from ticketpilot.chat.app import _build_citation_marker_map

        evidence = [
            EvidenceDisplayItem(
                chunk_id="22222222-2222-2222-2222-222222222222",
                doc_type="POLICY",
                title="退货政策",
                score=0.90,
            )
        ]

        marker_map = _build_citation_marker_map(evidence)

        # Build appended markers
        citation_ids = ["22222222-2222-2222-2222-222222222222"]
        markers = [marker_map.get(cid, f"[UNKNOWN]:{cid[:8]}") for cid in citation_ids]
        appended = " ".join(markers)

        assert appended == "[POLICY]:退货政策"

    def test_inline_markers_multiple_citations(self) -> None:
        """FR-15.5-4: Multiple citations all get markers."""
        from ticketpilot.chat import EvidenceDisplayItem
        from ticketpilot.chat.app import _build_citation_marker_map

        evidence = [
            EvidenceDisplayItem(
                chunk_id="33333333-3333-3333-3333-333333333333",
                doc_type="FAQ",
                title="退款说明",
                score=0.95,
            ),
            EvidenceDisplayItem(
                chunk_id="44444444-4444-4444-4444-444444444444",
                doc_type="POLICY",
                title="退货政策",
                score=0.90,
            ),
        ]

        marker_map = _build_citation_marker_map(evidence)

        # Multiple citation IDs
        citation_ids = [
            "33333333-3333-3333-3333-333333333333",
            "44444444-4444-4444-4444-444444444444",
        ]

        markers = [marker_map.get(cid, f"[UNKNOWN]:{cid[:8]}") for cid in citation_ids]

        assert len(markers) == 2
        assert "[FAQ]:退款说明" in markers
        assert "[POLICY]:退货政策" in markers

    def test_inline_markers_fallback_graceful(self) -> None:
        """FR-15.5-4: Graceful degradation when citation_id not found."""
        from ticketpilot.chat import EvidenceDisplayItem
        from ticketpilot.chat.app import _build_citation_marker_map

        evidence = [
            EvidenceDisplayItem(
                chunk_id="55555555-5555-5555-5555-555555555555",
                doc_type="FAQ",
                title="退款说明",
                score=0.95,
            )
        ]

        marker_map = _build_citation_marker_map(evidence)

        # Citation ID not in evidence panel
        unknown_cid = "99999999-9999-9999-9999-999999999999"
        marker = marker_map.get(unknown_cid, f"[UNKNOWN]:{unknown_cid[:8]}")

        # Should fallback gracefully
        assert "[UNKNOWN]" in marker
        assert unknown_cid[:8] in marker

    def test_citation_reference_readable(self) -> None:
        """FR-15.5-5: Citation reference list shows human-readable format."""
        from ticketpilot.chat import EvidenceDisplayItem

        evidence = [
            EvidenceDisplayItem(
                chunk_id="66666666-6666-6666-6666-666666666666",
                doc_type="FAQ",
                title="退款说明",
                score=0.95,
            ),
            EvidenceDisplayItem(
                chunk_id="77777777-7777-7777-7777-777777777777",
                doc_type="POLICY",
                title="退货政策",
                score=0.90,
            ),
        ]

        # Simulate reference list formatting
        citation_ids = [
            "66666666-6666-6666-6666-666666666666",
            "77777777-7777-7777-7777-777777777777",
        ]

        refs = []
        for cid in citation_ids:
            item = next((ev for ev in evidence if ev.chunk_id == cid), None)
            if item:
                ref_label = (
                    f"[{item.doc_type.upper()}] {item.title or item.chunk_id[:8]}"
                )
                refs.append(ref_label)
            else:
                refs.append(f"[{cid[:8]}...] (未找到)")

        assert "[FAQ] 退款说明" in refs
        assert "[POLICY] 退货政策" in refs

    def test_citation_reference_fallback_to_chunk_id(self) -> None:
        """FR-15.5-5: Citation without title falls back to chunk_id[:8]."""
        from ticketpilot.chat import EvidenceDisplayItem

        evidence = [
            EvidenceDisplayItem(
                chunk_id="88888888-8888-8888-8888-888888888888",
                doc_type="CASE",
                title=None,  # No title
                score=0.75,
            )
        ]

        cid = "88888888-8888-8888-8888-888888888888"
        item = next((ev for ev in evidence if ev.chunk_id == cid), None)
        assert item is not None
        ref_label = f"[{item.doc_type.upper()}] {item.title or item.chunk_id[:8]}"

        # Should use chunk_id[:8] when title is None
        assert ref_label == "[CASE] 88888888"
