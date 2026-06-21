"""Error compaction for agent runs.

Factor 9: Compact Errors into Context

Compacts exceptions into short, actionable summaries that can be
injected into WorkingMemory for downstream steps to reason about.
"""

from __future__ import annotations


def compact_error(error: Exception, context: str, max_len: int = 200) -> str:
    """Compact an error into a short, actionable summary.

    Args:
        error: The exception that occurred.
        context: Where the error happened (e.g., "evidence_retrieval", "intake").
        max_len: Maximum length of the error message.

    Returns:
        Compact error string like:
        "RETRIEVAL_FAILED: connection refused (context: evidence_retrieval)"

    Examples:
        >>> compact_error(ConnectionError("Connection refused"), "retrieval")
        'ConnectionError: Connection refused (context: retrieval)'
        >>> compact_error(ValueError("empty text"), "intake")
        'ValueError: empty text (context: intake)'
    """
    error_type = type(error).__name__
    msg = str(error)[:max_len]
    return f"{error_type}: {msg} (context: {context})"


def compact_errors(
    errors: list[tuple[Exception, str]], max_len: int = 200
) -> list[str]:
    """Compact multiple errors into summaries.

    Args:
        errors: List of (exception, context) tuples.
        max_len: Maximum length per error message.

    Returns:
        List of compact error strings.
    """
    return [compact_error(err, ctx, max_len) for err, ctx in errors]
