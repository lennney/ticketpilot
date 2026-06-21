"""Unit tests for result_merger."""

from uuid import uuid4

import pytest

from ticketpilot.retrieval.result_merger import merge_retrieval_results
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import FusedResult


def _fused(chunk_id=None, rrf_score=0.5, content="test", sources=None):
    return FusedResult(
        chunk_id=chunk_id or uuid4(),
        doc_id=uuid4(),
        doc_type=DocType.FAQ,
        content=content,
        rrf_score=rrf_score,
        keyword_rank=1,
        keyword_contribution=0.016,
        sources=sources or ["keyword"],
    )


class TestMergeRetrievalResults:
    def test_empty_input(self):
        assert merge_retrieval_results([]) == []

    def test_all_empty_sets(self):
        assert merge_retrieval_results([[], []]) == []

    def test_single_set_passthrough(self):
        r = _fused()
        result = merge_retrieval_results([[r]])
        assert len(result) == 1
        assert result[0].chunk_id == r.chunk_id

    def test_sum_score_dedup(self):
        cid = uuid4()
        r1 = _fused(chunk_id=cid, rrf_score=0.3, sources=["keyword"])
        r2 = _fused(chunk_id=cid, rrf_score=0.2, sources=["vector"])
        merged = merge_retrieval_results([[r1], [r2]], strategy="sum_score")
        assert len(merged) == 1
        assert merged[0].rrf_score == pytest.approx(0.5)

    def test_sum_score_different_chunks(self):
        c1 = uuid4()
        c2 = uuid4()
        r1 = _fused(chunk_id=c1, rrf_score=0.3)
        r2 = _fused(chunk_id=c2, rrf_score=0.5)
        merged = merge_retrieval_results([[r1], [r2]], strategy="sum_score")
        assert len(merged) == 2
        # c2 should rank first (higher score)
        assert merged[0].chunk_id == c2

    def test_max_score_strategy(self):
        cid = uuid4()
        r1 = _fused(chunk_id=cid, rrf_score=0.3)
        r2 = _fused(chunk_id=cid, rrf_score=0.7)
        merged = merge_retrieval_results([[r1], [r2]], strategy="max_score")
        assert len(merged) == 1
        assert merged[0].rrf_score == pytest.approx(0.7)

    def test_rrf_again_strategy(self):
        c1 = uuid4()
        c2 = uuid4()
        # c1 ranked #1 in both queries, c2 ranked #2
        r1q1 = _fused(chunk_id=c1, rrf_score=0.5)
        r1q2 = _fused(chunk_id=c1, rrf_score=0.4)
        r2q1 = _fused(chunk_id=c2, rrf_score=0.3)
        r2q2 = _fused(chunk_id=c2, rrf_score=0.6)
        merged = merge_retrieval_results(
            [[r1q1, r2q1], [r1q2, r2q2]], strategy="rrf_again"
        )
        assert len(merged) == 2
        # c1 ranked higher in both, should be first
        assert merged[0].chunk_id == c1

    def test_multi_query_marker(self):
        r = _fused()
        merged = merge_retrieval_results([[r], [r]])
        assert "multi_query" in merged[0].sources

    def test_unknown_strategy_defaults_to_sum_score(self):
        """Unknown strategy string falls back to sum_score."""
        cid = uuid4()
        r1 = _fused(chunk_id=cid, rrf_score=0.3)
        r2 = _fused(chunk_id=cid, rrf_score=0.2)
        merged = merge_retrieval_results([[r1], [r2]], strategy="unknown_strategy")
        assert len(merged) == 1
        assert merged[0].rrf_score == pytest.approx(0.5)  # sum_score behavior

    def test_sum_score_prefers_highest_rrf_representative(self):
        """When same chunk appears multiple times, representative has highest rrf_score."""
        cid = uuid4()
        r1 = _fused(chunk_id=cid, rrf_score=0.1, sources=["keyword"])
        r2 = _fused(chunk_id=cid, rrf_score=0.8, sources=["vector"])
        merged = merge_retrieval_results([[r1], [r2]], strategy="sum_score")
        assert len(merged) == 1
        # Representative should be r2 (higher rrf_score)
        assert "vector" in merged[0].sources

    def test_multi_query_marker_no_duplicate(self):
        """Same chunk from 3 queries should have only one 'multi_query' marker."""
        cid = uuid4()
        r1 = _fused(chunk_id=cid, rrf_score=0.3, sources=["keyword"])
        r2 = _fused(chunk_id=cid, rrf_score=0.2, sources=["keyword"])
        r3 = _fused(chunk_id=cid, rrf_score=0.1, sources=["keyword"])
        merged = merge_retrieval_results([[r1], [r2], [r3]], strategy="sum_score")
        assert len(merged) == 1
        assert merged[0].sources.count("multi_query") == 1

    def test_rrf_again_precise_scores(self):
        """Verify exact RRF scores with k=60."""
        c1 = uuid4()
        c2 = uuid4()
        r1q1 = _fused(chunk_id=c1, rrf_score=0.5)
        r1q2 = _fused(chunk_id=c1, rrf_score=0.4)
        r2q1 = _fused(chunk_id=c2, rrf_score=0.3)
        r2q2 = _fused(chunk_id=c2, rrf_score=0.6)
        merged = merge_retrieval_results(
            [[r1q1, r2q1], [r1q2, r2q2]], strategy="rrf_again"
        )
        k = 60
        expected_c1 = 2 * (1 / (k + 1))  # Both rank 1
        expected_c2 = 2 * (1 / (k + 2))  # Both rank 2
        assert len(merged) == 2
        assert merged[0].chunk_id == c1
        assert merged[0].rrf_score == pytest.approx(expected_c1)
        assert merged[1].chunk_id == c2
        assert merged[1].rrf_score == pytest.approx(expected_c2)
