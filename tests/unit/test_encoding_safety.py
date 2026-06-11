"""Tests for encoding safety and exclusion rules in classification.

All tests in this file run against the IntentClassifier (pure Python, no DB).
Encoding safety in the retrieval layer (keyword_search.py) requires DB
and is tested in tests/integration/.
"""

import pytest
from ticketpilot.schema.ticket import IntentClass
from ticketpilot.classification.classifier import IntentClassifier


class TestEncodingSafety:
    """Verify that the classifier handles bad input gracefully."""

    def test_bytes_content_safety(self):
        """Classifier should not crash on strings with embedded byte escapes."""
        classifier = IntentClassifier()
        # 包含可能损坏编码的文本
        result = classifier.classify("退款\xe2\x80\x99投诉")
        assert result.intent is not None

    def test_null_content_safety(self):
        """Null/empty content should result in OTHER classification."""
        classifier = IntentClassifier()
        result = classifier.classify("")
        assert result.intent == IntentClass.OTHER
        assert result.confidence > 0

    def test_surrogate_characters(self):
        """Classifier should not crash on surrogate characters in Python strings."""
        classifier = IntentClassifier()
        text = "退款问题\ud800态度差"
        result = classifier.classify(text)
        assert result.intent is not None


class TestExclusionRules:
    """Verify that exclusion rules work correctly in classifier."""

    def test_refund_excluded_for_complaint(self):
        """退款 + 投诉 → 应为 COMPLAINT，不是 REFUND。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退款，你们态度太差了我要投诉")
        # 因为 REFUND 规则有 exclusions=["投诉", "态度"]
        # 所以应该跳过 REFUND，匹配到 COMPLAINT
        assert result.intent == IntentClass.COMPLAINT

    def test_refund_without_exclusion(self):
        """仅退款，无投诉关键词 → 应为 REFUND。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退款")
        assert result.intent == IntentClass.REFUND

    def test_return_excluded_for_complaint(self):
        """退货 + 态度差 → 应为 COMPLAINT。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退货，你们客服态度太恶心了")
        # RETURN_EXCHANGE 有 exclusions=["投诉", "态度", "差评", "12315"]
        assert result.intent == IntentClass.COMPLAINT

    def test_refund_not_blocked_by_irrelevant_word(self):
        """包含不在排除列表中的词 → 仍为 REFUND。"""
        classifier = IntentClassifier()
        # "退款"匹配，且"热线"不在 REFUND 排除列表中
        result = classifier.classify("我要退款但你们热线打不通")
        assert result.intent == IntentClass.REFUND

    def test_refund_excluded_when_complaint_keyword_present(self):
        """退款 + 12315 → 排除规则生效 → 变为 COMPLAINT。"""
        classifier = IntentClassifier()
        # "12315" 在 REFUND exclusions 中 -> 跳过 REFUND -> COMPLAINT 匹配
        result = classifier.classify("我要退款，我的订单号是12315")
        assert result.intent == IntentClass.COMPLAINT

    def test_backward_compatibility_no_exclusions(self):
        """已有规则中未设置 exclusions 的 intent 不受影响。"""
        classifier = IntentClassifier()
        # ACCOUNT_ISSUE 没有 exclusions 字段
        result = classifier.classify("我的账号被冻结了")
        assert result.intent == IntentClass.ACCOUNT_ISSUE
        # TECHNICAL_ISSUE 也没有 exclusions
        result = classifier.classify("支付失败，系统bug")
        assert result.intent == IntentClass.TECHNICAL_ISSUE
