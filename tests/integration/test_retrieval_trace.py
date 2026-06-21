"""Integration tests for retrieval trace."""

import uuid
from datetime import datetime

import pytest

from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import (
    FusedResult,
    KeywordResult,
    RetrievalTrace,
    VectorResult,
)


class TestRetrievalTraceSchema:
    """Tests for retrieval trace schema validation."""

    def test_trace_has_all_required_fields(self):
        """Test that RetrievalTrace has all required fields."""
        trace = RetrievalTrace(
            query="test query",
            query_embedding=[0.1] * 384,
            keyword_results=[],
            vector_results=[],
            fused_results=[],
            final_evidence_ids=[],
            total_latency_ms=100,
        )

        assert trace.query == "test query"
        assert len(trace.query_embedding) == 384
        assert trace.keyword_results == []
        assert trace.vector_results == []
        assert trace.fused_results == []
        assert trace.final_evidence_ids == []
        assert trace.total_latency_ms == 100

    def test_trace_has_default_values(self):
        """Test that trace has sensible defaults."""
        trace = RetrievalTrace(query="test")

        assert trace.created_at is not None
        assert trace.embedding_provider == "fake"
        assert trace.hnsw_params == {}
        assert trace.top_k == 10
        assert trace.rrf_k == 60

    def test_trace_timestamps_are_datetime(self):
        """Test that timestamp fields are datetime objects."""
        trace = RetrievalTrace(query="test")

        assert isinstance(trace.created_at, datetime)


class TestKeywordResultSchema:
    """Tests for KeywordResult schema."""

    def test_keyword_result_required_fields(self):
        """Test KeywordResult has required fields."""
        result = KeywordResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test content",
            score=0.5,
            rank=1,
        )

        assert result.search_method == "fts"  # default
        assert result.fts_rank is None  # default
        assert result.like_rank is None  # default

    def test_keyword_result_with_fts_rank(self):
        """Test KeywordResult with FTS rank."""
        result = KeywordResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test",
            score=0.5,
            rank=1,
            search_method="fts",
            fts_rank=1,
            like_rank=None,
        )

        assert result.search_method == "fts"
        assert result.fts_rank == 1


class TestVectorResultSchema:
    """Tests for VectorResult schema."""

    def test_vector_result_required_fields(self):
        """Test VectorResult has required fields."""
        result = VectorResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test content",
            score=0.9,
            rank=1,
        )

        assert result.embedding_provider == "fake"  # default


class TestFusedResultSchema:
    """Tests for FusedResult schema."""

    def test_fused_result_keyword_only(self):
        """Test FusedResult with keyword-only source."""
        result = FusedResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test content",
            rrf_score=0.5,
            keyword_rank=2,
            keyword_contribution=1 / 62,
            vector_rank=None,
            vector_contribution=None,
            sources=["keyword"],
        )

        assert result.keyword_rank == 2
        assert result.vector_rank is None
        assert "keyword" in result.sources
        assert "vector" not in result.sources

    def test_fused_result_vector_only(self):
        """Test FusedResult with vector-only source."""
        result = FusedResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test content",
            rrf_score=0.5,
            keyword_rank=None,
            keyword_contribution=None,
            vector_rank=3,
            vector_contribution=1 / 63,
            sources=["vector"],
        )

        assert result.keyword_rank is None
        assert result.vector_rank == 3

    def test_fused_result_both_sources(self):
        """Test FusedResult with both keyword and vector sources."""
        result = FusedResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="test content",
            rrf_score=0.03252,
            keyword_rank=2,
            keyword_contribution=1 / 62,
            vector_rank=5,
            vector_contribution=1 / 65,
            sources=["keyword", "vector"],
        )

        assert result.keyword_rank == 2
        assert result.vector_rank == 5
        assert len(result.sources) == 2


class TestRetrievalTraceIntegration:
    """Integration tests for retrieval trace (requires database)."""

    @pytest.fixture
    def db_available(self):
        """Check if database is available."""
        try:
            from ticketpilot.retrieval.db.connection import get_db_connection

            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
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

    def test_trace_captures_query_and_embedding(self, db_available, ensure_seeded):
        """Test that trace captures query and embedding."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval
        from ticketpilot.retrieval.vector_search import _detect_embedding_dim

        expected_dim = _detect_embedding_dim()

        trace = hybrid_retrieval("退款政策", top_k=5)

        assert trace.query == "退款政策"
        assert len(trace.query_embedding) == expected_dim
        assert all(isinstance(x, float) for x in trace.query_embedding)

    def test_trace_captures_keyword_results(self, db_available, ensure_seeded):
        """Test that trace captures keyword results."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        for result in trace.keyword_results:
            assert isinstance(result, KeywordResult)
            assert result.chunk_id is not None
            assert result.doc_id is not None
            assert result.doc_type is not None
            assert result.content is not None
            assert result.score >= 0
            assert result.rank >= 1

    def test_trace_captures_vector_results(self, db_available, ensure_seeded):
        """Test that trace captures vector results."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        for result in trace.vector_results:
            assert isinstance(result, VectorResult)
            assert result.chunk_id is not None
            assert result.doc_id is not None
            assert result.doc_type is not None
            assert result.content is not None
            assert 0 <= result.score <= 1
            assert result.rank >= 1

    def test_trace_captures_fused_results_with_contributions(
        self, db_available, ensure_seeded
    ):
        """Test that trace captures fused results with per-ranker contributions."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        for result in trace.fused_results:
            assert isinstance(result, FusedResult)
            assert result.chunk_id is not None
            assert result.doc_id is not None
            assert result.doc_type is not None
            assert result.content is not None
            assert result.rrf_score >= 0

            # Per-ranker contributions
            if result.keyword_rank is not None:
                assert result.keyword_contribution is not None
                assert result.keyword_contribution == pytest.approx(
                    1 / (trace.rrf_k + result.keyword_rank)
                )
            if result.vector_rank is not None:
                assert result.vector_contribution is not None
                assert result.vector_contribution == pytest.approx(
                    1 / (trace.rrf_k + result.vector_rank)
                )

    def test_trace_captures_latency(self, db_available, ensure_seeded):
        """Test that trace captures latency for each stage."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        assert trace.keyword_latency_ms >= 0
        assert trace.vector_latency_ms >= 0
        assert trace.fusion_latency_ms >= 0
        assert trace.total_latency_ms >= 0

    def test_trace_explain_result(self, db_available, ensure_seeded):
        """Test the explain_result method."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        if trace.fused_results:
            chunk_id = trace.fused_results[0].chunk_id
            explanation = trace.explain_result(chunk_id)

            assert "Chunk ID:" in explanation
            assert "RRF Score:" in explanation
            assert "Contributions:" in explanation
            assert "Content preview:" in explanation

    def test_trace_get_result_by_chunk_id(self, db_available, ensure_seeded):
        """Test the get_result_by_chunk_id method."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        if trace.fused_results:
            target = trace.fused_results[0]
            found = trace.get_result_by_chunk_id(target.chunk_id)

            assert found is not None
            assert found.chunk_id == target.chunk_id

    def test_trace_nonexistent_chunk_id(self, db_available, ensure_seeded):
        """Test get_result_by_chunk_id with non-existent ID."""
        if not db_available:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.pipeline import hybrid_retrieval

        trace = hybrid_retrieval("退款", top_k=5)

        found = trace.get_result_by_chunk_id(uuid.uuid4())
        assert found is None
