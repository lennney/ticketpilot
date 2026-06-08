"""Unit tests for HybridReranker."""
import math
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from ticketpilot.retrieval.hybrid_reranker import (
    HybridReranker,
    RerankResult,
    _cosine_similarity,
    _keyword_density,
    _length_score,
    _normalize_minmax,
)
from ticketpilot.retrieval.reranker_config import RerankerConfig
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import FusedResult


def _make_fused(
    chunk_id=None, doc_type="FAQ", content="test content", rrf_score=0.5
) -> FusedResult:
    return FusedResult(
        chunk_id=chunk_id or uuid4(),
        doc_id=uuid4(),
        doc_type=DocType(doc_type),
        content=content,
        rrf_score=rrf_score,
        keyword_rank=1,
        keyword_contribution=0.016,
        vector_rank=2,
        vector_contribution=0.015,
        sources=["keyword", "vector"],
    )


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        assert abs(_cosine_similarity([1, 0], [0, 1])) < 1e-9

    def test_opposite_vectors(self):
        assert abs(_cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 1e-9

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 0]) == 0.0


class TestLengthScore:
    def test_optimal_length_scores_highest(self):
        score = _length_score(500, 200, 800)
        assert score > 0.9

    def test_very_short_scores_low(self):
        score = _length_score(10, 200, 800)
        assert score < 0.3

    def test_very_long_scores_lower(self):
        score_optimal = _length_score(500, 200, 800)
        score_long = _length_score(3000, 200, 800)
        assert score_optimal > score_long

    def test_zero_length(self):
        assert _length_score(0, 200, 800) == 0.0


class TestKeywordDensity:
    def test_all_terms_present(self):
        assert _keyword_density("退款 到账", "退款一直没到账怎么办") == 1.0

    def test_partial_terms(self):
        assert _keyword_density("退款 到账 物流", "退款政策说明") == pytest.approx(1 / 3)

    def test_no_terms(self):
        assert _keyword_density("退款", "物流发货说明") == 0.0

    def test_empty_query(self):
        assert _keyword_density("", "some content") == 0.0


class TestNormalizeMinMax:
    def test_uniform_values(self):
        result = _normalize_minmax([5, 5, 5])
        assert result == [0.5, 0.5, 0.5]

    def test_normal_range(self):
        result = _normalize_minmax([0, 5, 10])
        assert result[0] == 0.0
        assert result[1] == pytest.approx(0.5)
        assert result[2] == 1.0

    def test_empty(self):
        assert _normalize_minmax([]) == []


