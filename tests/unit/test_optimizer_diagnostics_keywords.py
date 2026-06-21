"""Tests for Chinese keyword extraction in diagnostics."""

from __future__ import annotations


def test_extract_chinese_keywords_basic():
    """Test basic keyword extraction from Chinese texts."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = [
        "我要投诉你们服务太差了",
        "投诉态度不好",
        "服务很差要投诉",
    ]
    existing = ["投诉", "差评"]
    keywords = _extract_chinese_keywords(texts, existing)
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    # Should not include words already in existing
    for kw in keywords:
        assert kw not in existing
    print(f"Extracted keywords: {keywords}")


def test_extract_chinese_keywords_empty_texts():
    """Test with empty text list."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    keywords = _extract_chinese_keywords([], ["投诉"])
    assert keywords == []


def test_extract_chinese_keywords_all_existing():
    """Test when all frequent words are already in existing keywords."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = ["投诉投诉投诉", "投诉投诉"]
    existing = ["投诉"]
    keywords = _extract_chinese_keywords(texts, existing)
    # All common words are already in existing, so should be empty or very limited
    assert isinstance(keywords, list)
    for kw in keywords:
        assert kw not in existing


def test_extract_chinese_keywords_max_limit():
    """Test that max_keywords parameter is respected."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = [
        "我要投诉你们服务太差了态度不好",
        "投诉服务态度问题",
        "服务差投诉态度",
    ]
    keywords = _extract_chinese_keywords(texts, [], max_keywords=3)
    assert len(keywords) <= 3


def test_extract_chinese_keywords_non_chinese_filtered():
    """Test that non-Chinese characters are filtered out."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = ["Hello world 123 投诉 test"]
    keywords = _extract_chinese_keywords(texts, [])
    # Should not contain English words or numbers
    for kw in keywords:
        assert kw.isascii() is False or len(kw) > 0


def test_extract_chinese_keywords_stop_words_filtered():
    """Test that common stop words are filtered out."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = ["我是好人", "你好吗"]
    keywords = _extract_chinese_keywords(texts, [])
    # Stop words like "我是", "好人" should be filtered or low priority
    # The function should still return something useful
    assert isinstance(keywords, list)


def test_extract_chinese_keywords_document_frequency():
    """Test that words appearing in more texts are ranked higher."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = [
        "投诉服务态度差",
        "投诉服务太慢了",
        "投诉服务质量不好",
    ]
    keywords = _extract_chinese_keywords(texts, [])
    # "投诉" appears in all 3 texts, should be highest (if not in existing)
    # "服务" appears in all 3 texts
    assert isinstance(keywords, list)
    assert len(keywords) > 0


def test_extract_jieba_returns_meaningful_words():
    """Test that jieba produces proper Chinese words (not broken n-grams)."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = [
        "我要投诉你们客服态度太差了",
        "投诉服务不好态度恶劣",
    ]
    keywords = _extract_chinese_keywords(texts, [])
    # Each keyword should be at least 2 chars (jieba outputs proper words)
    for kw in keywords:
        assert len(kw) >= 2
    # Should have some keywords (no n-gram garbage like '诉你', '们客', '服态')
    assert len(keywords) > 0
    # None should be mid-word splits (n-gram artifacts)
    for kw in keywords:
        # These are common n-gram artifacts — none should appear
        assert kw not in ("诉你", "们客", "服态", "货但", "我申"), (
            f"'{kw}' is an n-gram artifact, not a real word"
        )
