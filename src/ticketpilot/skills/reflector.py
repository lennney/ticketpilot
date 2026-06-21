"""Self-reflection loop: check drafts against skill best practices."""

from __future__ import annotations

import logging

from ticketpilot.skills.schema import SkillPattern

logger = logging.getLogger(__name__)


class ReflectionResult:
    """Result of reflecting on a draft against a skill pattern."""

    __slots__ = ("passed", "issues", "suggestions")

    def __init__(
        self,
        passed: bool,
        issues: list[str],
        suggestions: list[str],
    ) -> None:
        self.passed = passed
        self.issues = issues
        self.suggestions = suggestions


def reflect_on_draft(
    draft_text: str,
    skill: SkillPattern,
    risk_flags: list[str],
) -> ReflectionResult:
    """Check whether a draft satisfies a skill's best practices.

    Checks:
      1. Required risk-flag acknowledgements
      2. Key elements from resolution steps
      3. Tone alignment
    """
    issues: list[str] = []
    suggestions: list[str] = []

    # 1. Risk-flag acknowledgement
    for flag in skill.risk_flags_to_acknowledge:
        if (
            flag == "legal_risk"
            and "律师" not in draft_text
            and "法律" not in draft_text
        ):
            issues.append(f"缺少法律风险声明: {flag}")
            suggestions.append("添加法律风险相关的免责声明")

    # 2. Resolution step coverage (suggestions only, not hard issues)
    for step in skill.resolution_steps:
        if "订单号" in step and "订单" not in draft_text:
            suggestions.append(f"建议添加: {step}")

    # 3. Tone check
    if (
        skill.tone == "empathetic"
        and "抱歉" not in draft_text
        and "理解" not in draft_text
    ):
        suggestions.append("建议添加同理心表达")

    passed = len(issues) == 0
    return ReflectionResult(passed=passed, issues=issues, suggestions=suggestions)