class TestHybridReranker:
    def test_empty_candidates(self):
        reranker = HybridReranker()
        assert reranker.rerank([], "test") == []

    def test_single_candidate(self):
        c = _make_fused(rrf_score=0.5, content="退款政策说明 退款条件")
        reranker = HybridReranker()
        results = reranker.rerank([c], "退款", intent="refund", top_k=5)
        assert len(results) == 1
        assert results[0].rank == 1
        assert results[0].final_score > 0

    def test_ranking_order(self):
        c1 = _make_fused(rrf_score=0.3, content="退款政策说明")
        c2 = _make_fused(rrf_score=0.8, content="退款退款退款退款退款")
        reranker = HybridReranker()
        results = reranker.rerank([c1, c2], "退款", top_k=10)
        assert len(results) == 2
        # c2 has higher RRF + more keyword hits, should rank first
        assert results[0].chunk_id == c2.chunk_id
        assert results[0].rank == 1

    def test_intent_boost_effect(self):
        policy_doc = _make_fused(
            doc_type="POLICY", rrf_score=0.3, content="退款政策 退款条件"
        )
        case_doc = _make_fused(
            doc_type="CASE", rrf_score=0.3, content="退款案例 退款处理"
        )
        reranker = HybridReranker()
        results = reranker.rerank(
            [policy_doc, case_doc], "退款", intent="refund", top_k=10
        )
        # Policy doc should rank higher due to intent boost for refund→policy
        policy_result = next(r for r in results if r.chunk_id == policy_doc.chunk_id)
        case_result = next(r for r in results if r.chunk_id == case_doc.chunk_id)
        assert policy_result.final_score > case_result.final_score

    def test_signals_recorded(self):
        c = _make_fused(content="退款政策说明 退款流程")
        reranker = HybridReranker()
        results = reranker.rerank([c], "退款", top_k=5)
        assert len(results[0].signals) == 4
        signal_names = {s.name for s in results[0].signals}
        assert signal_names == {
            "rrf_score", "embedding_similarity",
            "intent_metadata_boost", "content_quality",
        }

    def test_fake_embedding_weight_redistribution(self):
        """With fake embedding provider, embedding weight should be 0."""
        cfg = RerankerConfig.default()
        # No embedding_provider = fake
        reranker = HybridReranker(config=cfg, embedding_provider=None)
        c = _make_fused(content="test content")
        results = reranker.rerank([c], "test", top_k=5)
        # embedding_similarity signal should have weight=0
        emb_signal = next(
            s for s in results[0].signals if s.name == "embedding_similarity"
        )
        assert emb_signal.weight == 0.0

    def test_to_fused_result_conversion(self):
        c = _make_fused(content="退款政策")
        reranker = HybridReranker()
        results = reranker.rerank([c], "退款", top_k=5)
        fused = results[0].to_fused_result()
        assert isinstance(fused, FusedResult)
        assert "hybrid_rerank" in fused.sources
        assert fused.chunk_id == c.chunk_id

    def test_top_k_less_than_candidates(self):
        """top_k truncates results."""
        candidates = [_make_fused(rrf_score=0.1 * i) for i in range(5)]
        reranker = HybridReranker()
        results = reranker.rerank(candidates, "test", top_k=2)
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[1].rank == 2

    def test_top_k_more_than_candidates(self):
        """top_k > len(candidates) returns all candidates."""
        candidates = [_make_fused(rrf_score=0.5)]
        reranker = HybridReranker()
        results = reranker.rerank(candidates, "test", top_k=10)
        assert len(results) == 1


class TestIsRealEmbeddingProvider:
    def test_real_provider(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        provider = MagicMock()
        provider.embed = MagicMock()
        provider.provider_name = "openai"
        assert _is_real_embedding_provider(provider) is True

    def test_fake_provider(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        provider = MagicMock()
        provider.embed = MagicMock()
        provider.provider_name = "fake"
        assert _is_real_embedding_provider(provider) is False

    def test_no_embed_or_encode(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        provider = MagicMock(spec=[])  # no attributes
        assert _is_real_embedding_provider(provider) is False

    def test_unknown_provider_name(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        provider = MagicMock()
        provider.encode = MagicMock()
        # No provider_name attribute → getattr returns "unknown"
        del provider.provider_name
        assert _is_real_embedding_provider(provider) is False

    def test_none_provider(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        assert _is_real_embedding_provider(None) is False

    def test_encode_method_sufficient(self):
        from ticketpilot.retrieval.hybrid_reranker import _is_real_embedding_provider
        provider = MagicMock(spec=["encode", "provider_name"])
        provider.encode = MagicMock()
        provider.provider_name = "bge"
        assert _is_real_embedding_provider(provider) is True


class TestKeywordDensityEdgeCases:
    def test_latin_word_boundary_no_false_positive(self):
        """'art' should NOT match inside 'smart'."""
        assert _keyword_density("art", "smart car") == 0.0

    def test_latin_word_boundary_exact_match(self):
        """'art' matches standalone 'Art'."""
        assert _keyword_density("art", "Art of war") == 1.0

    def test_cjk_substring_match(self):
        """CJK terms use substring matching."""
        assert _keyword_density("退款", "退款政策说明") == 1.0

    def test_mixed_cjk_latin(self):
        """Mixed query: CJK substring + Latin word boundary."""
        assert _keyword_density("退款 policy", "退款 policy 说明") == 1.0
        # 'policy' inside 'policyholder' should not match
        assert _keyword_density("policy", "policyholder agreement") == 0.0
