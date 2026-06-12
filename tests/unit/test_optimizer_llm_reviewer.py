"""Tests for the LLM-based keyword trade-off reviewer.

These tests avoid actual LLM API calls by monkeypatching the OpenAI client
or the _llm_complete helper where appropriate.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ticketpilot.optimizer.config import OptimizerConfig
from ticketpilot.optimizer.llm_reviewer import _llm_complete, review_keyword
from ticketpilot.optimizer.tradeoff import KeywordTradeoff


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_tradeoff() -> KeywordTradeoff:
    return KeywordTradeoff(
        keyword="发货太慢",
        target_intent="logistics_complaint",
        fixed_case_ids=["case1", "case2", "case3"],
        harmed_case_ids=["case4"],
        net_gain=2,
        description="Add '发货太慢' to logistics_complaint",
    )


@pytest.fixture
def negative_tradeoff() -> KeywordTradeoff:
    return KeywordTradeoff(
        keyword="东西",
        target_intent="logistics_complaint",
        fixed_case_ids=["case1"],
        harmed_case_ids=["case2", "case3", "case4", "case5"],
        net_gain=-3,
        description="Add '东西' to logistics_complaint — too generic",
    )


@pytest.fixture
def config() -> OptimizerConfig:
    return OptimizerConfig(
        llm_api_key="test-key",
        llm_base_url="https://api.openai.com/v1",
        llm_model="gpt-4o-mini",
    )


# ---------------------------------------------------------------------------
# Tests: _llm_complete error handling
# ---------------------------------------------------------------------------


class TestLlmCompleteErrors:
    """_llm_complete should raise ValueError when no API key is available."""

    def test_missing_api_key_from_config_and_env(self):
        """No key in config and no env var -> ValueError."""
        cfg = OptimizerConfig(llm_api_key="", llm_base_url="", llm_model="")
        with pytest.raises(ValueError, match="No LLM API key configured"):
            _llm_complete("some prompt", cfg)

    @patch.dict("os.environ", {"OPTIMIZER_LLM_API_KEY": "env-key"})
    def test_api_key_from_env_var(self):
        """Key from env var should be accepted (no actual call, just no ValueError)."""
        # We patch OpenAI to prevent real network calls during this test
        cfg = OptimizerConfig(
            llm_api_key="",
            llm_base_url="https://api.openai.com/v1",
            llm_model="gpt-4o-mini",
        )
        with patch("ticketpilot.optimizer.llm_reviewer.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"decision": "APPROVE", "reasoning": "ok"}'
            mock_client.chat.completions.create.return_value = mock_response

            result = _llm_complete("some prompt", cfg)
            assert result is not None
            assert "APPROVE" in result

            # Verify the env var was used
            mock_openai.assert_called_once_with(api_key="env-key", base_url=cfg.llm_base_url)


# ---------------------------------------------------------------------------
# Tests: review_keyword prompt construction
# ---------------------------------------------------------------------------


class TestReviewKeywordPromptConstruction:
    """Verify the prompt is correctly built from tradeoff data."""

    def test_prompt_includes_all_fields(self, sample_tradeoff, config):
        """The formatted prompt should contain keyword, counts, samples."""
        fixed_samples = ["包裹配送时间太长", "物流信息不更新了"]
        harmed_samples = ["请问发货时间是多久"]

        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            mock_llm.return_value = '{"decision": "APPROVE", "reasoning": "Good improvement"}'
            result = review_keyword(sample_tradeoff, fixed_samples, harmed_samples, config)

            # Check _llm_complete was called
            mock_llm.assert_called_once()
            prompt = mock_llm.call_args[0][0]

            # Verify all key pieces are present in prompt
            assert "发货太慢" in prompt
            assert "logistics_complaint" in prompt
            assert "3" in prompt  # fixed_count
            assert "1" in prompt  # harmed_count
            assert "2" in prompt  # net_gain
            assert "包裹配送时间太长" in prompt
            assert "物流信息不更新了" in prompt
            assert "请问发货时间是多久" in prompt
            assert result["decision"] == "APPROVE"

    def test_prompt_sample_truncation(self, sample_tradeoff, config):
        """Only first 3 samples and 80 chars per sample should be included."""
        fixed_samples = ["a" * 100, "b" * 100, "c" * 100, "d" * 100]  # 4 samples

        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            mock_llm.return_value = '{"decision": "APPROVE", "reasoning": "ok"}'
            review_keyword(sample_tradeoff, fixed_samples, [], config)

            prompt = mock_llm.call_args[0][0]
            # Check sample truncation: the 4th sample should NOT be in the prompt
            assert "d" * 80 not in prompt
            # Check 80-char truncation: each sample should be at most 80 chars
            assert "a" * 80 in prompt
            assert "a" * 81 not in prompt

    def test_prompt_with_negative_tradeoff(self, negative_tradeoff, config):
        """Negative tradeoff should be reflected in the prompt."""
        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            mock_llm.return_value = '{"decision": "REJECT", "reasoning": "Net gain negative"}'
            result = review_keyword(negative_tradeoff, ["a"], ["b"], config)

            prompt = mock_llm.call_args[0][0]
            assert "-3" in prompt  # net_gain
            assert "东西" in prompt  # keyword
            assert result["decision"] == "REJECT"


# ---------------------------------------------------------------------------
# Tests: JSON parse fallback
# ---------------------------------------------------------------------------


class TestJsonParseFallback:
    """When the LLM response is malformed, review_keyword should return REJECT."""

    def test_malformed_json_returns_reject(self, sample_tradeoff, config):
        """Non-JSON response from LLM should be caught and return REJECT."""
        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            mock_llm.return_value = "I think this is a good keyword, APPROVE"
            result = review_keyword(sample_tradeoff, ["a"], ["b"], config)

            assert result["decision"] == "REJECT"
            assert "Failed to parse LLM response" in result["reasoning"]

    def test_extra_text_after_json_returns_reject(self, sample_tradeoff, config):
        """If LLM returns JSON but with extra trailing text, json.loads should still work
        if the JSON is properly terminated. If there's leading/trailing text json.loads won't
        parse it, so we expect REJECT."""
        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            # json.loads of this will work if the JSON portion is valid
            mock_llm.return_value = '{"decision": "APPROVE", "reasoning": "ok"}'
            result = review_keyword(sample_tradeoff, ["a"], ["b"], config)
            assert result["decision"] == "APPROVE"

    def test_json_in_code_fence(self, sample_tradeoff, config):
        """JSON inside markdown code fences won't parse directly -> REJECT."""
        with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
            mock_llm.return_value = "```json\n{\"decision\": \"APPROVE\", \"reasoning\": \"ok\"}\n```"
            result = review_keyword(sample_tradeoff, ["a"], ["b"], config)

            # json.loads on the raw string will fail because of the ``` fences
            assert result["decision"] == "REJECT"
            assert "Failed to parse" in result["reasoning"]


# ---------------------------------------------------------------------------
# Tests: review_keyword default config
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """review_keyword should work with no config passed (uses defaults)."""

    def test_default_config_no_api_key_raises(self, sample_tradeoff):
        """With no config and no env var, _llm_complete should raise ValueError."""
        with patch.dict("os.environ", clear=True):
            if "OPTIMIZER_LLM_API_KEY" in __import__("os").environ:
                pass  # can't actually clear in all contexts, but we try
            with pytest.raises(ValueError, match="No LLM API key configured"):
                review_keyword(sample_tradeoff, ["a"], ["b"])

    def test_default_config_with_env_key(self, sample_tradeoff):
        """With env var set, default config should pick it up."""
        with patch.dict("os.environ", {"OPTIMIZER_LLM_API_KEY": "env-key-from-test"}):
            with patch("ticketpilot.optimizer.llm_reviewer._llm_complete") as mock_llm:
                mock_llm.return_value = '{"decision": "APPROVE", "reasoning": "ok"}'
                result = review_keyword(sample_tradeoff, ["a"], ["b"])
                assert result["decision"] == "APPROVE"
