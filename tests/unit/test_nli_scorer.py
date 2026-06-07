"""Unit tests for NLI-based faithfulness and relevancy scorer.

Tests cover:
- Basic faithfulness scoring
- Synonym handling
- Negation detection
- Sentence decomposition
- Score range (0.0-1.0, no artificial floor)
- Comparison with keyword scorer
"""

from __future__ import annotations

import pytest

from ticketpilot.evaluation.nli_scorer import (
    NLIScorer,
    _detect_negation,
    _expand_synonyms,
    _extract_keywords,
    _segment_sentences,
)


@pytest.fixture
def scorer() -> NLIScorer:
    return NLIScorer()


# ===================================================================
# Internal helpers
# ===================================================================


class TestSegmentSentences:
    def test_split_by_period(self):
        sentences = _segment_sentences("这是第一句。这是第二句。")
        assert sentences == ["这是第一句", "这是第二句"]

    def test_split_by_mixed_punctuation(self):
        sentences = _segment_sentences("你好！请问退款了吗？没有收到。")
        assert sentences == ["你好", "请问退款了吗", "没有收到"]

    def test_single_sentence(self):
        sentences = _segment_sentences("只有一句话")
        assert sentences == ["只有一句话"]

    def test_empty_text(self):
        sentences = _segment_sentences("")
        assert sentences == []


class TestExtractKeywords:
    def test_filters_stop_words(self):
        keywords = _extract_keywords("我的订单已经发货了")
        assert "的" not in keywords
        assert "已经" not in keywords
        assert "了" not in keywords

    def test_keeps_meaningful_words(self):
        keywords = _extract_keywords("退款快递物流订单")
        assert "退款" in keywords
        assert "快递" in keywords
        assert "物流" in keywords
        assert "订单" in keywords

    def test_empty_text(self):
        assert _extract_keywords("") == set()

    def test_all_stop_words(self):
        assert _extract_keywords("的了在是") == set()


class TestExpandSynonyms:
    def test_refund_synonyms(self):
        words = {"退款"}
        expanded = _expand_synonyms(words)
        assert "退货" in expanded
        assert "退钱" in expanded
        assert "退还" in expanded

    def test_no_expansion_for_unknown(self):
        words = {"苹果", "香蕉"}
        expanded = _expand_synonyms(words)
        assert expanded == words

    def test_mixed_known_unknown(self):
        words = {"退款", "苹果"}
        expanded = _expand_synonyms(words)
        assert "退货" in expanded
        assert "苹果" in expanded


class TestDetectNegation:
    def test_positive_text(self):
        assert _detect_negation("已经发货了") is False

    def test_negation_bu(self):
        assert _detect_negation("不能退款") is True

    def test_negation_meiyou(self):
        assert _detect_negation("没有收到包裹") is True

    def test_negation_wei(self):
        assert _detect_negation("未处理") is True


# ===================================================================
# Faithfulness scoring
# ===================================================================


class TestScoreFaithfulness:
    def test_perfect_faithfulness(self, scorer: NLIScorer):
        """Answer is directly from context."""
        context = ["您的订单已发货，快递单号为SF123456789"]
        answer = "您的订单已发货，快递单号为SF123456789"
        score = scorer.score_faithfulness(answer, context)
        assert score > 0.8

    def test_partial_faithfulness(self, scorer: NLIScorer):
        """Answer fully grounded in context (subset of claims)."""
        context = ["您的订单已发货，快递单号为SF123456789，预计3天到达"]
        answer = "订单已发货"
        score = scorer.score_faithfulness(answer, context)
        assert score > 0.8  # All answer claims are in context

    def test_no_faithfulness(self, scorer: NLIScorer):
        """Answer has no overlap with context."""
        context = ["退款政策说明"]
        answer = "苹果很好吃"
        score = scorer.score_faithfulness(answer, context)
        assert score < 0.3

    def test_empty_context(self, scorer: NLIScorer):
        score = scorer.score_faithfulness("任何回答", [])
        assert score == 0.0

    def test_empty_answer(self, scorer: NLIScorer):
        score = scorer.score_faithfulness("", ["一些上下文"])
        assert score == 0.0

    def test_synonym_faithfulness(self, scorer: NLIScorer):
        """Answer uses synonyms of context words — should still score well."""
        context = ["我们支持退款服务，7天内可退"]
        answer = "可以退货，7天内可退"
        score = scorer.score_faithfulness(answer, context)
        assert score > 0.2  # Synonym "退货" matches "退款"

    def test_negation_penalty(self, scorer: NLIScorer):
        """Answer negates context — should be penalized."""
        context = ["订单已发货"]
        answer = "订单没有发货"
        score = scorer.score_faithfulness(answer, context)
        assert score < 0.5  # Negation should heavily penalize

    def test_score_range_zero_to_one(self, scorer: NLIScorer):
        """Score must be in [0.0, 1.0], no artificial 0.5 floor."""
        score = scorer.score_faithfulness("完全无关", ["一些内容"])
        assert 0.0 <= score <= 1.0

    def test_multiple_context_passages(self, scorer: NLIScorer):
        """Handles multiple context passages."""
        context = [
            "退款需要在7天内申请",
            "快递物流信息可在订单页面查看",
        ]
        answer = "退款需要在7天内申请"
        score = scorer.score_faithfulness(answer, context)
        assert score > 0.6


