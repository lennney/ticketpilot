"""Context window truncation for retrieval results.

When retrieval returns too many chunks, truncate to fit within
a token budget while preserving the highest-scoring evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ticketpilot.retrieval.traces import FusedResult


@dataclass(frozen=True)
class TruncationConfig:
    """Configuration for context window truncation."""

    max_tokens: int = 4000
    chars_per_token: float = 4.0  # Approximate for English/Chinese mixed
    reserve_tokens: int = 200  # Reserve for prompt overhead

    @property
    def effective_max_chars(self) -> int:
        """Effective max characters based on token budget."""
        return int((self.max_tokens - self.reserve_tokens) * self.chars_per_token)


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """Estimate token count from text length.

    Args:
        text: Input text
        chars_per_token: Average characters per token (default 4.0)

    Returns:
        Estimated token count
    """
    return max(1, int(len(text) / chars_per_token))


def truncate_context(
    chunks: Sequence[FusedResult],
    config: TruncationConfig | None = None,
) -> list[FusedResult]:
    """Truncate retrieval results to fit within token budget.

    Sorts by RRF score (descending) and adds chunks until
    the token budget is exhausted.

    Args:
        chunks: Retrieved chunks with scores
        config: Truncation configuration (uses defaults if None)

    Returns:
        Truncated list of chunks, sorted by score descending
    """
    if not chunks:
        return []

    config = config or TruncationConfig()
    max_chars = config.effective_max_chars

    # Sort by RRF score descending (highest first)
    sorted_chunks = sorted(chunks, key=lambda c: c.rrf_score, reverse=True)

    result: list[FusedResult] = []
    current_chars = 0

    for chunk in sorted_chunks:
        chunk_chars = len(chunk.content or "")

        # Always include at least one chunk
        if result and current_chars + chunk_chars > max_chars:
            break

        result.append(chunk)
        current_chars += chunk_chars

    return result


def get_truncation_stats(
    original: Sequence[FusedResult],
    truncated: Sequence[FusedResult],
) -> dict[str, int | float]:
    """Get statistics about truncation.

    Args:
        original: Original chunks before truncation
        truncated: Chunks after truncation

    Returns:
        Dict with truncation statistics
    """
    original_chars = sum(len(c.content or "") for c in original)
    truncated_chars = sum(len(c.content or "") for c in truncated)

    return {
        "original_count": len(original),
        "truncated_count": len(truncated),
        "removed_count": len(original) - len(truncated),
        "original_chars": original_chars,
        "truncated_chars": truncated_chars,
        "chars_saved": original_chars - truncated_chars,
        "compression_ratio": (
            truncated_chars / original_chars if original_chars > 0 else 1.0
        ),
    }
