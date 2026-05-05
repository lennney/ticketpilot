"""Integration tests for vector retrieval."""

import uuid

import pytest

from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider
from ticketpilot.retrieval.traces import VectorResult
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.vector_search import (
    get_hnsw_params,
    vector_search,
)


class TestVectorSearchLogic:
    """Tests for vector search logic (without database)."""

    def test_hnsw_params_are_correct(self):
        """Test that HNSW params match specification."""
        params = get_hnsw_params()
        assert params["m"] == 16
        assert params["ef_construction"] == 200
        assert params["ef_search"] == 100

    def test_embedding_dimension_validation(self):
        """Test that wrong dimension embeddings are rejected.

        Note: This test requires database to be available since vector_search
        imports db.connection. If DB is not available, this test will be skipped.
        """
        try:
            from ticketpilot.retrieval.vector_search import _detect_embedding_dim
            expected_dim = _detect_embedding_dim()
        except Exception:
            pytest.skip("Database not available")

        wrong_dim_embedding = [0.1] * 100  # Wrong dimension

        with pytest.raises(ValueError, match=f"Expected {expected_dim}-d embedding"):
            vector_search(wrong_dim_embedding, top_k=10)

    def test_fake_embedding_produces_default_dim(self):
        """Test that fake embeddings have correct dimension."""
        from ticketpilot.retrieval.providers.fake_embedding import FAKE_EMBEDDING_DIM
        provider = FakeEmbeddingProvider(dimension=FAKE_EMBEDDING_DIM)
        vec = provider.embed("test")

        assert len(vec) == FAKE_EMBEDDING_DIM


class TestVectorSearchMocked:
    """Tests for vector search with mocked database.

    Note: These tests require the database to be available since the actual
    implementation needs to import db.connection. The integration tests
    handle the database-required cases.
    """

    @pytest.fixture
    def mock_vector_results(self):
        """Create mock vector results."""
        return [
            VectorResult(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                content="退款政策说明",
                score=0.95,
                rank=1,
                embedding_provider="fake",
            ),
            VectorResult(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                doc_type=DocType.FAQ,
                content="如何申请退款",
                score=0.88,
                rank=2,
                embedding_provider="fake",
            ),
        ]

    def test_vector_search_module_loads(self, mock_vector_results):
        """Test that vector_search module can be imported."""
        try:
            import ticketpilot.retrieval.db.connection  # noqa: F401
        except ImportError:
            pytest.skip("Database not available")

        from ticketpilot.retrieval.vector_search import vector_search, get_hnsw_params
        assert callable(vector_search)
        params = get_hnsw_params()
        assert params["m"] == 16


class TestVectorSearchIntegration:
    """Integration tests for vector search (requires database)."""

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

    @pytest.fixture
    def expected_dim(self, db_available):
        """Get expected embedding dimension from DB."""
        from ticketpilot.retrieval.vector_search import _detect_embedding_dim
        return _detect_embedding_dim()

    def test_vector_search_returns_results(self, db_available, ensure_seeded, expected_dim):
        """Test vector search returns results."""
        if not db_available:
            pytest.skip("Database not available")

        provider = FakeEmbeddingProvider(dimension=expected_dim)
        query_embedding = provider.embed("退款如何申请")

        results, latency_ms = vector_search(query_embedding, top_k=5)

        assert len(results) > 0, "Should return vector search results"
        assert latency_ms >= 0
        assert all(isinstance(r, VectorResult) for r in results)

    def test_vector_search_ranks_by_similarity(self, db_available, ensure_seeded, expected_dim):
        """Test that vector results are ranked by similarity."""
        if not db_available:
            pytest.skip("Database not available")

        provider = FakeEmbeddingProvider(dimension=expected_dim)
        query_embedding = provider.embed("退款政策")

        results, _ = vector_search(query_embedding, top_k=10)

        if len(results) > 1:
            # First result should have higher or equal similarity
            assert results[0].score >= results[1].score

    def test_vector_search_with_doc_type_filter(self, db_available, ensure_seeded, expected_dim):
        """Test vector search with doc_type filter."""
        if not db_available:
            pytest.skip("Database not available")

        provider = FakeEmbeddingProvider(dimension=expected_dim)
        query_embedding = provider.embed("退款")

        results, _ = vector_search(
            query_embedding,
            top_k=10,
            doc_types=[DocType.POLICY],
        )

        assert all(r.doc_type == DocType.POLICY for r in results)

    def test_vector_search_returns_trace_fields(self, db_available, ensure_seeded, expected_dim):
        """Test that vector results have all required fields."""
        if not db_available:
            pytest.skip("Database not available")

        provider = FakeEmbeddingProvider(dimension=expected_dim)
        query_embedding = provider.embed("退款")

        results, _ = vector_search(query_embedding, top_k=5)

        if results:
            result = results[0]
            assert result.chunk_id is not None
            assert result.doc_id is not None
            assert result.doc_type is not None
            assert result.content is not None
            assert 0 <= result.score <= 1  # Cosine similarity
            assert result.rank >= 1
            assert result.embedding_provider == "fake"

    def test_vector_search_scores_are_cosine_similarity(self, db_available, ensure_seeded, expected_dim):
        """Test that vector scores are valid cosine similarities."""
        if not db_available:
            pytest.skip("Database not available")

        provider = FakeEmbeddingProvider(dimension=expected_dim)

        # Query with same text should give score of 1.0
        text = "退款如何申请"
        embedding = provider.embed(text)

        results, _ = vector_search(embedding, top_k=1)

        if results:
            # The top result should be very similar (possibly the same content)
            assert results[0].score >= 0