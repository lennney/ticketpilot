"""Tests for risk assessment module."""

from datetime import datetime


from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RiskFlag,
    RiskSeverity,
)
from ticketpilot.risk.assessor import RiskAssessor


class TestRiskAssessor:
    """Tests for RiskAssessor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.assessor = RiskAssessor()

    def _make_classification(self, intent: IntentClass, confidence: float) -> ClassificationResult:
        """Helper to create ClassificationResult."""
        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            classified_at=datetime.utcnow(),
        )

    def _make_normalized_ticket(self, text: str, order_numbers: list[str] = None) -> NormalizedTicket:
        """Helper to create NormalizedTicket."""
        return NormalizedTicket(
            text=text,
            language="zh",
            order_numbers=order_numbers or [],
            product_info=None,
            amount=None,
            cleaned_at=datetime.utcnow(),
        )

    def test_flag_complaint_risk(self):
        """Test complaint_risk flag is set."""
        ticket = self._make_normalized_ticket("我要投诉你们，态度太差了")
        classification = self._make_classification(IntentClass.COMPLAINT, 0.9)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.COMPLAINT_RISK in result.flags

    def test_flag_compensation_risk(self):
        """Test compensation_risk flag is set."""
        ticket = self._make_normalized_ticket("我要求3倍赔偿，你们违约了")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.COMPENSATION_RISK in result.flags

    def test_flag_legal_risk(self):
        """Test legal_risk flag is set."""
        ticket = self._make_normalized_ticket("请联系我律师，准备起诉你们")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.LEGAL_RISK in result.flags
        assert result.must_human_review is True
        assert result.severity == RiskSeverity.HIGH

    def test_flag_account_security_risk(self):
        """Test account_security_risk flag is set."""
        ticket = self._make_normalized_ticket("账号被盗了，有人盗刷了我的订单")
        classification = self._make_classification(IntentClass.ACCOUNT_ISSUE, 0.9)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.ACCOUNT_SECURITY_RISK in result.flags

    def test_flag_policy_conflict(self):
        """Test policy_conflict flag is set."""
        ticket = self._make_normalized_ticket("你们违反了自己的政策")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.POLICY_CONFLICT in result.flags

    def test_flag_low_confidence(self):
        """Test low_confidence flag is set when classification confidence < 0.7."""
        ticket = self._make_normalized_ticket("东西坏了")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.LOW_CONFIDENCE in result.flags
        assert result.must_human_review is True
        assert result.severity == RiskSeverity.LOW  # LOW_CONFIDENCE is meta, doesn't count for severity

    def test_flag_insufficient_evidence(self):
        """Test insufficient_evidence flag is set for vague tickets."""
        ticket = self._make_normalized_ticket("东西坏了", order_numbers=[])
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.INSUFFICIENT_EVIDENCE in result.flags
        assert result.must_human_review is True
        assert result.severity == RiskSeverity.LOW  # INSUFFICIENT_EVIDENCE is meta, doesn't count for severity

    def test_flag_not_set_with_order(self):
        """Test insufficient_evidence is not set when order number exists."""
        ticket = self._make_normalized_ticket("东西坏了", order_numbers=["123456"])
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.INSUFFICIENT_EVIDENCE not in result.flags

    def test_severity_low_with_no_flags(self):
        """Test severity is LOW when no flags are set."""
        ticket = self._make_normalized_ticket("我申请退款，订单号123456", order_numbers=["123456"])
        classification = self._make_classification(IntentClass.REFUND, 0.9)
        result = self.assessor.assess(ticket, classification)
        assert result.severity == RiskSeverity.LOW
        assert result.must_human_review is False

    def test_severity_low_with_one_flag(self):
        """Test severity is LOW when exactly one flag is set."""
        ticket = self._make_normalized_ticket("我要投诉你们，态度太差了")
        classification = self._make_classification(IntentClass.COMPLAINT, 0.9)
        result = self.assessor.assess(ticket, classification)
        assert result.severity == RiskSeverity.LOW

    def test_severity_medium_with_two_flags(self):
        """Test severity is MEDIUM when exactly two flags are set."""
        ticket = self._make_normalized_ticket("我要求3倍赔偿，你们违约了")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert result.severity == RiskSeverity.MEDIUM

    def test_severity_high_with_three_or_more_flags(self):
        """Test severity is HIGH when three or more flags are set."""
        ticket = self._make_normalized_ticket("请联系我律师，准备起诉你们")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert result.severity == RiskSeverity.HIGH

    def test_flag_privacy_risk(self):
        """Test privacy_risk flag triggers with Chinese privacy keywords."""
        phrases = [
            "身份证号被看到",
            "身份证信息泄露",
            "证件号被别人看到了",
            "实名信息泄露",
            "个人信息泄露",
            "手机号泄露",
            "地址信息泄露",
            "泄露个人信息",
            "隐私信息泄露",
            "我的隐私被泄露了",
        ]
        for phrase in phrases:
            ticket = self._make_normalized_ticket(phrase)
            classification = self._make_classification(IntentClass.OTHER, 0.9)
            result = self.assessor.assess(ticket, classification)
            assert RiskFlag.PRIVACY_RISK in result.flags, f"Phrase {phrase!r} should trigger PRIVACY_RISK"
            assert result.must_human_review is True, f"Phrase {phrase!r} should require human review"

    def test_privacy_risk_severity(self):
        """Test PRIVACY_RISK counts as a substantive flag for severity."""
        ticket = self._make_normalized_ticket("泄露个人信息，我要投诉你们")
        classification = self._make_classification(IntentClass.COMPLAINT, 0.9)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.PRIVACY_RISK in result.flags
        assert RiskFlag.COMPLAINT_RISK in result.flags
        assert result.severity == RiskSeverity.MEDIUM
        assert result.must_human_review is True

    def test_privacy_risk_triggers_with_low_confidence(self):
        """Test PRIVACY_RISK combined with low_confidence meta-flag."""
        ticket = self._make_normalized_ticket("手机号泄露")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert RiskFlag.PRIVACY_RISK in result.flags
        assert RiskFlag.LOW_CONFIDENCE in result.flags
        assert result.severity == RiskSeverity.LOW
        assert result.must_human_review is True

    def test_assessed_at_is_set(self):
        """Test assessed_at timestamp is set."""
        ticket = self._make_normalized_ticket("测试")
        classification = self._make_classification(IntentClass.OTHER, 0.5)
        result = self.assessor.assess(ticket, classification)
        assert result.assessed_at is not None
