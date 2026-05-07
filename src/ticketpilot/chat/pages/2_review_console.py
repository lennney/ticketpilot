"""Streamlit multipage review console for TicketPilot chat.

This page is accessed when a reviewer clicks "进行人工审核" from the chat app.
It displays the full chat context and allows the reviewer to approve/edit/escalate/reject.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from ticketpilot.chat import ChatMessage, ChatRole, ReviewDecisionDisplay

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="TicketPilot 审核控制台", layout="wide")

# ---------------------------------------------------------------------------
# Risk flag labels
# ---------------------------------------------------------------------------

RISK_FLAG_LABELS: dict[str, str] = {
    "complaint_risk": "投诉风险",
    "compensation_risk": "补偿风险",
    "legal_risk": "法律风险",
    "privacy_risk": "隐私风险",
    "account_security_risk": "账户安全风险",
    "policy_conflict": "政策冲突",
    "insufficient_evidence": "证据不足",
    "low_confidence": "置信度低",
}

RISK_BADGE_COLORS: dict[str, tuple[str, str]] = {
    "HIGH": ("#dc2626", "#fef2f2"),
    "MEDIUM": ("#d97706", "#fffbeb"),
    "LOW": ("#16a34a", "#f0fdf4"),
}


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


def _render_chat_history(messages: list[ChatMessage]) -> None:
    """Render the chat message history."""
    st.subheader("💬 对话历史")

    if not messages:
        st.info("暂无对话历史")
        return

    for msg in messages:
        if msg.role == ChatRole.USER:
            with st.chat_message("user"):
                st.markdown(f"**用户**: {msg.text}")
        elif msg.role == ChatRole.AI:
            with st.chat_message("assistant"):
                st.markdown(f"**AI 客服**: {msg.text}")
        elif msg.role == ChatRole.SYSTEM:
            st.markdown(f"*{msg.text}*")
        st.divider()


def _render_review_panels(session) -> None:
    """Render draft, risk, and evidence panels from session.display."""
    display = getattr(session, "display", None)

    if not display:
        st.info("暂无展示数据")
        return

    # Risk panel
    st.subheader("⚠️ 风险状态")
    if display.risk_badge:
        text_color, bg_color = RISK_BADGE_COLORS.get(
            display.risk_badge, ("#666666", "#f5f5f5")
        )
        badge_html = (
            f"<span style='background-color:{bg_color};color:{text_color};"
            f"padding:4px 12px;border-radius:4px;font-weight:bold;'>"
            f"风险等级: {display.risk_badge}</span>"
        )
        st.markdown(badge_html, unsafe_allow_html=True)

    if display.risk_flags:
        st.markdown("**风险标记**:")
        for flag in display.risk_flags:
            label = RISK_FLAG_LABELS.get(flag, flag)
            st.markdown(f"- {label}")
    else:
        st.info("暂无风险评估")

    if display.human_review_required:
        if display.risk_badge == "HIGH":
            st.error("需要人工审核 - 高风险工单")
        else:
            st.warning("需要人工审核")
        if display.escalation_reason:
            st.markdown(f"*原因*: {display.escalation_reason}")
    else:
        st.success("无需人工审核")

    st.divider()

    # Draft panel
    st.subheader("📝 AI 客服回复草稿")
    if display.draft_text:
        st.text_area(
            "草稿文本",
            display.draft_text,
            height=200,
            disabled=True,
            key="review_draft_text",
        )

        # Guard status
        if display.guard_passed is True:
            st.success("✅ Guard Passed")
        elif display.guard_passed is False:
            st.error("❌ Guard Failed")
            if display.failure_reasons:
                st.markdown("**失败原因**:")
                for reason in display.failure_reasons:
                    st.markdown(f"- `{reason}`")

        # Citations
        if display.citation_ids:
            st.markdown("**引用证据**:")
            for cid in display.citation_ids:
                item = next(
                    (ev for ev in display.evidence_panel if ev.chunk_id == cid),
                    None,
                )
                if item:
                    ref_label = (
                        f"[{item.doc_type.upper()}] {item.title or item.chunk_id[:8]}"
                    )
                    with st.expander(ref_label):
                        if item.content_preview:
                            st.markdown(item.content_preview)
                        st.caption(f"完整 chunk_id: `{cid}`")
    else:
        st.info("暂无草稿文本")

    st.divider()

    # Evidence panel
    st.subheader("📚 证据面板")
    if display.evidence_panel:
        for item in display.evidence_panel:
            with st.expander(
                f"`{item.chunk_id[:8]}...` · {item.title or item.doc_type}"
            ):
                if item.title:
                    st.markdown(f"**{item.title}**")
                if item.score is not None:
                    st.caption(f"相关度: {item.score:.3f}")
                if item.content_preview:
                    st.markdown(item.content_preview)
    else:
        st.info("暂无证据")


def _render_action_buttons() -> str | None:
    """Render review action buttons and return the selected action.

    Returns:
        The action string ("approve", "edit", "escalate", "reject") or None.
    """
    st.subheader("📋 审核操作")

    col1, col2 = st.columns(2)

    action: str | None = None

    with col1:
        if st.button("✅ 批准", key="review_approve_btn", type="primary"):
            action = "approve"

        if st.button("✏️ 编辑", key="review_edit_btn"):
            st.session_state.show_edit = True

    with col2:
        if st.button("⬆️ 升级", key="review_escalate_btn"):
            st.session_state.show_escalate = True

        if st.button("❌ 拒绝", key="review_reject_btn"):
            st.session_state.show_reject = True

    # Edit section
    if st.session_state.get("show_edit"):
        st.markdown("**编辑草稿文本:**")
        edited = st.text_area(
            "edited_text",
            st.session_state.get("pending_review_session", {}).display.draft_text
            if st.session_state.get("pending_review_session")
            else "",
            height=150,
            key="edit_text_area",
        )
        if st.button("确认编辑", key="confirm_edit_btn"):
            if edited.strip():
                _submit_decision("edit", edited_text=edited)
            else:
                st.error("编辑后的文本不能为空")

    # Escalate section
    if st.session_state.get("show_escalate"):
        reason = st.text_input("升级原因", key="escalate_reason_input")
        if st.button("确认升级", key="confirm_escalate_btn"):
            if reason.strip():
                _submit_decision("escalate", decision_reason=reason)
            else:
                st.error("请输入升级原因")

    # Reject section
    if st.session_state.get("show_reject"):
        reason = st.text_input("拒绝原因", key="reject_reason_input")
        if st.button("确认拒绝", key="confirm_reject_btn"):
            if reason.strip():
                _submit_decision("reject", decision_reason=reason)
            else:
                st.error("请输入拒绝原因")

    return action


def _submit_decision(
    action: str,
    edited_text: str | None = None,
    decision_reason: str = "",
) -> None:
    """Submit the review decision and return to chat.

    Args:
        action: The review action ("approve", "edit", "escalate", "reject")
        edited_text: Edited draft text (for "edit" action)
        decision_reason: Reason for escalation/rejection
    """
    decision = ReviewDecisionDisplay(
        action=action,
        edited_text=edited_text,
        decision_reason=decision_reason,
        reviewed_at=datetime.now(timezone.utc),
    )

    st.session_state.last_review_decision = decision
    st.session_state.pending_review_session = None
    st.query_params["page"] = ""
    st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the review console page."""
    st.title("TicketPilot 审核控制台")
    st.caption("人工审核 - 不自动发送回复")

    pending_session = st.session_state.get("pending_review_session")

    if not pending_session:
        st.error("无待审核会话")
        st.info("请从聊天页面发起人工审核请求")
        return

    # Initialize session state flags
    if "show_edit" not in st.session_state:
        st.session_state.show_edit = False
    if "show_escalate" not in st.session_state:
        st.session_state.show_escalate = False
    if "show_reject" not in st.session_state:
        st.session_state.show_reject = False

    # 1. Render chat history
    _render_chat_history(pending_session.messages)

    # 2. Render draft, risk, evidence from session.display
    _render_review_panels(pending_session)

    # 3. Render action buttons
    action = _render_action_buttons()

    # Handle direct approve button click
    if action == "approve":
        _submit_decision("approve")


if __name__ == "__main__":
    main()
