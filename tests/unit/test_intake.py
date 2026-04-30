"""Tests for intake module (normalization and entity extraction)."""

from datetime import datetime


from ticketpilot.schema.ticket import RawTicket
from ticketpilot.intake.normalizer import TextNormalizer
from ticketpilot.intake.entity_extractor import EntityExtractor
from ticketpilot.intake.pipeline import pipeline as intake_pipeline


class TestTextNormalizer:
    """Tests for TextNormalizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = TextNormalizer()

    def test_strip_whitespace(self):
        """Test stripping leading/trailing whitespace."""
        assert self.normalizer.normalize("  hello  ") == "hello"
        assert self.normalizer.normalize("\thello\n") == "hello"

    def test_collapse_whitespace(self):
        """Test collapsing multiple whitespace to single space."""
        assert self.normalizer.normalize("hello    world") == "hello world"
        assert self.normalizer.normalize("hello\n\n\nworld") == "hello world"

    def test_empty_string(self):
        """Test normalizing empty string."""
        assert self.normalizer.normalize("") == ""
        assert self.normalizer.normalize("   ") == ""

    def test_mixed_case(self):
        """Test normalizing with both strip and collapse."""
        assert self.normalizer.normalize("  hello    world  ") == "hello world"


class TestEntityExtractor:
    """Tests for EntityExtractor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = EntityExtractor()

    def test_extract_order_number_with_prefix(self):
        """Test extracting order number with prefix like 订单号."""
        text = "我申请退款，订单号123456"
        result = self.extractor.extract(text)
        assert "123456" in result.order_numbers

    def test_extract_order_number_simple(self):
        """Test extracting order number with simple pattern."""
        text = "订单号: 789012"
        result = self.extractor.extract(text)
        assert "789012" in result.order_numbers

    def test_no_order_number(self):
        """Test when no order number is present."""
        text = "我只是问一下，这个产品怎么用"
        result = self.extractor.extract(text)
        assert len(result.order_numbers) == 0

    def test_multiple_order_numbers(self):
        """Test extracting multiple order numbers."""
        text = "订单号123456和订单号789012都有问题"
        result = self.extractor.extract(text)
        assert "123456" in result.order_numbers
        assert "789012" in result.order_numbers

    def test_no_duplicates(self):
        """Test that duplicate order numbers are removed."""
        text = "订单号123456和订单号123456是同一个"
        result = self.extractor.extract(text)
        assert result.order_numbers.count("123456") == 1


class TestIntakePipeline:
    """Tests for intake pipeline."""

    def test_pipeline_returns_normalized_ticket(self):
        """Test pipeline returns NormalizedTicket."""
        raw_ticket = RawTicket(
            original_text="测试文本",
            submitted_at=datetime.utcnow(),
        )
        result = intake_pipeline(raw_ticket)
        assert result.text == "测试文本"
        assert result.language == "zh"
        assert result.cleaned_at is not None

    def test_pipeline_normalizes_text(self):
        """Test pipeline normalizes text correctly."""
        raw_ticket = RawTicket(
            original_text="  退款申请    订单号123456  ",
            submitted_at=datetime.utcnow(),
        )
        result = intake_pipeline(raw_ticket)
        assert result.text == "退款申请 订单号123456"

    def test_pipeline_extracts_order_numbers(self):
        """Test pipeline extracts order numbers."""
        raw_ticket = RawTicket(
            original_text="我申请退款，订单号123456",
            submitted_at=datetime.utcnow(),
        )
        result = intake_pipeline(raw_ticket)
        assert "123456" in result.order_numbers

    def test_pipeline_handles_empty_text(self):
        """Test pipeline handles empty text."""
        raw_ticket = RawTicket(
            original_text="",
            submitted_at=datetime.utcnow(),
        )
        result = intake_pipeline(raw_ticket)
        assert result.text == ""
