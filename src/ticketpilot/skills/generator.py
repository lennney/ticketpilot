"""Generate skills from successful human-reviewed cases."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ticketpilot.skills.schema import SkillPattern

_KEYWORDS = ["退款", "投诉", "物流", "发货", "赔偿", "律师", "起诉"]


def generate_skill_from_success(
    intent: str,
    original_text: str,
    approved_draft: str,
    risk_flags: list[str],
    feedback: str = "",
) -> SkillPattern:
    """Extract a skill pattern from a successfully approved case.

    Extracts:
      1. Keywords present in the original ticket
      2. Resolution steps from the approved draft (split by sentence)
      3. Risk flags that were acknowledged
    """
    keywords = [word for word in _KEYWORDS if word in original_text]

    steps = [s.strip() for s in approved_draft.split("。") if len(s.strip()) > 5][:5]

    skill_id = f"{intent}_{uuid.uuid4().hex[:8]}"
    return SkillPattern(
        skill_id=skill_id,
        intent=intent,
        name=f"{intent}处理模式",
        description=f"从成功案例自动生成: {original_text[:50]}...",
        keywords=keywords,
        resolution_steps=steps,
        risk_flags_to_acknowledge=risk_flags,
        success_count=1,
        last_used=datetime.now(timezone.utc),
    )
