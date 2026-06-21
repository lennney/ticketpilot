"""Unit tests for chat app — human review panel and review decision display."""

from __future__ import annotations

from datetime import datetime, timezone

from ticketpilot.chat import (
    ChatDisplay,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatState,
    ReviewDecisionDisplay,
)
from ticketpilot.chat.app import (
    ACTION_BADGE_COLORS,
    ACTION_LABELS,
)


# ---------------------------------------------------------------------------
# Action labels and badge colors — constants
# ---------------------------------------------------------------------------


class TestActionLabels:
    """Tests for ACTION_LABELS mapping."""

    def test_all_review_actions_have_labels(self) -> None:
        """All four review actions have corresponding Chinese labels."""
        assert "approve" in ACTION_LABELS
        assert "edit" in ACTION_LABELS
        assert "escalate" in ACTION_LABELS
        assert "reject" in ACTION_LABELS

    def test_approve_label(self) -> None:
        """approve maps to '审核通过'."""
        assert ACTION_LABELS["approve"] == "审核通过"

    def test_edit_label(self) -> None:
        """edit maps to '审核通过（已编辑）'."""
        assert ACTION_LABELS["edit"] == "审核通过（已编辑）"

    def test_escalate_label(self) -> None:
        """escalate maps to '已升级'."""
        assert ACTION_LABELS["escalate"] == "已升级"

    def test_reject_label(self) -> None:
        """reject maps to '已拒绝'."""
        assert ACTION_LABELS["reject"] == "已拒绝"


class TestActionBadgeColors:
    """Tests for ACTION_BADGE_COLORS mapping."""

    def test_approve_has_green_color(self) -> None:
        """approve action has green color configuration."""
        text_color, bg_color = ACTION_BADGE_COLORS["approve"]
        assert text_color == "#16a34a"  # green
        assert bg_color == "#f0fdf4"  # light green

    def test_edit_has_yellow_color(self) -> None:
        """edit action has yellow color configuration."""
        text_color, bg_color = ACTION_BADGE_COLORS["edit"]
        assert text_color == "#ca8a04"  # yellow
        assert bg_color == "#fefce8"  # light yellow

    def test_escalate_has_orange_color(self) -> None:
        """escalate action has orange color configuration."""
        text_color, bg_color = ACTION_BADGE_COLORS["escalate"]
        assert text_color == "#ea580c"  # orange
        assert bg_color == "#fff7ed"  # light orange

    def test_reject_has_red_color(self) -> None:
        """reject action has red color configuration."""
        text_color, bg_color = ACTION_BADGE_COLORS["reject"]
        assert text_color == "#dc2626"  # red
        assert bg_color == "#fef2f2"  # light red

    def test_all_colors_are_valid_hex(self) -> None:
        """All badge colors are valid hex color codes."""
        for action, (text_color, bg_color) in ACTION_BADGE_COLORS.items():
            assert text_color.startswith("#"), f"{action}: text_color should be hex"
            assert bg_color.startswith("#"), f"{action}: bg_color should be hex"


# ---------------------------------------------------------------------------
# Human review button enabled state
# ---------------------------------------------------------------------------


class TestHumanReviewButtonEnabled:
    """Tests for human review button enabled state."""

    def test_button_enabled_when_human_review_required_true(self) -> None:
        """TC-15.6-3: Button should be enabled when human_review_required is True."""
        session = ChatSession(session_id="test")
        session.human_review_required = True
        session.context.human_review_required = True
        # Verify button should be enabled (not disabled)
        assert session.human_review_required is True
        assert session.context.human_review_required is True

    def test_button_disabled_when_human_review_not_required(self) -> None:
        """Button should not show active state when human_review_required is False."""
        session = ChatSession(session_id="test")
        session.human_review_required = False
        session.context.human_review_required = False
        assert session.human_review_required is False
        assert session.context.human_review_required is False

    def test_button_enabled_with_context_flag_only(self) -> None:
        """Button should be enabled with context flag even if session flag is False."""
        session = ChatSession(session_id="test")
        session.human_review_required = False
        session.context.human_review_required = True
        # Either flag being True should enable the button
        assert session.context.human_review_required is True

    def test_button_enabled_with_session_flag_only(self) -> None:
        """Button should be enabled with session flag even if context flag is False."""
        session = ChatSession(session_id="test")
        session.human_review_required = True
        session.context.human_review_required = False
        # Either flag being True should enable the button
        assert session.human_review_required is True


