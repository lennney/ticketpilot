"""Tests for intent classification module."""



from ticketpilot.schema.ticket import IntentClass
from ticketpilot.classification.classifier import IntentClassifier


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = IntentClassifier()

    def test_classify_refund(self):
        """Test classifying refund intent."""
        text = "我申请退款，订单号123456"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.REFUND
        assert result.confidence >= 0.5

    def test_classify_return_exchange(self):
        """Test classifying return/exchange intent."""
        text = "我想退货，这个产品有问题"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.RETURN_EXCHANGE

    def test_classify_account_issue(self):
        """Test classifying account issue intent."""
        text = "账号被盗了，有人盗刷了我的订单"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.ACCOUNT_ISSUE

    def test_classify_technical_issue(self):
        """Test classifying technical issue intent."""
        text = "APP打不开，一直闪退"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.TECHNICAL_ISSUE

    def test_classify_product_consulting(self):
        """Test classifying product consulting intent."""
        text = "这个产品怎么用？"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.PRODUCT_CONSULTING

    def test_classify_logistics(self):
        """Test classifying logistics intent."""
        text = "快递什么时候到？"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.LOGISTICS

    def test_classify_complaint(self):
        """Test classifying complaint intent."""
        text = "我要投诉你们，态度太差了"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.COMPLAINT

    def test_classify_other(self):
        """Test classifying other intent when no keywords match."""
        text = "今天天气不错"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.OTHER

    def test_classify_empty_text(self):
        """Test classifying empty text."""
        text = ""
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.OTHER
        assert result.confidence < 0.7

    def test_confidence_high_for_strong_match(self):
        """Test high confidence for clear keyword match."""
        text = "我要申请退款，请处理"
        result = self.classifier.classify(text)
        assert result.confidence >= 0.8

    def test_confidence_low_for_weak_match(self):
        """Test lower confidence for ambiguous text."""
        text = "东西坏了"
        result = self.classifier.classify(text)
        assert result.confidence < 0.7

    def test_classified_at_is_set(self):
        """Test classified_at timestamp is set."""
        text = "测试文本"
        result = self.classifier.classify(text)
        assert result.classified_at is not None
