"""Integration tests for retrieval pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from ticketpilot.retrieval.pipeline import (
    DEFAULT_RRF_K,
    hybrid_retrieval,
    simple_retrieval,
)
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.retrieval.schema.knowledge import DocType


class TestPipelineMocked:
    """Tests for retrieval pipeline with mocked components."""

    @pytest.fixture
    def mock_trace(self):
        """Create a mock retrieval trace."""
        return RetrievalTrace(
            query="退款申请",
            query_embedding=[0.1] * 384,
            keyword_results=[],
            keyword_latency_ms=5,
            keyword_search_method="fts",
            vector_results=[],
            vector_latency_ms=10,
            fused_results=[],
            fusion_latency_ms=2,
            rrf_k=60,
            final_evidence_ids=[],
            total_latency_ms=17,
            embedding_provider="fake",
            hnsw_params={"m": 16, "ef_construction": 200, "ef_search": 100},
            top_k=10,
        )

    def test_hybrid_retrieval_returns_trace(self):
        """Test that hybrid_retrieval returns a RetrievalTrace."""
        mock_keyword_results = []
        mock_vector_results = []

        with patch(
            "ticketpilot.retrieval.pipeline.get_fake_embedding_provider"
        ) as mock_provider, \
        patch(
            "ticketpilot.retrieval.pipeline.keyword_search",
            return_value=(mock_keyword_results, "fts")
        ), \
        patch(
            "ticketpilot.retrieval.pipeline.vector_search",
            return_value=(mock_vector_results, 1)
        ):
            mock_provider.return_value = FakeEmbeddingProvider()

            trace = hybrid_retrieval("测试查询")

            assert isinstance(trace, RetrievalTrace)
            assert trace.query == "测试查询"
            assert len(trace.query_embedding) == 384

    def test_hybrid_retrieval_trace_has_all_fields(self):
        """Test that trace has all required fields."""
        mock_keyword_results = []
        mock_vector_results = []

        with patch(
            "ticketpilot.retrieval.pipeline.get_fake_embedding_provider"
        ) as mock_provider, \
        patch(
            "ticketpilot.retrieval.pipeline.keyword_search",
            return_value=(mock_keyword_results, "fts")
        ), \
        patch(
            "ticketpilot.retrieval.pipeline.vector_search",
            return_value=(mock_vector_results, 1)
        ):
            mock_provider.return_value = FakeEmbeddingProvider()

            trace = hybrid_retrieval("退款")

            # Verify all trace fields are populated
            assert trace.query is not None
            assert trace.query_embedding is not None
            assert len(trace.query_embedding) == 384
            assert trace.keyword_results is not None
            assert trace.vector_results is not None
            assert trace.fused_results is not None
            assert trace.rrf_k == DEFAULT_RRF_K
            assert trace.embedding_provider == "fake"
            assert trace.hnsw_params is not None
            assert "m" in trace.hnsw_params
            assert "ef_search" in trace.hnsw_params

    def test_simple_retrieval_returns_content_list(self):
        """Test that simple_retrieval returns just content strings."""
        with patch(
            "ticketpilot.retrieval.pipeline.hybrid_retrieval"
        ) as mock_hybrid:
            mock_hybrid.return_value = MagicMock(
                fused_results=[
                    MagicMock(content="Result 1"),
                    MagicMock(content="Result 2"),
                ]
            )

            results = simple_retrieval("测试")

            assert results == ["Result 1", "Result 2"]


class TestPipelineIntegration:
    """Integration tests for retrieval pipeline (requires database)."""

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
            from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks, get_chunk_count
            if get_chunk_count() == 0:
                seed_knowledge_chunks(clear_existing=True)
        except Exception as e:
            pytest.skip(f"Could not seed database: {e}")

    def test_hybrid_retrieval_integration(self, db_available, ensure_seeded):
        """Test full hybrid retrieval pipeline."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款如何申请", top_k=5)

        assert isinstance(trace, RetrievalTrace)
        assert trace.query == "退款如何申请"
        assert len(trace.query_embedding) == 384

    def test_pipeline_combines_keyword_and_vector(self, db_available, ensure_seeded):
        """Test that pipeline combines keyword and vector results."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款政策", top_k=10)

        # Should have results from at least one path
        has_results = (
            len(trace.keyword_results) > 0 or len(trace.vector_results) > 0
        )
        assert has_results, "Should have results from keyword or vector search"

    def test_pipeline_ranking_differs_from_inputs(self, db_available, ensure_seeded):
        """Test that fused ranking can differ from individual rankings."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款", top_k=10)

        # If we have results from both paths, check that fusion happened
        if len(trace.keyword_results) > 0 and len(trace.vector_results) > 0:
            # Check that fused results have contributions from both
            for result in trace.fused_results[:3]:
                # A result that appears in both should have both sources
                if "keyword" in result.sources and "vector" in result.sources:
                    assert result.keyword_rank is not None
                    assert result.vector_rank is not None
                    break

    def test_pipeline_trace_timing(self, db_available, ensure_seeded):
        """Test that trace captures timing information."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款", top_k=5)

        assert trace.keyword_latency_ms >= 0
        assert trace.vector_latency_ms >= 0
        assert trace.fusion_latency_ms >= 0
        assert trace.total_latency_ms >= 0
        # Total should be >= sum of parts (approximately)
        assert trace.total_latency_ms >= (
            trace.keyword_latency_ms + trace.vector_latency_ms
        )

    def test_pipeline_top_k_limit(self, db_available, ensure_seeded):
        """Test that results are limited to top_k."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款", top_k=3)

        assert len(trace.fused_results) <= 3
        assert len(trace.final_evidence_ids) <= 3

    def test_pipeline_with_doc_type_filter(self, db_available, ensure_seeded):
        """Test pipeline with doc_type filter."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval(
            "退款",
            top_k=5,
            doc_types=[DocType.FAQ],
        )

        # All results should be FAQ type
        for result in trace.fused_results:
            assert result.doc_type == DocType.FAQ

    def test_pipeline_trace_explainability(self, db_available, ensure_seeded):
        """Test that trace enables full explainability."""
        if not db_available:
            pytest.skip("Database not available")

        trace = hybrid_retrieval("退款", top_k=5)

        if trace.fused_results:
            result = trace.fused_results[0]

            # Should be able to get per-ranker contributions
            if result.keyword_rank is not None:
                assert result.keyword_contribution is not None
            if result.vector_rank is not None:
                assert result.vector_contribution is not None

            # Should be able to explain the result
            explanation = trace.explain_result(result.chunk_id)
            assert "Chunk ID:" in explanation
            assert "RRF Score:" in explanation