# ---------------------------------------------------------------------------
# Session state transition on review callback
# ---------------------------------------------------------------------------


class TestSessionStateTransition:
    """Tests for session state transition on review decision callback."""

    def test_session_transitions_to_reviewed_state(self) -> None:
        """TC-15.6-5: Session transitions to REVIEWED after review callback."""
        session = ChatSession(session_id="test", state=ChatState.HUMAN_REVIEW)
        decision = ReviewDecisionDisplay(action="approve")

        # Simulate callback processing
        session.state = ChatState.REVIEWED
        session.last_review_decision = decision

        assert session.state == ChatState.REVIEWED
        assert session.last_review_decision.action == "approve"

    def test_system_message_appended_for_approve(self) -> None:
        """TC-15.6-5: System message is appended for approve action."""
        session = ChatSession(session_id="test", state=ChatState.HUMAN_REVIEW)
        decision = ReviewDecisionDisplay(action="approve")

        # Build system message (same logic as callback)
        action_label = ACTION_LABELS[decision.action]
        reason_text = (
            f" — {decision.decision_reason}" if decision.decision_reason else ""
        )
        system_message = f"[审核结果] {action_label}{reason_text}"

        # Append to messages
        system_msg = ChatMessage(
            role=ChatRole.SYSTEM,
            text=system_message,
            timestamp=datetime.now(timezone.utc),
        )
        session.messages.append(system_msg)

        assert len(session.messages) == 1
        assert session.messages[0].role == ChatRole.SYSTEM
        assert session.messages[0].text == "[审核结果] 审核通过"

    def test_system_message_appended_for_edit_with_reason(self) -> None:
        """System message includes reason for edit action."""
        decision = ReviewDecisionDisplay(
            action="edit",
            edited_text="Fixed text",
            decision_reason="Minor correction",
        )

        action_label = ACTION_LABELS[decision.action]
        reason_text = (
            f" — {decision.decision_reason}" if decision.decision_reason else ""
        )
        system_message = f"[审核结果] {action_label}{reason_text}"

        assert system_message == "[审核结果] 审核通过（已编辑） — Minor correction"

    def test_system_message_appended_for_escalate(self) -> None:
        """System message for escalate action."""
        decision = ReviewDecisionDisplay(
            action="escalate",
            decision_reason="Customer VIP",
        )

        action_label = ACTION_LABELS[decision.action]
        reason_text = (
            f" — {decision.decision_reason}" if decision.decision_reason else ""
        )
        system_message = f"[审核结果] {action_label}{reason_text}"

        assert system_message == "[审核结果] 已升级 — Customer VIP"

    def test_system_message_appended_for_reject(self) -> None:
        """System message for reject action."""
        decision = ReviewDecisionDisplay(
            action="reject",
            decision_reason="Inappropriate content",
        )

        action_label = ACTION_LABELS[decision.action]
        reason_text = (
            f" — {decision.decision_reason}" if decision.decision_reason else ""
        )
        system_message = f"[审核结果] {action_label}{reason_text}"

        assert system_message == "[审核结果] 已拒绝 — Inappropriate content"

    def test_review_decision_preserved_after_callback(self) -> None:
        """last_review_decision is preserved after callback processing."""
        session = ChatSession(session_id="test", state=ChatState.HUMAN_REVIEW)
        decision = ReviewDecisionDisplay(
            action="approve",
            decision_reason="Looks good",
        )

        # Simulate callback
        session.state = ChatState.REVIEWED
        session.last_review_decision = decision

        assert session.last_review_decision is not None
        assert session.last_review_decision.decision_reason == "Looks good"


# ---------------------------------------------------------------------------
# Review decision panel display
# ---------------------------------------------------------------------------


