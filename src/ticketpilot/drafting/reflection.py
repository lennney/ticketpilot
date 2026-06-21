"""Self-reflection and skill-based revision for the draft agent.

Functions:
    reflect_and_revise: LLM-based critique → revision loop that checks the
        draft for hallucination, coverage, and accuracy.
    skill_reflect: Apply registered skill libraries to validate the draft
        against domain-specific best practices.
"""

from __future__ import annotations

import logging
from typing import Any

from ticketpilot.drafting.llm_utils import (
    _SYSTEM_PROMPT,
    LlmConfig,
    call_llm,
    extract_json,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.skills.loader import load_skill_library, select_relevant_skills
from ticketpilot.skills.reflector import reflect_on_draft

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM-based self-reflection
# ---------------------------------------------------------------------------


def reflect_and_revise(
    draft_result: dict[str, Any],
    normalized_text: str,
    issue_type: str,
    evidence: list[EvidenceCandidate],
    flags: list[str],
    must_human_review: bool,
    llm_config: LlmConfig,
    max_revisions: int = 1,
) -> dict[str, Any]:
    """Self-reflection loop: critique the draft and revise if needed.

    Implements the Critique → Revise pattern from industry best practices.
    Reduces hallucination by checking if the draft is grounded in evidence.

    Args:
        draft_result: Initial draft from LLM.
        normalized_text: Customer's normalized message.
        issue_type: Classified intent.
        evidence: Retrieved evidence.
        flags: Risk flags.
        must_human_review: Whether human review is required.
        llm_config: LLM endpoint configuration.
        max_revisions: Maximum number of revision attempts.

    Returns:
        Revised ``draft_result`` dict (or original if critique passes).
    """
    draft_text = draft_result.get("draft_text", "")

    if not draft_text or not evidence:
        return draft_result

    # Build evidence summary for critique
    evidence_summary = "\n".join(
        f"[{i+1}] {e.content[:200]}"
        for i, e in enumerate(evidence[:5])
    )

    for revision in range(max_revisions):
        # Ask LLM to critique the draft
        critique_prompt = (
            "你是一名质量审核专家。请审核以下客服回复草稿。\n\n"
            f"客户问题：{normalized_text}\n"
            f"问题类型：{issue_type}\n\n"
            f"检索到的证据：\n{evidence_summary}\n\n"
            f"回复草稿：\n{draft_text}\n\n"
            "请从以下维度审核：\n"
            "1. 回复是否基于证据？（有无编造信息）\n"
            "2. 回复是否回答了客户问题？\n"
            "3. 引用是否准确？\n"
            "4. 有无遗漏重要信息？\n\n"
            "审核结果格式（JSON）：\n"
            '{\n'
            '  "pass": true/false,\n'
            '  "issues": ["问题1", "问题2"],\n'
            '  "suggestions": ["建议1", "建议2"]\n'
            '}'
        )

        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是质量审核专家，负责审核客服回复质量。",
                },
                {"role": "user", "content": critique_prompt},
            ]

            # Use lower temperature for consistent critique
            critique_config = LlmConfig(
                base_url=llm_config.base_url,
                api_key=llm_config.api_key,
                model=llm_config.model,
                timeout=llm_config.timeout,
                max_tokens=512,
                temperature=0.3,
            )
            response = call_llm(messages, critique_config)
            critique = extract_json(response)

            if not critique:
                logger.warning(
                    "reflect_and_revise: failed to parse critique response"
                )
                break

            # If critique passes, return original draft
            if critique.get("pass", False):
                logger.info(
                    "reflect_and_revise: self-reflection passed (revision %d)",
                    revision,
                )
                return draft_result

            # If critique fails, revise the draft
            issues = critique.get("issues", [])
            suggestions = critique.get("suggestions", [])

            logger.info(
                "reflect_and_revise: found issues (revision %d): %s",
                revision,
                issues,
            )

            revise_prompt = (
                "你是一名客服专家。请根据审核意见修改回复草稿。\n\n"
                f"客户问题：{normalized_text}\n"
                f"问题类型：{issue_type}\n\n"
                f"检索到的证据：\n{evidence_summary}\n\n"
                f"原回复草稿：\n{draft_text}\n\n"
                "审核发现的问题：\n"
                f"{chr(10).join(f'- {issue}' for issue in issues)}\n\n"
                "修改建议：\n"
                f"{chr(10).join(f'- {suggestion}' for suggestion in suggestions)}\n\n"
                "请修改回复，确保：\n"
                "1. 基于证据，不编造信息\n"
                "2. 回答客户问题\n"
                "3. 引用准确\n\n"
                "修改后的回复格式（JSON）：\n"
                '{\n'
                '  "draft_text": "修改后的回复内容",\n'
                '  "cited_evidence_ids": ["证据ID1", "证据ID2"],\n'
                '  "confidence": 0.8,\n'
                '  "unsupported_claims": [],\n'
                '  "missing_information": [],\n'
                '  "safety_notes": []\n'
                '}'
            )

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": revise_prompt},
            ]

            response = call_llm(messages, llm_config)
            revised = extract_json(response)

            if revised and revised.get("draft_text"):
                draft_result = revised
                draft_text = revised["draft_text"]
                logger.info(
                    "reflect_and_revise: draft revised (revision %d)", revision
                )
            else:
                logger.warning(
                    "reflect_and_revise: revision failed, keeping original"
                )
                break

        except Exception as e:
            logger.error("reflect_and_revise: self-reflection failed: %s", e)
            break

    return draft_result


# ---------------------------------------------------------------------------
# Skill-based reflection
# ---------------------------------------------------------------------------


def skill_reflect(
    result: DraftReply,
    issue_type: str,
    flags: list[str],
) -> DraftReply:
    """Apply skill-based reflection to the draft.

    Loads relevant skills, checks the draft against best practices,
    and appends suggestions to ``safety_notes`` if issues are found.
    This is optional — failures are silently absorbed.

    Args:
        result: The draft reply to reflect on (mutated in place).
        issue_type: Classified intent.
        flags: Risk flags.

    Returns:
        The (possibly modified) ``DraftReply``.
    """
    try:
        library = load_skill_library()
        skills = select_relevant_skills(library, issue_type, flags)
        if not skills:
            result.reflection_passed = None
            result.reflection_issues = []
            result.skill_used = None
            return result

        skill = skills[0]
        reflection = reflect_on_draft(result.draft_text, skill, flags)

        result.reflection_passed = reflection.passed
        result.reflection_issues = list(reflection.issues)
        result.skill_used = skill.skill_id

        if not reflection.passed:
            logger.info(
                "skill_reflect: found issues with %s: %s",
                skill.skill_id,
                reflection.issues,
            )
            # Append suggestions to safety notes for human reviewers
            result.safety_notes.extend(
                f"[Skill:{skill.skill_id}] {s}"
                for s in reflection.suggestions
            )
            # Lower confidence slightly when skill reflection fails
            result.confidence = max(0.0, result.confidence - 0.1)

        # Increment success count for the matched skill
        skill.success_count += 1
        return result
    except Exception as e:
        logger.debug("Skill reflection skipped: %s", e)
        result.reflection_passed = None
        result.reflection_issues = []
        result.skill_used = None
        return result
