"""Unit tests for MultiQueryExpander."""

from unittest.mock import patch


from ticketpilot.retrieval.query_expander import MultiQueryExpander


class TestMultiQueryExpander:
    def test_no_api_key_returns_original(self, monkeypatch):
        monkeypatch.delenv("TICKETPILOT_LLM_API_KEY", raising=False)
        expander = MultiQueryExpander(api_key="")
        result = expander.expand("退款没到账", "refund")
        assert result == ["退款没到账"]

    def test_parse_json_array(self):
        expander = MultiQueryExpander(api_key="fake")
        variants = expander._parse_variants('["退款进度", "退款到账时间"]')
        assert variants == ["退款进度", "退款到账时间"]

    def test_parse_markdown_fence(self):
        expander = MultiQueryExpander(api_key="fake")
        text = '```json\n["退款进度", "退款到账时间"]\n```'
        variants = expander._parse_variants(text)
        assert variants == ["退款进度", "退款到账时间"]

    def test_parse_invalid_returns_empty(self):
        expander = MultiQueryExpander(api_key="fake")
        assert expander._parse_variants("not json") == []

    def test_is_valid_variant_normal(self):
        expander = MultiQueryExpander(api_key="fake")
        assert expander._is_valid_variant("退款进度查询", "退款没到账")

    def test_is_valid_variant_empty(self):
        expander = MultiQueryExpander(api_key="fake")
        assert not expander._is_valid_variant("", "query")

    def test_is_valid_variant_same_as_original(self):
        expander = MultiQueryExpander(api_key="fake")
        assert not expander._is_valid_variant("退款没到账", "退款没到账")

    def test_is_valid_variant_too_long(self):
        expander = MultiQueryExpander(api_key="fake")
        assert not expander._is_valid_variant("a" * 51, "query")

    @patch("ticketpilot.retrieval.query_expander.MultiQueryExpander._call_llm")
    def test_expand_success(self, mock_llm):
        mock_llm.return_value = ["退款进度", "退款到账时间"]
        expander = MultiQueryExpander(api_key="fake-key")
        result = expander.expand("退款没到账", "refund")
        assert result == ["退款没到账", "退款进度", "退款到账时间"]

    @patch("ticketpilot.retrieval.query_expander.MultiQueryExpander._call_llm")
    def test_expand_llm_failure_fallback(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        expander = MultiQueryExpander(api_key="fake-key")
        result = expander.expand("退款没到账", "refund")
        assert result == ["退款没到账"]

    @patch("ticketpilot.retrieval.query_expander.MultiQueryExpander._call_llm")
    def test_expand_filters_invalid_variants(self, mock_llm):
        mock_llm.return_value = ["", "a" * 51, "有效变体"]
        expander = MultiQueryExpander(api_key="fake-key")
        result = expander.expand("退款没到账")
        assert result == ["退款没到账", "有效变体"]

    @patch("ticketpilot.retrieval.query_expander.MultiQueryExpander._call_llm")
    def test_expand_default_intent(self, mock_llm):
        """Test that expand works with default intent parameter (empty string)."""
        mock_llm.return_value = ["退款进度"]
        expander = MultiQueryExpander(api_key="fake-key")
        result = expander.expand("退款没到账")  # no intent arg
        assert result == ["退款没到账", "退款进度"]

    @patch("ticketpilot.retrieval.query_expander.MultiQueryExpander._call_llm")
    def test_expand_respects_num_variants_limit(self, mock_llm):
        """When LLM returns more variants than num_variants, truncate."""
        mock_llm.return_value = ["变体1", "变体2", "变体3"]
        expander = MultiQueryExpander(api_key="fake-key", num_variants=2)
        result = expander.expand("original query")
        assert len(result) == 3  # original + 2 variants
        assert "变体3" not in result

    def test_is_valid_variant_with_whitespace(self):
        """Variant that equals original after strip should be invalid."""
        expander = MultiQueryExpander(api_key="fake")
        assert not expander._is_valid_variant(" 退款没到账 ", "退款没到账")

    def test_parse_non_string_elements(self):
        """JSON array with non-string elements should convert to strings."""
        expander = MultiQueryExpander(api_key="fake")
        variants = expander._parse_variants('[123, true, "正常"]')
        assert variants == ["123", "True", "正常"]