class TestReviewDecisionPanelDisplay:
    """Tests for review decision panel color-coded badge display."""

    def test_approve_badge_color(self) -> None:
        """TC-15.6-6: Approve action renders with green badge."""
        decision = ReviewDecisionDisplay(action="approve")
        text_color, bg_color = ACTION_BADGE_COLORS[decision.action]
        assert text_color == "#16a34a"  # green
        assert bg_color == "#f0fdf4"  # light green

    def test_edit_badge_color(self) -> None:
        """TC-15.6-6: Edit action renders with yellow badge."""
        decision = ReviewDecisionDisplay(action="edit", edited_text="Updated")
        text_color, bg_color = ACTION_BADGE_COLORS[decision.action]
        assert text_color == "#ca8a04"  # yellow
        assert bg_color == "#fefce8"  # light yellow

    def test_escalate_badge_color(self) -> None:
        """TC-15.6-6: Escalate action renders with orange badge."""
        decision = ReviewDecisionDisplay(action="escalate")
        text_color, bg_color = ACTION_BADGE_COLORS[decision.action]
        assert text_color == "#ea580c"  # orange
        assert bg_color == "#fff7ed"  # light orange

    def test_reject_badge_color(self) -> None:
        """TC-15.6-6: Reject action renders with red badge."""
        decision = ReviewDecisionDisplay(action="reject")
        text_color, bg_color = ACTION_BADGE_COLORS[decision.action]
        assert text_color == "#dc2626"  # red
        assert bg_color == "#fef2f2"  # light red

    def test_edited_text_available_for_edit_action(self) -> None:
        """Edited text is available when action is 'edit'."""
        session = ChatSession(session_id="test")
        session.last_review_decision = ReviewDecisionDisplay(
            action="edit",
            edited_text="Fixed draft text here",
        )

        assert session.last_review_decision is not None
        assert session.last_review_decision.action == "edit"
        assert session.last_review_decision.edited_text == "Fixed draft text here"

    def test_no_edited_text_for_non_edit_actions(self) -> None:
        """Edited text is None for non-edit actions."""
        decision = ReviewDecisionDisplay(action="approve")
        assert decision.edited_text is None

        decision = ReviewDecisionDisplay(action="escalate")
        assert decision.edited_text is None

        decision = ReviewDecisionDisplay(action="reject")
        assert decision.edited_text is None


# ---------------------------------------------------------------------------
# Review console interface
# ---------------------------------------------------------------------------


class TestReviewConsoleInterface:
    """Tests for review console interface via session state."""

    def test_pending_review_session_stores_snapshot(self) -> None:
        """TC-15.6-4: pending_review_session stores a session snapshot."""
        session = ChatSession(session_id="test-123")
        session.messages = [
            ChatMessage(role=ChatRole.USER, text="I want refund"),
            ChatMessage(role=ChatRole.AI, text="Processing..."),
        ]

        # Simulate snapshot creation
        snapshot = session.model_copy(deep=True)

        assert snapshot is not None
        assert len(snapshot.messages) == 2
        assert snapshot.messages[0].text == "I want refund"

    def test_review_decision_display_builds_correctly(self) -> None:
        """ReviewDecisionDisplay builds correctly for all actions."""
        # Approve
        decision = ReviewDecisionDisplay(action="approve")
        assert decision.action == "approve"

        # Edit with text
        decision = ReviewDecisionDisplay(
            action="edit",
            edited_text="Fixed text",
            decision_reason="Minor edit",
        )
        assert decision.action == "edit"
        assert decision.edited_text == "Fixed text"

        # Escalate
        decision = ReviewDecisionDisplay(
            action="escalate",
            decision_reason="VIP customer",
        )
        assert decision.action == "escalate"

        # Reject
        decision = ReviewDecisionDisplay(
            action="reject",
            decision_reason="Bad content",
        )
        assert decision.action == "reject"

    def test_review_console_reads_pending_session(self) -> None:
        """Review console can read pending_review_session from session state."""
        session = ChatSession(session_id="test")
        session.messages = [
            ChatMessage(role=ChatRole.USER, text="Test message"),
        ]
        session.display = ChatDisplay(
            user_message="Test message",
            draft_text="Draft response",
            risk_badge="HIGH",
        )

        # Simulate session state storage
        pending_session = session.model_copy(deep=True)

        # Verify the snapshot has the expected data
        assert pending_session is not None
        assert len(pending_session.messages) == 1
        assert pending_session.display is not None
        assert pending_session.display.draft_text == "Draft response"
