"""Tests for Chinese text segmentation in keyword search."""

from ticketpilot.retrieval.keyword_search import _segment_chinese_terms


def test_english_terms_pass_through():
    """Non-Chinese terms should not be segmented."""
    result = _segment_chinese_terms(["refund", "policy", "order-123"])
    assert result == ["refund", "policy", "order-123"]


def test_chinese_single_term_segmented():
    """Single long Chinese term should be broken into meaningful words."""
    result = _segment_chinese_terms(["我买的手机充电器坏了"])
    assert "手机" in result
    assert "充电器" in result
    # Stopword '的' should be filtered
    assert "的" not in result
    # Single-char stopwords should also be filtered
    assert "我" not in result


def test_chinese_stopwords_filtered():
    """Single-character Chinese stopwords should be removed."""
    result = _segment_chinese_terms(["我的", "是的", "走了"])
    assert "的" not in result
    assert "了" not in result


def test_mixed_chinese_english():
    """Mixed terms: English passes through, Chinese gets segmented."""
    result = _segment_chinese_terms(["iPhone", "退款政策", "error"])
    assert "iPhone" in result
    assert "error" in result
    assert "退款" in result or "政策" in result


def test_empty_terms():
    """Empty input returns empty list."""
    result = _segment_chinese_terms([])
    assert result == []


def test_all_stopwords_filters_everything():
    """If all terms are stopwords, result should be empty."""
    result = _segment_chinese_terms(["的", "了", "吗"])
    assert result == []


def test_numeric_mixed_with_chinese():
    """Numeric and Chinese mixed text."""
    result = _segment_chinese_terms(["7天无理由退货"])
    assert "7" in result or "天" in result
    assert "退货" in result
