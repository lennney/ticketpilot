"""Evidence-grounded prompt builder for LLM draft generation.

Converts ticket context and evidence candidates into a structured prompt
that constrains the LLM to evidence-grounded drafting only.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from ticketpilot.schema.evidence import EvidenceCandidate

logger = logging.getLogger(__name__)

EVIDENCE_MAX_CHARS = 200
DEFAULT_MAX_EVIDENCE = 5

EVIDENCE_SEPARATOR = "\n---\n"
SECTION_SEPARATOR = "\n\n"

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "prompts" / "templates"


class DraftPromptInput(BaseModel):
    """Input data for building a draft generation prompt.

    Attributes:
        ticket_text: The customer's normalized message text.
        issue_type: Classified issue type / intent label.
        risk_flags: Risk flags detected for this ticket.
        severity: Risk severity level ("low", "medium", "high", "critical").
        must_human_review: Whether risk assessment already requires human review.
        evidence_candidates: Retrieved evidence candidates from the knowledge base.
        template_id: Template identifier for specialized prompts (e.g., "complaint", "refund").
    """

    ticket_text: str
    issue_type: str
    risk_flags: list[str] = Field(default_factory=list)
    severity: str = "low"
    must_human_review: bool = False
    evidence_candidates: list[EvidenceCandidate] = Field(default_factory=list)
    template_id: str = "default"


def load_template(template_id: str) -> str | None:
    """Load a prompt template from the templates directory.

    Args:
        template_id: Template identifier (filename without .md extension).

    Returns:
        Template content string, or None if not found.
    """
    template_path = _TEMPLATES_DIR / f"{template_id}.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    logger.warning("Template '%s' not found at %s", template_id, template_path)
    return None


def format_evidence_block(
    evidence: list[EvidenceCandidate],
    max_count: int = DEFAULT_MAX_EVIDENCE,
    max_chars: int = EVIDENCE_MAX_CHARS,
) -> str:
    """Format evidence candidates into a structured text block.

    Evidence is sorted by rank ascending. Empty content items are skipped.
    Long content is truncated deterministically to ``max_chars``.

    Args:
        evidence: List of evidence candidates, assumed already ranked.
        max_count: Maximum number of evidence items to include.
        max_chars: Maximum characters per evidence content snippet.

    Returns:
        A formatted string of evidence blocks separated by ``EVIDENCE_SEPARATOR``.
    """
    sorted_ev = sorted(evidence, key=lambda e: e.rank)
    blocks: list[str] = []

    for ev in sorted_ev[:max_count]:
        if not ev.content.strip():
            continue

        title_line = f"（{ev.title}）" if ev.title else ""
        snippet = ev.content[:max_chars]
        block = (
            f"[证据 ID]: {ev.chunk_id}\n"
            f"[文档 ID]: {ev.doc_id}\n"
            f"[类型]: {ev.doc_type.value}\n"
            f"[标题]: {title_line}\n"
            f"[相关度]: 排名 {ev.rank}, 评分 {ev.score:.2f}\n"
            f"[内容]: {snippet}"
        )
        blocks.append(block)

    if not blocks:
        return "[无可用证据]"

    return EVIDENCE_SEPARATOR.join(blocks)


def build_safety_instructions(
    risk_flags: list[str] | None = None,
    severity: str = "low",
    must_human_review: bool = False,
) -> str:
    """Build safety and constraint instructions for the prompt.

    Args:
        risk_flags: Risk flags detected for this ticket.
        severity: Risk severity level.
        must_human_review: Whether risk assessment already requires review.

    Returns:
        Safety instruction text to include in the prompt.
    """
    flags = risk_flags or []
    lines: list[str] = []

    lines.append("## 安全与约束规则")
    lines.append("")
    lines.append("在生成回复草稿时，必须遵守以下规则：")
    lines.append("")
    rules = [
        "你正在起草客服回复草稿，此回复不会自动发送给客户。",
        "仅使用上面提供的证据来支持你的回复。",
        "每一条事实性或政策性陈述都必须引用对应的证据ID，格式为 [证据ID]。",
        "如果证据不足以回答客户的问题，必须说明需要转人工处理。",
        "禁止承诺退款金额、赔偿、法律行动、账户变更或任何未在证据中明确支持的内容。",
        "禁止承认法律责任或做出超出证据范围的保证。",
        "禁止承诺解决时间线或保证特定结果。",
        "所有回复必须以草稿形式呈现，不得使用最终确认语气。",
    ]

    if flags:
        rules.append(
            f"本工单包含高风险标记：{', '.join(flags)}。"
            "回复中必须说明案件已升级至人工审核。"
        )

    if must_human_review:
        rules.append("风险评估已要求人工审核，回复必须明确建议转人工处理。")

    for i, rule in enumerate(rules, start=1):
        lines.append(f"{i}. {rule}")

    lines.append("")
    if severity in ("high", "critical"):
        lines.append(f"注意：本工单严重程度为「{severity}」，请格外谨慎处理。")

    return "\n".join(lines)


def build_output_format_instructions() -> str:
    """Build structured output format instructions for the prompt.

    Returns:
        Output format instruction text.
    """
    return """## 输出格式要求