# ===================================================================
# Relevancy scoring
# ===================================================================


class TestScoreRelevancy:
    def test_highly_relevant(self, scorer: NLIScorer):
        """Answer directly addresses the question."""
        question = "如何申请退款？"
        answer = "您可以在订单页面点击退款按钮申请退款"
        score = scorer.score_relevancy(question, answer)
        assert score > 0.2

    def test_irrelevant_answer(self, scorer: NLIScorer):
        """Answer does not address the question."""
        question = "如何申请退款？"
        answer = "今天的天气很好"
        score = scorer.score_relevancy(question, answer)
        assert score < 0.3

    def test_synonym_relevancy(self, scorer: NLIScorer):
        """Answer uses synonyms of question keywords."""
        question = "怎么退货？"
        answer = "退款流程如下：点击申请退款"
        score = scorer.score_relevancy(question, answer)
        assert score > 0.3  # "退货" and "退款" are synonyms

    def test_empty_question(self, scorer: NLIScorer):
        score = scorer.score_relevancy("", "一些回答")
        assert score == 0.0

    def test_empty_answer(self, scorer: NLIScorer):
        score = scorer.score_relevancy("一些问题", "")
        assert score == 0.0

    def test_partial_relevancy(self, scorer: NLIScorer):
        """Answer addresses part of the question."""
        question = "退款和发货的流程是什么？"
        answer = "退款需要在7天内申请"
        score = scorer.score_relevancy(question, answer)
        assert 0.2 < score < 0.9

    def test_score_range(self, scorer: NLIScorer):
        """Score in [0.0, 1.0]."""
        score = scorer.score_relevancy("问题", "完全无关的回答")
        assert 0.0 <= score <= 1.0


# ===================================================================
# Integration with agent_eval.py
# ===================================================================


class TestAgentEvalIntegration:
    def test_keyword_scorer_backward_compatible(self):
        """Default scorer_type='keyword' returns same results as before."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness, compute_relevancy

        context = ["订单已发货"]
        score = compute_faithfulness("订单已发货", context)
        assert 0.5 <= score <= 1.0  # Keyword scorer has 0.5 floor

        score = compute_relevancy("订单状态", "订单已发货")
        assert 0.5 <= score <= 1.0

    def test_nli_scorer_via_agent_eval(self):
        """scorer_type='nli' delegates to NLIScorer."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness, compute_relevancy

        context = ["退款政策：7天内可退"]
        score = compute_faithfulness("退款政策：7天内可退", context, scorer_type="nli")
        assert score > 0.8

        score = compute_relevancy("如何退款？", "退款需要在7天内申请", scorer_type="nli")
        assert score > 0.2

    def test_nli_no_artificial_floor(self):
        """NLI scorer returns scores below 0.5 for poor matches."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness

        score_keyword = compute_faithfulness("完全无关", ["一些内容"], scorer_type="keyword")
        score_nli = compute_faithfulness("完全无关", ["一些内容"], scorer_type="nli")
        # NLI should score lower for irrelevant content
        assert score_nli <= score_keyword

    def test_invalid_scorer_type(self):
        """Invalid scorer_type defaults to keyword behavior."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness

        score = compute_faithfulness("text", ["ctx"], scorer_type="invalid")
        # Should not raise, falls through to keyword
        assert 0.0 <= score <= 1.0


# ===================================================================
# NLI vs Keyword comparison
# ===================================================================


class TestNLIvsKeyword:
    def test_nli_better_with_synonyms(self):
        """NLI scorer handles synonym matches that keyword misses."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness

        context = ["我们支持退款服务"]
        answer = "可以退货"

        keyword_score = compute_faithfulness(answer, context, scorer_type="keyword")
        nli_score = compute_faithfulness(answer, context, scorer_type="nli")
        # NLI should score higher due to synonym expansion (退款↔退货)
        assert nli_score > keyword_score

    def test_nli_better_with_negation(self):
        """NLI scorer detects negation contradictions."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness

        context = ["订单已发货"]
        answer = "订单没有发货"

        keyword_score = compute_faithfulness(answer, context, scorer_type="keyword")
        nli_score = compute_faithfulness(answer, context, scorer_type="nli")
        # NLI should score lower due to negation detection
        assert nli_score < keyword_score

    def test_nli_full_range(self):
        """NLI scorer uses full 0.0-1.0 range, not compressed 0.5-1.0."""
        from ticketpilot.evaluation.agent_eval import compute_faithfulness

        # Very poor match
        nli_low = compute_faithfulness("苹果好吃", ["退款政策"], scorer_type="nli")
        keyword_low = compute_faithfulness("苹果好吃", ["退款政策"], scorer_type="keyword")

        # NLI can go below 0.5
        assert nli_low < 0.5
        assert keyword_low >= 0.5  # keyword has artificial floor

    def test_deterministic(self, scorer: NLIScorer):
        """NLI scorer is deterministic."""
        context = ["退款政策7天内可退"]
        answer = "可以退款"

        r1 = scorer.score_faithfulness(answer, context)
        r2 = scorer.score_faithfulness(answer, context)
        assert r1 == r2

        r1 = scorer.score_relevancy("如何退款？", answer)
        r2 = scorer.score_relevancy("如何退款？", answer)
        assert r1 == r2
