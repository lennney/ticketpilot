"""Tests for RRF fusion correctness."""

import uuid

import pytest

from ticketpilot.retrieval.rrf import format_rrf_explanation, rrf_fusion
from ticketpilot.retrieval.traces import FusedResult, KeywordResult, VectorResult
from ticketpilot.retrieval.schema.knowledge import DocType


class TestRRFCorrectness:
    """Tests for RRF formula correctness."""

    def _make_keyword_result(
        self, chunk_id: uuid.UUID, rank: int, score: float = 1.0
    ) -> KeywordResult:
        """Helper to create KeywordResult."""
        return KeywordResult(
            chunk_id=chunk_id,
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content=f"content for {chunk_id}",
            score=score,
            rank=rank,
            search_method="fts",
            fts_rank=rank,
            like_rank=None,
        )

    def _make_vector_result(
        self, chunk_id: uuid.UUID, rank: int, score: float = 0.9
    ) -> VectorResult:
        """Helper to create VectorResult."""
        return VectorResult(
            chunk_id=chunk_id,
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content=f"content for {chunk_id}",
            score=score,
            rank=rank,
            embedding_provider="fake",
        )

    def test_rrf_single_ranker_keyword_only(self):
        """Scenario 1: Only keyword results (no vector)."""
        kw_results = [
            self._make_keyword_result(uuid.uuid4(), 1),
            self._make_keyword_result(uuid.uuid4(), 2),
            self._make_keyword_result(uuid.uuid4(), 3),
        ]
        vec_results = []

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 3
        # Check order is preserved
        assert fused[0].keyword_rank == 1
        assert fused[1].keyword_rank == 2
        assert fused[2].keyword_rank == 3
        # Check contributions
        assert fused[0].keyword_contribution == pytest.approx(1 / (60 + 1))
        assert fused[1].keyword_contribution == pytest.approx(1 / (60 + 2))
        assert fused[2].keyword_contribution == pytest.approx(1 / (60 + 3))
        # Check vector contributions are None
        assert all(r.vector_rank is None for r in fused)
        # Check sources
        assert all("keyword" in r.sources for r in fused)
        assert all("vector" not in r.sources for r in fused)

    def test_rrf_single_ranker_vector_only(self):
        """Scenario 2: Only vector results (no keyword)."""
        kw_results = []
        vec_results = [
            self._make_vector_result(uuid.uuid4(), 1),
            self._make_vector_result(uuid.uuid4(), 2),
        ]

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 2
        assert fused[0].vector_rank == 1
        assert fused[1].vector_rank == 2
        # Check keyword contributions are None
        assert all(r.keyword_rank is None for r in fused)

    def test_rrf_both_rankers_same_order(self):
        """Scenario 3: Both rankers agree on order."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        id3 = uuid.uuid4()

        kw_results = [
            self._make_keyword_result(id1, 1),
            self._make_keyword_result(id2, 2),
            self._make_keyword_result(id3, 3),
        ]
        vec_results = [
            self._make_vector_result(id1, 1),
            self._make_vector_result(id2, 2),
            self._make_vector_result(id3, 3),
        ]

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 3
        assert fused[0].chunk_id == id1
        assert fused[1].chunk_id == id2
        assert fused[2].chunk_id == id3

    def test_rrf_both_rankers_different_order(self):
        """Scenario 4: Rankers disagree on order."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        # Keyword: id1 > id2
        # Vector: id2 > id1
        kw_results = [
            self._make_keyword_result(id1, 1),
            self._make_keyword_result(id2, 2),
        ]
        vec_results = [
            self._make_vector_result(id2, 1),
            self._make_vector_result(id1, 2),
        ]

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 2
        # id1: kw_rank=1, vec_rank=2 -> 1/61 + 1/62 = 0.01639 + 0.01613 = 0.03252
        # id2: kw_rank=2, vec_rank=1 -> 1/62 + 1/61 = 0.01613 + 0.01639 = 0.03252
        # They should be equal, but order depends on secondary sort
        id1_result = next(r for r in fused if r.chunk_id == id1)
        id2_result = next(r for r in fused if r.chunk_id == id2)
        assert id1_result.keyword_rank == 1
        assert id1_result.vector_rank == 2
        assert id2_result.keyword_rank == 2
        assert id2_result.vector_rank == 1

    def test_rrf_one_doc_in_both_one_in_one(self):
        """Scenario 5: One doc in both rankers, one doc in only one."""
        id_both = uuid.uuid4()
        id_kw_only = uuid.uuid4()

        kw_results = [
            self._make_keyword_result(id_both, 1),
            self._make_keyword_result(id_kw_only, 2),
        ]
        vec_results = [
            self._make_vector_result(id_both, 1),
        ]

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 2
        # id_both should be first (has contributions from both)
        assert fused[0].chunk_id == id_both
        assert fused[0].keyword_rank == 1
        assert fused[0].vector_rank == 1
        assert len(fused[0].sources) == 2

    def test_rrf_empty_results(self):
        """Scenario 6: Both result lists are empty."""
        fused = rrf_fusion([], [], k=60)
        assert fused == []

    def test_rrf_k_parameter_affects_scores(self):
        """Scenario 7: Different k values produce different scores."""
        id1 = uuid.uuid4()
        kw_results = [self._make_keyword_result(id1, 1)]
        vec_results = []

        fused_k30 = rrf_fusion(kw_results, vec_results, k=30)
        fused_k60 = rrf_fusion(kw_results, vec_results, k=60)
        fused_k100 = rrf_fusion(kw_results, vec_results, k=100)

        # Higher k means lower contribution
        assert fused_k30[0].rrf_score > fused_k60[0].rrf_score
        assert fused_k60[0].rrf_score > fused_k100[0].rrf_score

    def test_rrf_explainability_keyword_only(self):
        """Scenario 8: Verify explainability for keyword-only results."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        kw_results = [
            self._make_keyword_result(id1, 2),
            self._make_keyword_result(id2, 5),
        ]
        vec_results = []

        fused = rrf_fusion(kw_results, vec_results, k=60)

        id1_result = next(r for r in fused if r.chunk_id == id1)
        id2_result = next(r for r in fused if r.chunk_id == id2)

        # Verify contributions are calculated correctly
        assert id1_result.keyword_contribution == pytest.approx(1 / (60 + 2))
        assert id1_result.vector_contribution is None
        assert id2_result.keyword_contribution == pytest.approx(1 / (60 + 5))
        assert id2_result.vector_contribution is None

    def test_rrf_explainability_both_rankers(self):
        """Scenario 9: Verify explainability for both rankers."""
        id1 = uuid.uuid4()
        kw_results = [self._make_keyword_result(id1, 2)]
        vec_results = [self._make_vector_result(id1, 5)]

        fused = rrf_fusion(kw_results, vec_results, k=60)

        assert len(fused) == 1
        result = fused[0]

        # Verify contributions
        assert result.keyword_rank == 2
        assert result.vector_rank == 5
        assert result.keyword_contribution == pytest.approx(1 / (60 + 2))
        assert result.vector_contribution == pytest.approx(1 / (60 + 5))
        assert result.rrf_score == pytest.approx(1 / (60 + 2) + 1 / (60 + 5))
        assert "keyword" in result.sources
        assert "vector" in result.sources


class TestRRFExplanation:
    """Tests for RRF explanation formatting."""

    def test_format_rrf_explanation(self):
        """Test that explanation is properly formatted."""
        result = FusedResult(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            content="Test content",
            rrf_score=0.03252,
            keyword_rank=2,
            keyword_contribution=1 / 62,
            vector_rank=5,
            vector_contribution=1 / 65,
            sources=["keyword", "vector"],
        )

        explanation = format_rrf_explanation(result, k=60)

        assert "Chunk ID:" in explanation
        assert "RRF Score: 0.03252" in explanation
        assert "Per-ranker contributions:" in explanation
        assert "keyword: rank=2" in explanation
        assert "vector: rank=5" in explanation
