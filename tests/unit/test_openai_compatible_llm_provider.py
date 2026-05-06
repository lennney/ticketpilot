"""Unit tests for OpenAICompatibleProvider.

Mock-only tests — no network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from ticketpilot.drafting.llm_provider import (
    LLMProvider,
    OpenAICompatibleProvider,
)
from ticketpilot.drafting.provider_config import (
    LLMProviderConfig,
    create_llm_provider,
    load_llm_provider_config,
)
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType
from uuid import uuid4


def _make_evidence(
    rank: int = 1,
    score: float = 0.8,
    content: str = "退货需要在7天内申请。",
    doc_type: DocType = DocType.FAQ,
) -> MagicMock:
    ev = MagicMock()
    ev.chunk_id = uuid4()
    ev.doc_id = uuid4()
    ev.doc_type = doc_type
    ev.source_table = f"knowledge_{doc_type.value.lower()}"
    ev.source_id = str(ev.doc_id)
    ev.content = content
    ev.score = score
    ev.rank = rank
    ev.title = None
    return ev


class TestOpenAICompatibleProviderInterface:
    def test_is_llm_provider_subclass(self):
        assert issubclass(OpenAICompatibleProvider, LLMProvider)

    def test_provider_name(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test-key",
            model="gpt-4o-mini",
        )
        assert provider.provider_name == "openai_compatible"

    def test_model_name(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test-key",
            model="gpt-4o-mini",
        )
        assert provider.model_name == "gpt-4o-mini"

    def test_repr_does_not_expose_api_key(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-secret-key-12345",
            model="gpt-4o-mini",
        )
        repr_str = repr(provider)
        assert "sk-secret-key-12345" not in repr_str
        assert "sk-" not in repr_str

    def test_repr_shows_base_url_and_model(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        repr_str = repr(provider)
        assert "api.example.com" in repr_str
        assert "gpt-4o-mini" in repr_str


class TestOpenAICompatibleProviderGenerateDraft:
    def test_mapped_response_returns_draft_reply(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        evidence = [_make_evidence()]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_context.read.return_value = b'{"choices":[{"message":{"content":"Hello, regarding your refund request, we will process it within 1-3 business days."}}]}'
            mock_urlopen.return_value = mock_context

            result = provider.generate_draft(
                normalized_text="我要退款",
                issue_type="refund",
                evidence_candidates=evidence,
            )

        assert isinstance(result, DraftReply)
        assert result.draft_text == "Hello, regarding your refund request, we will process it within 1-3 business days."
        assert result.provider_id == "openai_compatible"
        assert result.confidence == 0.7

    def test_invalid_json_triggers_safe_fallback(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        evidence = [_make_evidence()]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_context.read.return_value = b"not valid json"
            mock_urlopen.return_value = mock_context

            result = provider.generate_draft(
                normalized_text="我要退款",
                issue_type="refund",
                evidence_candidates=evidence,
            )

        assert result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert result.must_human_review is True
        assert result.fallback_reason == "api_error"
        assert result.escalation_reason == "api_call_failed"

    def test_network_error_triggers_safe_fallback(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        evidence = [_make_evidence()]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = OSError("Connection refused")

            result = provider.generate_draft(
                normalized_text="我要退款",
                issue_type="refund",
                evidence_candidates=evidence,
            )

        assert result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert result.must_human_review is True
        assert result.fallback_reason == "api_error"
        assert result.escalation_reason == "api_call_failed"

    def test_timeout_error_triggers_safe_fallback(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
            timeout_seconds=5,
        )
        evidence = [_make_evidence()]

        with patch("urllib.request.urlopen") as mock_urlopen:
            import urllib.error
            mock_urlopen.side_effect = urllib.error.URLError("timed out")

            result = provider.generate_draft(
                normalized_text="我要退款",
                issue_type="refund",
                evidence_candidates=evidence,
            )

        assert result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert result.must_human_review is True
        assert result.fallback_reason == "api_error"

    def test_no_evidence_returns_safe_fallback(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )

        result = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
            evidence_candidates=[],
        )

        assert result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert result.must_human_review is True
        assert result.fallback_reason == "no_evidence"
        assert result.confidence == 0.0

    def test_risk_flags_trigger_human_review(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        evidence = [_make_evidence()]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_context.read.return_value = b'{"choices":[{"message":{"content":"Hello"}}]}'
            mock_urlopen.return_value = mock_context

            result = provider.generate_draft(
                normalized_text="我要退款",
                issue_type="refund",
                risk_flags=["privacy_risk"],
                evidence_candidates=evidence,
            )

        assert result.must_human_review is True
        assert result.escalation_reason == "risk_flags: privacy_risk"
        assert any("privacy_risk" in note for note in result.safety_notes)


class TestLLMProviderConfig:
    def test_config_repr_does_not_expose_api_key(self):
        config = LLMProviderConfig(
            provider_type="openai_compatible",
            base_url="https://api.example.com",
            api_key="sk-secret-12345",
            model="gpt-4o-mini",
        )
        repr_str = repr(config)
        assert "sk-secret-12345" not in repr_str
        assert "sk-" not in repr_str

    def test_config_repr_shows_base_url_and_model(self):
        config = LLMProviderConfig(
            provider_type="openai_compatible",
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
        )
        repr_str = repr(config)
        assert "api.example.com" in repr_str
        assert "gpt-4o-mini" in repr_str


class TestLoadLLMProviderConfig:
    def test_defaults_to_fake(self):
        with patch.dict("os.environ", {}, clear=True):
            config = load_llm_provider_config()
            assert config.provider_type == "fake"

    def test_openai_compatible_requires_base_url(self):
        with patch.dict(
            "os.environ",
            {
                "TICKETPILOT_LLM_PROVIDER": "openai_compatible",
                "TICKETPILOT_LLM_API_KEY": "sk-test",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="TICKETPILOT_LLM_BASE_URL"):
                load_llm_provider_config()

    def test_openai_compatible_requires_api_key(self):
        with patch.dict(
            "os.environ",
            {
                "TICKETPILOT_LLM_PROVIDER": "openai_compatible",
                "TICKETPILOT_LLM_BASE_URL": "https://api.example.com",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="TICKETPILOT_LLM_API_KEY"):
                load_llm_provider_config()

    def test_openai_compatible_with_valid_env(self):
        with patch.dict(
            "os.environ",
            {
                "TICKETPILOT_LLM_PROVIDER": "openai_compatible",
                "TICKETPILOT_LLM_BASE_URL": "https://api.example.com",
                "TICKETPILOT_LLM_API_KEY": "sk-test",
                "TICKETPILOT_LLM_MODEL": "gpt-4o",
                "TICKETPILOT_LLM_TIMEOUT_SECONDS": "60",
                "TICKETPILOT_LLM_MAX_TOKENS": "1024",
                "TICKETPILOT_LLM_TEMPERATURE": "0.5",
            },
            clear=True,
        ):
            config = load_llm_provider_config()
            assert config.provider_type == "openai_compatible"
            assert config.base_url == "https://api.example.com"
            assert config.api_key == "sk-test"
            assert config.model == "gpt-4o"
            assert config.timeout_seconds == 60
            assert config.max_tokens == 1024
            assert config.temperature == 0.5

    def test_unknown_provider_raises_valueerror(self):
        with patch.dict(
            "os.environ",
            {"TICKETPILOT_LLM_PROVIDER": "unknown_provider"},
            clear=True,
        ):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                load_llm_provider_config()


class TestCreateLLMProvider:
    def test_create_fake_provider(self):
        config = LLMProviderConfig(provider_type="fake")
        provider = create_llm_provider(config)
        assert provider.provider_name == "fake"
        assert provider.model_name == "fake"

    def test_create_openai_compatible_provider(self):
        config = LLMProviderConfig(
            provider_type="openai_compatible",
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o-mini",
            timeout_seconds=30,
            max_tokens=512,
            temperature=0.3,
        )
        provider = create_llm_provider(config)
        assert provider.provider_name == "openai_compatible"
        assert provider.model_name == "gpt-4o-mini"