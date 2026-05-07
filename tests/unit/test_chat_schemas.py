"""Unit tests for chat schemas — ChatSession, ChatContext, ChatMessage, and helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ticketpilot.chat import (
    ChatContext,
    ChatDisplay,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatState,
    EvidenceDisplayItem,
    append_message,
    update_context_from_message,
)


# ---------------------------------------------------------------------------
# ChatState
# ---------------------------------------------------------------------------


class TestChatState:
    """ChatState enum values."""

    def test_all_states_exist(self) -> None:
        assert ChatState.IDLE.value == "IDLE"
        assert ChatState.PROCESSING.value == "PROCESSING"
        assert ChatState.DRAFT_READY.value == "DRAFT_READY"
        assert ChatState.HUMAN_REVIEW.value == "HUMAN_REVIEW"
        assert ChatState.REVIEWED.value == "REVIEWED"


# ---------------------------------------------------------------------------
# ChatRole
# ---------------------------------------------------------------------------


class TestChatRole:
    """ChatRole enum values."""

    def test_all_roles_exist(self) -> None:
        assert ChatRole.USER.value == "user"
        assert ChatRole.AI.value == "ai"
        assert ChatRole.SYSTEM.value == "system"


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------


class TestChatMessage:
    """ChatMessage creation and validation."""

    def test_accepts_valid_user_message(self) -> None:
        msg = ChatMessage(role=ChatRole.USER, text="我要退款，订单号12345")
        assert msg.role == ChatRole.USER
        assert msg.text == "我要退款，订单号12345"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}

    def test_accepts_ai_message(self) -> None:
        msg = ChatMessage(role=ChatRole.AI, text="您好，请问有什么可以帮您？")
        assert msg.role == ChatRole.AI

    def test_accepts_system_message(self) -> None:
        msg = ChatMessage(role=ChatRole.SYSTEM, text="Session started")
        assert msg.role == ChatRole.SYSTEM

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, text="")

    def test_rejects_whitespace_only_text(self) -> None:
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, text="   ")

    def test_rejects_empty_string_variation(self) -> None:
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, text="\t\n")

    def test_metadata_default_is_independent_per_instance(self) -> None:
        msg1 = ChatMessage(role=ChatRole.USER, text="message 1")
        msg2 = ChatMessage(role=ChatRole.USER, text="message 2")
        msg1.metadata["key"] = "value"
        assert msg2.metadata == {}

    def test_accepts_metadata(self) -> None:
        meta = {
            "turn_id": 1,
            "detected_order_id": "12345",
            "issue_type": "refund",
            "risk_flags": ["COMPENSATION_RISK"],
            "severity": "HIGH",
        }
        msg = ChatMessage(role=ChatRole.USER, text="test", metadata=meta)
        assert msg.metadata["detected_order_id"] == "12345"
        assert msg.metadata["risk_flags"] == ["COMPENSATION_RISK"]

    def test_timestamp_defaults_to_utc_now(self) -> None:
        before = datetime.now(timezone.utc)
        msg = ChatMessage(role=ChatRole.USER, text="hello")
        after = datetime.now(timezone.utc)
        assert before <= msg.timestamp <= after

    def test_accepts_custom_timestamp(self) -> None:
        ts = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
        msg = ChatMessage(role=ChatRole.USER, text="hello", timestamp=ts)
        assert msg.timestamp == ts

    def test_model_dump_includes_all_fields(self) -> None:
        msg = ChatMessage(role=ChatRole.USER, text="hello", metadata={"key": "val"})
        d = msg.model_dump()
        assert d["role"] == "user"
        assert d["text"] == "hello"
        assert d["metadata"] == {"key": "val"}
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# ChatContext
# ---------------------------------------------------------------------------


class TestChatContext:
    """ChatContext default values and field behavior."""

    def test_default_fields_are_empty_or_false(self) -> None:
        ctx = ChatContext()
        assert ctx.current_issue_type is None
        assert ctx.current_order_id is None
        assert ctx.current_product_name is None
        assert ctx.latest_risk_flags == []
        assert ctx.latest_severity is None
        assert ctx.latest_evidence_ids == []
        assert ctx.latest_citation_ids == []
        assert ctx.latest_guard_passed is None
        assert ctx.human_review_required is False
        assert ctx.handoff_reason is None
        assert ctx.turn_count == 0

    def test_latest_risk_flags_default_list_is_independent(self) -> None:
        ctx1 = ChatContext()
        ctx2 = ChatContext()
        ctx1.latest_risk_flags.append("COMPENSATION_RISK")
        assert ctx2.latest_risk_flags == []

    def test_turn_count_starts_at_zero(self) -> None:
        ctx = ChatContext()
        assert ctx.turn_count == 0

    def test_accepts_populated_context(self) -> None:
        ctx = ChatContext(
            current_order_id="12345",
            current_issue_type="refund",
            latest_risk_flags=["COMPENSATION_RISK"],
            latest_severity="HIGH",
            human_review_required=True,
            handoff_reason="compensation_risk detected",
            turn_count=3,
        )
        assert ctx.current_order_id == "12345"
        assert ctx.current_issue_type == "refund"
        assert ctx.latest_risk_flags == ["COMPENSATION_RISK"]
        assert ctx.latest_severity == "HIGH"
        assert ctx.human_review_required is True
        assert ctx.handoff_reason == "compensation_risk detected"
        assert ctx.turn_count == 3


# ---------------------------------------------------------------------------
# EvidenceDisplayItem
# ---------------------------------------------------------------------------


class TestEvidenceDisplayItem:
    """EvidenceDisplayItem validation."""

    def test_accepts_required_fields(self) -> None:
        item = EvidenceDisplayItem(chunk_id="abc-123", doc_type="Policy")
        assert item.chunk_id == "abc-123"
        assert item.doc_type == "Policy"

    def test_accepts_optional_fields(self) -> None:
        item = EvidenceDisplayItem(
            chunk_id="abc-123",
            doc_type="Policy",
            title="退货政策",
            score=0.95,
            content_preview="7天内可申请退货...",
        )
        assert item.title == "退货政策"
        assert item.score == 0.95
        assert item.content_preview == "7天内可申请退货..."

    def test_rejects_empty_chunk_id(self) -> None:
        with pytest.raises(ValidationError):
            EvidenceDisplayItem(chunk_id="", doc_type="Policy")

    def test_rejects_whitespace_chunk_id(self) -> None:
        with pytest.raises(ValidationError):
            EvidenceDisplayItem(chunk_id="   ", doc_type="Policy")

    def test_doc_type_cannot_be_empty_string(self) -> None:
        with pytest.raises(ValidationError):
            EvidenceDisplayItem(chunk_id="abc-123", doc_type="")

    def test_score_is_optional(self) -> None:
        item = EvidenceDisplayItem(chunk_id="abc", doc_type="FAQ")
        assert item.score is None

    def test_model_dump_includes_all_fields(self) -> None:
        item = EvidenceDisplayItem(
            chunk_id="abc",
            doc_type="Case",
            title="案例",
            score=0.88,
            content_preview="...",
        )
        d = item.model_dump()
        assert d["chunk_id"] == "abc"
        assert d["doc_type"] == "Case"
        assert d["title"] == "案例"
        assert d["score"] == 0.88


# ---------------------------------------------------------------------------
# ChatDisplay
# ---------------------------------------------------------------------------


class TestChatDisplay:
    """ChatDisplay default values."""

    def test_default_lists_are_independent(self) -> None:
        d1 = ChatDisplay()
        d2 = ChatDisplay()
        d1.risk_flags.append("LEGAL_RISK")
        assert d2.risk_flags == []

    def test_default_human_review_required_is_false(self) -> None:
        d = ChatDisplay()
        assert d.human_review_required is False

    def test_accepts_populated_display(self) -> None:
        from ticketpilot.chat import EvidenceDisplayItem

        ev = EvidenceDisplayItem(chunk_id="ev-1", doc_type="Policy")
        d = ChatDisplay(
            user_message="我要退款",
            ai_message="根据政策可以退款",
            risk_badge="LOW",
            risk_flags=["COMPENSATION_RISK"],
            evidence_panel=[ev],
            draft_text="尊敬的用户，根据政策[{ev-1}]，可以办理退货。",
            guard_passed=True,
            failure_reasons=[],
            human_review_required=False,
            citation_ids=["ev-1"],
        )
        assert d.user_message == "我要退款"
        assert d.ai_message == "根据政策可以退款"
        assert d.risk_badge == "LOW"
        assert len(d.evidence_panel) == 1
        assert d.guard_passed is True


# ---------------------------------------------------------------------------
# ChatSession
# ---------------------------------------------------------------------------


class TestChatSession:
    """ChatSession creation and multi-turn behavior."""

    def test_rejects_empty_session_id(self) -> None:
        with pytest.raises(ValidationError):
            ChatSession(session_id="")

    def test_rejects_whitespace_session_id(self) -> None:
        with pytest.raises(ValidationError):
            ChatSession(session_id="   ")

    def test_default_state_is_idle(self) -> None:
        session = ChatSession(session_id="sess-1")
        assert session.state == ChatState.IDLE

    def test_default_messages_is_empty_independent_list(self) -> None:
        s1 = ChatSession(session_id="s1")
        s2 = ChatSession(session_id="s2")
        msg = ChatMessage(role=ChatRole.USER, text="hello")
        s1.messages.append(msg)
        assert s2.messages == []

    def test_default_context_is_independent(self) -> None:
        s1 = ChatSession(session_id="s1")
        s2 = ChatSession(session_id="s2")
        s1.context.current_order_id = "12345"
        assert s2.context.current_order_id is None

    def test_can_hold_multiple_messages(self) -> None:
        session = ChatSession(session_id="sess-1")
        msg1 = ChatMessage(role=ChatRole.USER, text="我要退款")
        msg2 = ChatMessage(role=ChatRole.AI, text="好的，请问订单号是？")
        msg3 = ChatMessage(role=ChatRole.USER, text="12345")
        session.messages.extend([msg1, msg2, msg3])
        assert len(session.messages) == 3
        assert session.messages[0].text == "我要退款"
        assert session.messages[2].text == "12345"


# ---------------------------------------------------------------------------
# append_message helper
# ---------------------------------------------------------------------------


class TestAppendMessage:
    """append_message() pure function behavior."""

    def test_appends_message(self) -> None:
        session = ChatSession(session_id="s1")
        msg = ChatMessage(role=ChatRole.USER, text="hello")
        new_session = append_message(session, msg)
        assert len(new_session.messages) == 1
        assert new_session.messages[0].text == "hello"

    def test_does_not_mutate_original_session(self) -> None:
        session = ChatSession(session_id="s1")
        msg = ChatMessage(role=ChatRole.USER, text="hello")
        new_session = append_message(session, msg)
        assert len(session.messages) == 0
        assert len(new_session.messages) == 1

    def test_increments_turn_count_for_user_message(self) -> None:
        session = ChatSession(session_id="s1", context=ChatContext(turn_count=0))
        msg = ChatMessage(role=ChatRole.USER, text="hello")
        new_session = append_message(session, msg)
        assert new_session.context.turn_count == 1

    def test_does_not_increment_turn_count_for_ai_message(self) -> None:
        session = ChatSession(session_id="s1", context=ChatContext(turn_count=2))
        msg = ChatMessage(role=ChatRole.AI, text="how can I help?")
        new_session = append_message(session, msg)
        assert new_session.context.turn_count == 2

    def test_does_not_increment_turn_count_for_system_message(self) -> None:
        session = ChatSession(session_id="s1", context=ChatContext(turn_count=1))
        msg = ChatMessage(role=ChatRole.SYSTEM, text="Session started")
        new_session = append_message(session, msg)
        assert new_session.context.turn_count == 1

    def test_preserves_context_on_append(self) -> None:
        ctx = ChatContext(
            current_order_id="12345",
            current_issue_type="refund",
            turn_count=1,
        )
        session = ChatSession(session_id="s1", context=ctx)
        msg = ChatMessage(role=ChatRole.USER, text="ok")
        new_session = append_message(session, msg)
        assert new_session.context.current_order_id == "12345"
        assert new_session.context.current_issue_type == "refund"
        assert new_session.context.turn_count == 2  # incremented


# ---------------------------------------------------------------------------
# update_context_from_message helper
# ---------------------------------------------------------------------------


class TestUpdateContextFromMessage:
    """update_context_from_message() updates context from message metadata."""

    def test_updates_current_order_id(self) -> None:
        ctx = ChatContext()
        msg = ChatMessage(
            role=ChatRole.USER,
            text="退款",
            metadata={"detected_order_id": "12345"},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.current_order_id == "12345"

    def test_updates_current_issue_type(self) -> None:
        ctx = ChatContext()
        msg = ChatMessage(
            role=ChatRole.USER,
            text="我要退款",
            metadata={"issue_type": "refund"},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.current_issue_type == "refund"

    def test_updates_latest_risk_flags(self) -> None:
        ctx = ChatContext()
        msg = ChatMessage(
            role=ChatRole.USER,
            text="我要赔偿",
            metadata={"risk_flags": ["COMPENSATION_RISK"]},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert "COMPENSATION_RISK" in new_ctx.latest_risk_flags

    def test_merges_risk_flags_not_replaces(self) -> None:
        ctx = ChatContext(latest_risk_flags=["LEGAL_RISK"])
        msg = ChatMessage(
            role=ChatRole.USER,
            text="还有赔偿",
            metadata={"risk_flags": ["COMPENSATION_RISK"]},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert "LEGAL_RISK" in new_ctx.latest_risk_flags
        assert "COMPENSATION_RISK" in new_ctx.latest_risk_flags

    def test_sets_human_review_required_true(self) -> None:
        ctx = ChatContext()
        msg = ChatMessage(
            role=ChatRole.USER,
            text="退款",
            metadata={"human_review_required": True},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.human_review_required is True

    def test_human_review_required_stays_true_once_set(self) -> None:
        ctx = ChatContext(human_review_required=True)
        msg = ChatMessage(
            role=ChatRole.USER,
            text="谢谢",
            metadata={},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.human_review_required is True

    def test_short_followup_does_not_overwrite_order_id(self) -> None:
        ctx = ChatContext(current_order_id="12345")
        msg = ChatMessage(
            role=ChatRole.USER,
            text="谢谢",
            metadata={},  # No new order_id
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.current_order_id == "12345"

    def test_new_order_id_overwrites_previous(self) -> None:
        ctx = ChatContext(current_order_id="12345")
        msg = ChatMessage(
            role=ChatRole.USER,
            text="我要查另一个订单67890",
            metadata={"detected_order_id": "67890"},
        )
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.current_order_id == "67890"

    def test_empty_metadata_preserves_context(self) -> None:
        ctx = ChatContext(
            current_order_id="12345",
            current_issue_type="refund",
            latest_risk_flags=["LEGAL_RISK"],
            turn_count=2,
        )
        msg = ChatMessage(role=ChatRole.USER, text="好的", metadata={})
        new_ctx = update_context_from_message(ctx, msg)
        assert new_ctx.current_order_id == "12345"
        assert new_ctx.current_issue_type == "refund"
        assert new_ctx.latest_risk_flags == ["LEGAL_RISK"]
        assert new_ctx.turn_count == 2  # turn_count not updated by this func

    def test_model_dump_includes_context(self) -> None:
        session = ChatSession(
            session_id="s1",
            context=ChatContext(
                current_order_id="12345",
                turn_count=1,
            ),
        )
        d = session.model_dump()
        assert d["context"]["current_order_id"] == "12345"
        assert d["context"]["turn_count"] == 1

    def test_whitespace_message_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatMessage(role=ChatRole.USER, text="   ")
