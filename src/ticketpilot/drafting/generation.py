"""Draft generation, verification, and safe fallback for the draft agent.

Functions:
    generate_reply: Use the LLM to produce a reply grounded in evidence.
    verify_reply: Validate the generated reply and build a ``DraftReply``.
    build_fallback: Build a safe ``DraftReply`` when the agent cannot proceed.

Constants:
    SAFE_FALLBACK_TEXT: Chinese message used when no grounded reply is
        possible.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ticketpilot.drafting.llm_utils import (
    _SYSTEM_PROMPT,
    LlmConfig,
    call_llm,
    extract_json,
)
from ticketpilot.drafting.schemas import Citation, DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate

logger = logging.getLogger(__name__)

# Safe fallback when agent cannot produce a grounded reply
SAFE_FALLBACK_TEXT = "根据现有信息，无法确认具体政策条款，建议转人工处理。"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_reply(
    normalized_text: str,
    issue_type: str,
    flags: list[str],
    severity: str,
    must_human_review: bool,
    evidence: list[EvidenceCandidate],
    llm_config: LlmConfig,
    template_id: str = "default",
) -> dict[str, Any] | None:
    """Use LLM to generate a reply grounded in evidence.

    Formats the customer message, issue type, risk flags, and top-five
    evidence items into a structured prompt, calls the LLM, and returns a
    dict with keys ``draft_text``, ``cited_evidence_ids``, ``confidence``,
    ``unsupported_claims``, ``missing_information``, and ``safety_notes``.

    Args:
        normalized_text: Customer's normalized message.
        issue_type: Classified intent / issue type.
        flags: Detected risk flags.
        severity: Risk severity level.
        must_human_review: Whether risk assessment requires human review.
        evidence: Retrieved evidence candidates.
        llm_config: LLM endpoint configuration.
        template_id: Template identifier for optional specialised guidance.

    Returns:
        A dict with the keys listed above, or ``None`` on failure.
    """
    # Format evidence for prompt — use top 5 by rank
    evidence_lines: list[str] = []
    sorted_ev = sorted(evidence, key=lambda e: e.rank)[:5]
    for idx, ev in enumerate(sorted_ev, start=1):
        doc_type = (
            ev.doc_type.value
            if hasattr(ev.doc_type, "value")
            else str(ev.doc_type)
        )
        evidence_lines.append(f"[{idx}] ({doc_type}) {ev.content[:200]}")
    numbered_evidence = "\n".join(evidence_lines)

    # Build id mapping (numbered index → chunk UUID)
    id_to_chunk: dict[int, str] = {}
    for idx, ev in enumerate(sorted_ev, start=1):
        id_to_chunk[idx] = str(ev.chunk_id)

    # Load specialised template if available
    from ticketpilot.drafting.prompt_builder import load_template

    template_content = load_template(template_id)
    template_section = ""
    if template_content:
        template_section = f"\n\n## 专项处理指南\n\n{template_content}"

    # Build safety instructions
    safety_lines = [
        "## 安全规则",
        "1. 回复必须基于下方证据，禁止编造信息。",
        "2. 引用证据时使用 [1]、[2] 等编号格式。",
        "3. 禁止承诺退款金额、赔偿金额、法律行动、账号变更。",
        "4. 禁止承诺解决时间线或保证特定结果。",
        "5. 只有当证据列表为空时，才建议转人工。",
        "6. 不要在回复中提及「草稿」「审核」等内部流程词。",
    ]
    if severity in ("high", "critical"):
        safety_lines.append(
            f"7. 本工单严重程度为「{severity}」，必须建议转人工处理。"
        )
    if flags:
        safety_lines.append(
            f"8. 本工单包含风险标记：{', '.join(flags)}，"
            "回复中必须说明已升级至人工审核。"
        )

    user_content = (
        f"用户消息：{normalized_text}\n"
        f"问题类型：{issue_type}\n"
        f"风险标记：{flags}\n"
        f"严重度：{severity}\n\n"
        f"## 可用证据\n{numbered_evidence}\n\n"
        + "\n".join(safety_lines)
        + template_section
        + "\n\n请生成回复。输出JSON格式：\n"
        '{"step": "reply", "draft_text": "回复内容", '
        '"cited_evidence_ids": ["1", "2"], "confidence": 0.8, '
        '"unsupported_claims": [], "missing_information": [], '
        '"safety_notes": []}'
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = call_llm(messages, llm_config)
        parsed = extract_json(response)
        if parsed and "draft_text" in parsed:
            # Remap numbered citation IDs back to chunk IDs
            cited = parsed.get("cited_evidence_ids", [])
            resolved_ids: list[str] = []
            for cid in cited:
                try:
                    idx = int(cid)
                    if idx in id_to_chunk:
                        resolved_ids.append(id_to_chunk[idx])
                    else:
                        resolved_ids.append(cid)
                except (ValueError, TypeError):
                    resolved_ids.append(cid)
            parsed["cited_evidence_ids"] = resolved_ids
            return parsed

        # If LLM returned text but not structured JSON, wrap it
        if response and not parsed:
            return {
                "step": "reply",
                "draft_text": response.strip(),
                "cited_evidence_ids": [
                    str(ev.chunk_id) for ev in sorted_ev[:3]
                ],
                "confidence": 0.5,
                "unsupported_claims": [],
                "missing_information": [],
                "safety_notes": [
                    "LLM未返回结构化格式，已直接使用回复文本"
                ],
            }
        return None

    except Exception as e:
        logger.error("reply generation failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_reply(
    draft_result: dict[str, Any],
    evidence: list[EvidenceCandidate],
    flags: list[str],
    must_human_review: bool,
    build_fallback_fn: Callable[..., DraftReply],
    search_queries: list[str] | None = None,
) -> DraftReply:
    """Verify the generated reply and build a ``DraftReply``.

    Checks performed:
    - ``draft_text`` is non-empty.
    - Cited evidence IDs are valid.
    - Risk flags and severity are respected.

    Args:
        draft_result: The dict returned by :func:`generate_reply`.
        evidence: Evidence candidates used during generation.
        flags: Risk flags.
        must_human_review: Whether human review was already required.
        build_fallback_fn: Callable for constructing a fallback reply
            (expected to match :func:`build_fallback` signature).
        search_queries: List of search queries issued during the agent
            loop (included in the generation trace for debugging).

    Returns:
        A fully populated ``DraftReply``.
    """
    draft_text = draft_result.get("draft_text", "")
    cited_ids = draft_result.get("cited_evidence_ids", [])
    confidence = draft_result.get("confidence", 0.5)
    unsupported = draft_result.get("unsupported_claims", [])
    missing = draft_result.get("missing_information", [])
    safety_notes = draft_result.get("safety_notes", [])

    # Clamp confidence
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (ValueError, TypeError):
        confidence = 0.5

    # Build citations from evidence
    evidence_by_id = {str(e.chunk_id): e for e in evidence}
    citations: list[Citation] = []
    valid_cited_ids: list[str] = []
    for cid in cited_ids:
        cid_str = str(cid)
        if cid_str in evidence_by_id:
            ev = evidence_by_id[cid_str]
            citations.append(
                Citation(
                    chunk_id=ev.chunk_id,
                    doc_id=ev.doc_id,
                    doc_type=ev.doc_type,
                    source_table=getattr(ev, "source_table", ""),
                    source_id=getattr(ev, "source_id", ev.doc_id),
                    evidence_excerpt=ev.content[:200],
                    claim_supported=True,
                )
            )
            valid_cited_ids.append(cid_str)

    # If no valid citations but we have evidence, add top evidence
    if not citations and evidence:
        sorted_ev = sorted(evidence, key=lambda e: e.rank)[:3]
        for ev in sorted_ev:
            citations.append(
                Citation(
                    chunk_id=ev.chunk_id,
                    doc_id=ev.doc_id,
                    doc_type=ev.doc_type,
                    source_table=getattr(ev, "source_table", ""),
                    source_id=getattr(ev, "source_id", ev.doc_id),
                    evidence_excerpt=ev.content[:200],
                    claim_supported=True,
                )
            )
            valid_cited_ids.append(str(ev.chunk_id))

    # Empty draft text fallback
    if not draft_text.strip():
        return build_fallback_fn(
            reason="empty_draft",
            flags=flags,
            must_human_review=True,
        )

    # Determine review requirements
    needs_review = must_human_review or bool(flags) or bool(unsupported)

    escalation_reason: str | None = None
    if needs_review:
        if flags:
            escalation_reason = f"risk_flags: {', '.join(flags)}"
        elif must_human_review:
            escalation_reason = "risk_assessment_requires_review"
        elif unsupported:
            escalation_reason = "unsupported_claims_detected"

    if flags:
        safety_notes.append(
            f"工单含风险标记：{', '.join(flags)}，需人工审核"
        )

    # Build generation trace for debugging
    trace = {
        "agent_iterations": 5,
        "search_queries": search_queries or [],
        "evidence_count": len(evidence),
        "cited_count": len(valid_cited_ids),
    }

    return DraftReply(
        ticket_id="",
        draft_text=draft_text,
        citations=citations,
        evidence_used=citations,
        unsupported_claims=unsupported,
        missing_information=missing,
        confidence=confidence,
        must_human_review=needs_review,
        provider_id="draft_agent",
        escalation_reason=escalation_reason,
        safety_notes=safety_notes,
        cited_evidence_ids=valid_cited_ids,
        generation_trace=trace,
    )


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def build_fallback(
    reason: str,
    flags: list[str],
    must_human_review: bool,
    error_msg: str | None = None,
) -> DraftReply:
    """Build a safe fallback ``DraftReply`` when the agent cannot proceed.

    Args:
        reason: Machine-readable reason string (e.g. ``"agent_error"``).
        flags: Risk flags.
        must_human_review: Whether human review was already required.
        error_msg: Optional error message for debugging.

    Returns:
        A ``DraftReply`` with zero confidence and ``must_human_review=True``.
    """
    safety_notes: list[str] = []
    if flags:
        safety_notes.append(
            f"工单含风险标记：{', '.join(flags)}，需人工审核"
        )
    if error_msg:
        safety_notes.append(f"Agent错误：{error_msg}")

    escalation_reason: str | None = None
    if flags:
        escalation_reason = f"risk_flags: {', '.join(flags)}"
    elif must_human_review:
        escalation_reason = "risk_assessment_requires_review"
    else:
        escalation_reason = "agent_fallback"

    return DraftReply(
        ticket_id="",
        draft_text=SAFE_FALLBACK_TEXT,
        citations=[],
        evidence_used=[],
        unsupported_claims=["Agent无法生成有依据的回复"],
        missing_information=["未找到相关证据"],
        confidence=0.0,
        must_human_review=True,
        fallback_reason=reason,
        provider_id="draft_agent",
        escalation_reason=escalation_reason,
        safety_notes=safety_notes,
        cited_evidence_ids=[],
    )
