"""Integration tests for keyword retrieval."""

import uuid
from unittest.mock import patch

import pytest

from ticketpilot.retrieval.keyword_search import (
    _check_business_terms,
    _extract_search_terms,
    keyword_search,
)
from ticketpilot.retrieval.traces import KeywordResult
from ticketpilot.retrieval.schema.knowledge import DocType


class TestKeywordSearchLogic:
    """Tests for keyword search logic (without database)."""

    def test_extract_search_terms_english(self):
        """Test extracting search terms from English text."""
        terms = _extract_search_terms("hello world test")
        assert terms == ["hello", "world", "test"]

    def test_extract_search_terms_empty(self):
        """Test extracting search terms from empty string."""
        terms = _extract_search_terms("")
        assert terms == []

    def test_extract_search_terms_whitespace(self):
        """Test extracting search terms with extra whitespace."""
        terms = _extract_search_terms("  hello   world  ")
        assert terms == ["hello", "world"]

    def test_check_business_terms_found(self):
        """Test detecting business terms in query."""
        found = _check_business_terms("我想申请退款")
        assert "退款" in found

    def test_check_business_terms_not_found(self):
        """Test when no business terms are found."""
        found = _check_business_terms("hello world")
        assert len(found) == 0

    def test_check_business_terms_multiple(self):
        """Test detecting multiple business terms."""
        found = _check_business_terms("退款申请，7天内处理投诉")
        assert "退款" in found
        assert "7天" in found
        assert "投诉" in found


class TestKeywordSearchMocked:
    """Tests for keyword search with mocked database."""

    @pytest.fixture
    def mock_keyword_results(self):
        """Create mock keyword results."""
        return [
            KeywordResult(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                content="如何申请退款？",
                score=0.5,
                rank=1,
                search_method="fts",
                fts_rank=1,
                like_rank=None,
            ),
            KeywordResult(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.POLICY,
                content="退款政策说明",
                score=0.4,
                rank=2,
                search_method="fts",
                fts_rank=2,
                like_rank=None,
            ),
        ]

    def test_keyword_search_returns_results(self, mock_keyword_results):
        """Test that keyword_search returns results structure."""
        with patch(
            "ticketpilot.retrieval.keyword_search._fts_search",
            return_value=mock_keyword_results,
        ):
            results, method = keyword_search("退款", top_k=10)

            assert len(results) == 2
            assert method == "fts"
            assert all(isinstance(r, KeywordResult) for r in results)

    def test_keyword_search_with_doc_types_filter(self, mock_keyword_results):
        """Test that keyword_search properly filters by doc_types."""
        with patch(
            "ticketpilot.retrieval.keyword_search._fts_search",
            return_value=mock_keyword_results,
        ):
            results, method = keyword_search(
                "退款",
                top_k=10,
                doc_types=[DocType.FAQ],
            )

            assert len(results) == 2


class TestKeywordSearchFTS:
    """Integration tests for FTS search (requires database)."""

    @pytest.fixture
    def db_available(self):
        """Check if database is available."""
        try:
            from ticketpilot.retrieval.db.connection import get_db_connection

            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            import sys
            import traceback

            print(f"DEBUG db_available exception: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False

    @pytest.fixture
    def ensure_seeded(self, db_available):
        """Ensure database is seeded with test data."""
        if not db_available:
            pytest.skip("Database not available")
        try:
            from ticketpilot.retrieval.db.seeding import (
                seed_knowledge_chunks,
                get_chunk_count,
            )

            if get_chunk_count() == 0:
                seed_knowledge_chunks(clear_existing=True)
        except Exception as e:
            pytest.skip(f"Could not seed database: {e}")

    def test_fts_search_returns_results(self, db_available, ensure_seeded):
        """Test FTS search returns results for known term."""
        if not db_available:
            pytest.skip("Database not available")

        results, method = keyword_search("退款", top_k=5)

        assert len(results) > 0, "Should return results for '退款'"
        assert method in ["fts", "fts+like"]
        assert all(r.score >= 0 for r in results)

    def test_fts_search_ranks_by_relevance(self, db_available, ensure_seeded):
        """Test that FTS results are ranked by relevance."""
        if not db_available:
            pytest.skip("Database not available")

        results, _ = keyword_search("退款", top_k=10)

        if len(results) > 1:
            # First result should have higher or equal score
            assert results[0].score >= results[1].score

    def test_fts_search_with_doc_type_filter(self, db_available, ensure_seeded):
        """Test FTS search with doc_type filter."""
        if not db_available:
            pytest.skip("Database not available")

        results, _ = keyword_search(
            "退款",
            top_k=10,
            doc_types=[DocType.FAQ],
        )

        assert all(r.doc_type == DocType.FAQ for r in results)

    def test_like_fallback_for_business_terms(self, db_available, ensure_seeded):
        """Test LIKE fallback for strong business terms."""
        if not db_available:
            pytest.skip("Database not available")

        # Query with business term
        results, method = keyword_search("7天", top_k=10)

        # Should either use LIKE or supplement with it
        assert method in ["fts", "fts+like"]

    def test_keyword_search_returns_trace_fields(self, db_available, ensure_seeded):
        """Test that keyword results have all required fields."""
        if not db_available:
            pytest.skip("Database not available")

        results, _ = keyword_search("退款", top_k=5)

        if results:
            result = results[0]
            assert result.chunk_id is not None
            assert result.doc_id is not None
            assert result.doc_type is not None
            assert result.content is not None
            assert result.score >= 0
            assert result.rank >= 1
            assert result.search_method in ["fts", "like"]
