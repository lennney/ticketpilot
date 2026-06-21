"""Tests for query_builder — pure function, no mocking needed."""

from ticketpilot.retrieval.query_builder import build_retrieval_query
from ticketpilot.schema.ticket import IntentClass, RiskFlag


class TestBuildRetrievalQuery:
    def test_includes_normalized_text(self):
        query = build_retrieval_query("我的订单还没发货", IntentClass.LOGISTICS, set())
        assert "我的订单还没发货" in query

    def test_uses_chinese_intent_terms_not_english_enum_name(self):
        query = build_retrieval_query("申请退款", IntentClass.REFUND, set())
        assert "退款" in query
        assert "退货" in query
        assert "refund" not in query.lower()

    def test_all_8_intents_have_terms_or_empty(self):
        for intent in IntentClass:
            query = build_retrieval_query("测试文本", intent, set())
            if intent == IntentClass.OTHER:
                assert query == "测试文本"
            else:
                assert len(query) > len("测试文本")

    def test_risk_flag_terms_included(self):
        query = build_retrieval_query(
            "用户投诉", IntentClass.COMPLAINT, {RiskFlag.LEGAL_RISK}
        )
        assert "法律" in query
        assert "法规" in query

    def test_multiple_risk_flags_combined(self):
        flags = {RiskFlag.COMPENSATION_RISK, RiskFlag.PRIVACY_RISK}
        query = build_retrieval_query(
            "要求赔偿并删除信息", IntentClass.COMPLAINT, flags
        )
        assert "赔偿" in query
        assert "赔付" in query
        assert "金额" in query
        assert "隐私" in query
        assert "数据" in query

    def test_deduplication_removes_duplicates(self):
        intent_terms = ["退款", "退货", "退款政策"]
        risk_terms = ["赔偿", "赔付", "金额"]
        assert len(intent_terms) == len(set(intent_terms))
        assert len(risk_terms) == len(set(risk_terms))

        query = build_retrieval_query(
            "退款退货退款", IntentClass.REFUND, {RiskFlag.COMPENSATION_RISK}
        )
        parts = query.split()
        assert len(parts) == len(set(parts))

    def test_other_intent_no_risk_flags_returns_text_only(self):
        query = build_retrieval_query("随便问问", IntentClass.OTHER, set())
        assert query == "随便问问"

    def test_empty_text_still_returns_terms_when_available(self):
        query = build_retrieval_query("", IntentClass.REFUND, {RiskFlag.LEGAL_RISK})
        assert "退款" in query
        assert "法律" in query
        assert len(query) > 0

    def test_meta_flags_do_not_add_query_terms(self):
        for meta_flag in (RiskFlag.LOW_CONFIDENCE, RiskFlag.INSUFFICIENT_EVIDENCE):
            query = build_retrieval_query("测试", IntentClass.OTHER, {meta_flag})
            assert "low" not in query.lower()
            assert "insufficient" not in query.lower()
            assert query == "测试"

    def test_empty_text_and_no_terms_returns_empty(self):
        query = build_retrieval_query("", IntentClass.OTHER, set())
        assert query == ""

    def test_deduplication_cross_intent_and_risk(self):
        query = build_retrieval_query(
            "赔偿问题",
            IntentClass.COMPLAINT,
            {RiskFlag.COMPENSATION_RISK},
        )
        parts = query.split()
        assert "赔偿" in parts
        assert len(parts) == len(set(parts))

    def test_deduplication_preserves_first_occurrence_order(self):
        query = build_retrieval_query("退款申请", IntentClass.REFUND, set())
        parts = query.split()
        assert parts[0] == "退款申请"

    def test_all_risk_flags_with_terms_covered(self):
        substantive_flags = {
            RiskFlag.COMPENSATION_RISK,
            RiskFlag.LEGAL_RISK,
            RiskFlag.PRIVACY_RISK,
            RiskFlag.ACCOUNT_SECURITY_RISK,
            RiskFlag.POLICY_CONFLICT,
        }
        for flag in substantive_flags:
            query = build_retrieval_query("测试", IntentClass.OTHER, {flag})
            parts = query.split()
            assert len(parts) >= 2, f"Flag {flag.value} should contribute terms"
