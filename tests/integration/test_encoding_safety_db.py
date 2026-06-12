"""Integration tests for encoding safety in DB-backed retrieval.

Requires PostgreSQL (Docker). Skipped when TICKETPILOT_SKIP_DB_TESTS=1.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TICKETPILOT_SKIP_DB_TESTS") == "1",
    reason="Skipping DB-dependent integration tests",
)


class TestFTSContentSafety:
    """Verify FTS search handles encoding edge cases (needs real DB connection)."""

    def test_keyword_search_handles_special_chars(self):
        """Keyword search should handle special characters without crashing."""
        from ticketpilot.retrieval.keyword_search import _fts_search

        results = _fts_search("退款\x00投诉", top_k=5)
        # 不应崩溃
        assert isinstance(results, list)
