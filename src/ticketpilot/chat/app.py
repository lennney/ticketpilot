"""Streamlit chat demo for TicketPilot AI customer service copilot.

This is a UI skeleton for Phase 15.2. Pipeline integration comes in Phase 15.3.
No real provider calls, no database, no auto-send.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import streamlit as st

from ticketpilot.chat import (
    ChatContext,
    ChatDisplay,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatState,
    append_message,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="TicketPilot AI 客服 Copilot",
    page_icon="💬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Boundary notice
# ---------------------------------------------------------------------------

BOUNDARY_BANNER = """
**TicketPilot AI 客服 Copilot — Local Demo / Portfolio Prototype**

- 本演示使用合成数据，不代表生产系统
- Synthetic data only — no real customer data
- No auto-send — drafts are for demo review only
- Human-in-the-loop for high-risk cases
- Not a production-ready system
"""

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialize session state for chat session and context."""
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = ChatSession(
            session_id=str(uuid.uuid4()),
            messages=[],
            state=ChatState.IDLE,
            context=ChatContext(),
        )


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


def _render_boundary_banner() -> None:
    """Render the boundary/explanation banner."""
    st.info(BOUNDARY_BANNER)


def _render_header() -> None:
    """Render the page header."""
    st.title("💬 TicketPilot AI 客服 Copilot")
    st.caption("Local Demo · Synthetic Data · No Auto-Send")


def _render_chat_history(messages: list[ChatMessage]) -> None:
    """Render the chat message history."""
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


def _render_context_panel(ctx: ChatContext) -> None:
    """Render the conversation context panel."""
    st.subheader("📋 当前上下文")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**当前订单号**")
        st.text(
            ctx.current_order_id if ctx.current_order_id else "暂无",
            disabled=True,
        )
        st.markdown("**当前问题类型**")
        st.text(
            ctx.current_issue_type if ctx.current_issue_type else "暂无",
            disabled=True,
        )
        st.markdown("**当前产品**")
        st.text(
            ctx.current_product_name if ctx.current_product_name else "暂无",
            disabled=True,
        )

    with col2:
        st.markdown("**风险等级**")
        severity_text = ctx.latest_severity if ctx.latest_severity else "暂无"
        severity_color = ""
        if severity_text == "HIGH":
            severity_color = "🔴 HIGH"
        elif severity_text == "MEDIUM":
            severity_color = "🟡 MEDIUM"
        elif severity_text == "LOW":
            severity_color = "🟢 LOW"
        st.text(
            severity_color or severity_text,
            disabled=True,
        )
        st.markdown("**风险标记**")
        if ctx.latest_risk_flags:
            for flag in ctx.latest_risk_flags:
                st.text(f"• {flag}", disabled=True)
        else:
            st.text("暂无", disabled=True)
        st.markdown("**对话轮数**")
        st.text(str(ctx.turn_count), disabled=True)


def _render_risk_panel(display: ChatDisplay | None) -> None:
    """Render the risk status panel."""
    st.subheader("⚠️ 风险状态")

    if display is None:
        st.info("等待 Phase 15.3 pipeline 接入...")
        return

    if display.risk_badge:
        badge_color = {
            "HIGH": "🔴 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "🟢 LOW",
        }.get(display.risk_badge, display.risk_badge)
        st.metric("风险等级", badge_color)

    if display.risk_flags:
        st.markdown("**风险标记**:")
        for flag in display.risk_flags:
            st.markdown(f"- `{flag}`")
    else:
        st.info("暂无风险评估")

    st.divider()

    # Human review status
    if display.human_review_required:
        st.error("🚨 需要人工审核")
        if display.escalation_reason:
            st.markdown(f"*原因*: {display.escalation_reason}")
    else:
        st.success("✅ 无需人工审核")


