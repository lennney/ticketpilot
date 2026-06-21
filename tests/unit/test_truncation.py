"""Tests for context window truncation."""

import pytest
from ticketpilot.retrieval.truncation import (
    TruncationConfig,
    estimate_tokens,
    truncate_context,
    get_truncation_stats,
)
from ticketpilot.retrieval.traces import FusedResult
from ticketpilot.retrieval.schema.knowledge import DocType


def _make_chunk(content: str, rrf_score: float = 0.5) -> FusedResult:
    """Helper to create a FusedResult for testing."""
    from uuid import uuid4

    return FusedResult(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        doc_type=DocType.FAQ,
        content=content,
        rrf_score=rrf_score,
    )


class TestEstimateTokens:
    def test_empty_text(self):
        assert estimate_tokens("") == 1  # min 1

    def test_short_text(self):
        assert estimate_tokens("hello") == 1

    def test_english_text(self):
        text = "a" * 100  # 100 chars
        assert estimate_tokens(text) == 25  # 100 / 4

    def test_custom_chars_per_token(self):
        text = "a" * 100
        assert estimate_tokens(text, chars_per_token=2.0) == 50


class TestTruncationConfig:
    def test_default_config(self):
        config = TruncationConfig()
        assert config.max_tokens == 4000
        assert config.chars_per_token == 4.0
        assert config.reserve_tokens == 200

    def test_effective_max_chars(self):
        config = TruncationConfig(
            max_tokens=4000, chars_per_token=4.0, reserve_tokens=200
        )
        assert config.effective_max_chars == 15200  # (4000 - 200) * 4

    def test_custom_config(self):
        config = TruncationConfig(
            max_tokens=1000, chars_per_token=3.0, reserve_tokens=100
        )
        assert config.effective_max_chars == 2700  # (1000 - 100) * 3


class TestTruncateContext:
    def test_empty_chunks(self):
        assert truncate_context([]) == []

    def test_single_chunk(self):
        chunk = _make_chunk("test text", rrf_score=0.8)
        result = truncate_context([chunk])
        assert len(result) == 1
        assert result[0] is chunk

    def test_sorted_by_score(self):
        low = _make_chunk("low", rrf_score=0.3)
        high = _make_chunk("high", rrf_score=0.9)
        mid = _make_chunk("mid", rrf_score=0.6)

        result = truncate_context([low, high, mid])
        assert len(result) == 3
        assert result[0].rrf_score == 0.9
        assert result[1].rrf_score == 0.6
        assert result[2].rrf_score == 0.3

    def test_truncates_to_budget(self):
        # Create chunks that exceed budget
        config = TruncationConfig(max_tokens=100, chars_per_token=4.0, reserve_tokens=0)
        # max_chars = 100 * 4 = 400

        chunks = [
            _make_chunk("a" * 200, rrf_score=0.9),
            _make_chunk("b" * 200, rrf_score=0.8),
            _make_chunk("c" * 200, rrf_score=0.7),
        ]

        result = truncate_context(chunks, config)
        # Should fit ~2 chunks (400 chars budget)
        assert len(result) == 2
        assert result[0].rrf_score == 0.9
        assert result[1].rrf_score == 0.8

    def test_always_includes_first_chunk(self):
        """Even if first chunk exceeds budget, it should be included."""
        config = TruncationConfig(max_tokens=10, chars_per_token=4.0, reserve_tokens=0)
        # max_chars = 40

        chunk = _make_chunk("a" * 1000, rrf_score=0.9)
        result = truncate_context([chunk], config)
        assert len(result) == 1

    def test_preserves_all_if_within_budget(self):
        config = TruncationConfig(
            max_tokens=10000, chars_per_token=4.0, reserve_tokens=0
        )
        chunks = [_make_chunk("short", rrf_score=0.5) for _ in range(10)]

        result = truncate_context(chunks, config)
        assert len(result) == 10


class TestTruncationStats:
    def test_no_truncation(self):
        chunks = [_make_chunk("test", rrf_score=0.5)]
        stats = get_truncation_stats(chunks, chunks)

        assert stats["original_count"] == 1
        assert stats["truncated_count"] == 1
        assert stats["removed_count"] == 0
        assert stats["chars_saved"] == 0
        assert stats["compression_ratio"] == 1.0

    def test_with_truncation(self):
        original = [
            _make_chunk("a" * 100, rrf_score=0.3),
            _make_chunk("b" * 200, rrf_score=0.9),
        ]
        truncated = [original[1]]  # Keep only high-scored

        stats = get_truncation_stats(original, truncated)

        assert stats["original_count"] == 2
        assert stats["truncated_count"] == 1
        assert stats["removed_count"] == 1
        assert stats["original_chars"] == 300
        assert stats["truncated_chars"] == 200
        assert stats["chars_saved"] == 100
        assert stats["compression_ratio"] == pytest.approx(200 / 300)

    def test_empty_lists(self):
        stats = get_truncation_stats([], [])
        assert stats["original_count"] == 0
        assert stats["truncated_count"] == 0
        assert stats["compression_ratio"] == 1.0
