"""Shared utilities for safe-fallback detection."""

from ticketpilot.drafting.llm_provider import SAFE_FALLBACK_TEXT

# Chinese strings that indicate a safe-fallback message
# (as opposed to a substantive customer-service answer).
SAFE_FALLBACK_PATTERNS: list[str] = [
    "无法确认具体政策条款",
    "建议转人工处理",
    "转人工",
    "证据不足",
]


def is_safe_fallback(draft_text: str) -> bool:
    """Check if draft is a safe-fallback message with no substantive claims.

    Args:
        draft_text: The draft reply text to check.

    Returns:
        True if the text matches safe-fallback patterns or is empty.
    """
    if not draft_text:
        return True
    text_lower = draft_text.lower()
    for pattern in SAFE_FALLBACK_PATTERNS:
        if pattern in text_lower:
            return True
    return draft_text == SAFE_FALLBACK_TEXT