请按以下结构组织你的回复草稿：

1. **answer_text**：完整的回复草稿文本，包括称呼、具体答复和结束语。
2. **cited_evidence_ids**：你在回复中引用的所有证据ID列表。
3. **unsupported_claims**：客户要求但证据无法支持的内容列表（若无则留空）。
4. **safety_notes**：任何需要注意的安全相关说明（若无则留空）。
5. **must_human_review**：如果回复需要人工审核，设置为 true；否则为 false。
6. **escalation_reason**：如果需要升级，说明原因（否则留空）。
7. **confidence**：你对回复准确性的信心值（0.0 到 1.0）。

注意：
- cited_evidence_ids 必须只包含上面证据列表中出现的ID。
- 如果证据不足，must_human_review 必须为 true。"""


def build_prompt(
    input_data: DraftPromptInput,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
    evidence_max_chars: int = EVIDENCE_MAX_CHARS,
    template_id: str | None = None,
) -> str:
    """Build a complete structured prompt for LLM draft generation.

    Assembles ticket context, evidence blocks, safety instructions, and
    output format instructions into a single prompt string.

    Args:
        input_data: The prompt input with ticket and evidence context.
        max_evidence: Maximum evidence items to include.
        evidence_max_chars: Max characters per evidence snippet.
        template_id: Override template ID. If None, uses input_data.template_id.

    Returns:
        A structured prompt string ready for LLM input.

    Raises:
        ValueError: If ticket_text is empty.
    """
    if not input_data.ticket_text.strip():
        msg = "ticket_text must not be empty"
        raise ValueError(msg)

    effective_template_id = template_id or input_data.template_id

    sections: list[str] = []

    # System role
    sections.append(
        "你是一名客服回复草稿助手。请根据以下信息和证据，生成专业的客服回复草稿。"
    )

    # Load and insert specialized template if available
    template_content = load_template(effective_template_id)
    if template_content:
        sections.append(
            f"## 专项处理指南（{effective_template_id}）\n\n{template_content}"
        )
    elif effective_template_id != "default":
        # Try falling back to default template
        default_content = load_template("default")
        if default_content:
            sections.append(f"## 专项处理指南（default）\n\n{default_content}")

    # Ticket context
    context_lines = [
        "## 工单信息",
        "",
        f"客户问题：{input_data.ticket_text}",
        f"问题类型：{input_data.issue_type}",
        f"严重程度：{input_data.severity}",
    ]
    if input_data.risk_flags:
        context_lines.append(f"风险标记：{', '.join(input_data.risk_flags)}")
    if input_data.must_human_review:
        context_lines.append("人工审核标记：需要人工审核")
    sections.append("\n".join(context_lines))

    # Evidence block
    evidence_header = "## 可用证据"
    formatted_evidence = format_evidence_block(
        input_data.evidence_candidates,
        max_count=max_evidence,
        max_chars=evidence_max_chars,
    )
    sections.append(f"{evidence_header}\n\n{formatted_evidence}")

    # Safety instructions
    sections.append(
        build_safety_instructions(
            risk_flags=input_data.risk_flags,
            severity=input_data.severity,
            must_human_review=input_data.must_human_review,
        )
    )

    # Output format instructions
    sections.append(build_output_format_instructions())

    return SECTION_SEPARATOR.join(sections)