def _render_evidence_panel(display: ChatDisplay | None) -> None:
    """Render the evidence panel."""
    st.subheader("📚 证据面板")

    if display is None or not display.evidence_panel:
        st.info("暂无证据 — 等待 Phase 15.3 pipeline 接入")
        return

    for item in display.evidence_panel:
        with st.expander(f"`{item.chunk_id[:8]}...` · {item.doc_type}"):
            if item.title:
                st.markdown(f"**{item.title}**")
            if item.score is not None:
                st.caption(f"相关度: {item.score:.3f}")
            if item.content_preview:
                st.markdown(item.content_preview)


def _render_draft_panel(display: ChatDisplay | None) -> None:
    """Render the AI draft panel."""
    st.subheader("📝 AI 客服回复草稿")

    if display is None:
        st.info("暂无草稿 — 等待 Phase 15.3 pipeline 接入")
        return

    if display.draft_text:
        st.markdown(display.draft_text)

        st.divider()

        # Guard status
        if display.guard_passed is True:
            st.success("✅ Guard Passed")
        elif display.guard_passed is False:
            st.error("❌ Guard Failed")
            if display.failure_reasons:
                st.markdown("**失败原因**:")
                for reason in display.failure_reasons:
                    st.markdown(f"- `{reason}`")

        # Citation IDs
        if display.citation_ids:
            st.markdown("**引用证据**:")
            for cid in display.citation_ids:
                st.markdown(f"- `[{cid[:8]}...]`")
    else:
        st.info("暂无草稿 — 等待 Phase 15.3 pipeline 接入")


def _render_human_review_panel(session: ChatSession) -> None:
    """Render the human review action panel."""
    st.subheader("🛡️ 人工审核")

    if session.human_review_required or session.context.human_review_required:
        st.warning(
            "此工单需要人工审核。\n\n"
            "Phase 15.6 将接入人工审核控制台。"
        )
        st.button(
            "🔍 进行人工审核",
            disabled=True,
            help="Phase 15.6 接入后可用",
        )
    else:
        st.success("无需人工审核")


def _render_chat_input(session: ChatSession) -> ChatMessage | None:
    """Render chat input and return a new user message if submitted.

    Returns None if no new message was submitted.
    """
    placeholder = "输入您的问题... (e.g., 我要退款，订单号12345)"

    user_input = st.chat_input(placeholder)

    if not user_input:
        return None

    user_input = user_input.strip()
    if not user_input:
        return None

    # Transition to processing
    if session.state == ChatState.IDLE:
        session.state = ChatState.PROCESSING

    new_message = ChatMessage(
        role=ChatRole.USER,
        text=user_input,
        timestamp=datetime.now(timezone.utc),
        metadata={"turn_id": session.context.turn_count + 1},
    )

    return new_message


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the TicketPilot AI 客服 Copilot chat demo."""
    _init_session_state()

    _render_boundary_banner()
    _render_header()

    session = st.session_state.chat_session

    # Two-column layout
    left_col, right_col = st.columns([3, 2])

    with left_col:
        # Chat history
        _render_chat_history(session.messages)

        # AI placeholder response after user submits
        # (Phase 15.3 will replace this with real pipeline)
        if session.messages and session.messages[-1].role == ChatRole.USER:
            with st.chat_message("assistant"):
                st.markdown(
                    "已收到您的消息。\n\n"
                    "**Phase 15.3 将接入 pipeline 分析意图、风险和证据。**\n\n"
                    "目前处于 UI skeleton 阶段，暂无真实回复生成。"
                )

    with right_col:
        # Top: context panel
        _render_context_panel(session.context)

        st.divider()

        # Risk status
        _render_risk_panel(session.display)

        st.divider()

        # Human review
        _render_human_review_panel(session)

    # Full-width panels below chat
    st.divider()

    col_ev, col_draft = st.columns(2)

    with col_ev:
        _render_evidence_panel(session.display)

    with col_draft:
        _render_draft_panel(session.display)

    # Handle new input
    new_msg = _render_chat_input(session)

    if new_msg:
        # Append message and transition state
        st.session_state.chat_session = append_message(session, new_msg)
        # Show processing state
        st.session_state.chat_session.state = ChatState.PROCESSING
        st.rerun()


if __name__ == "__main__":
    main()
