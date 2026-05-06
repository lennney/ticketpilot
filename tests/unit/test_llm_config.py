"""Unit tests for LLM provider configuration."""

import os

import pytest

from ticketpilot.drafting.llm_provider import FakeLLMProvider
from ticketpilot.drafting.provider_config import (
    LLMProviderConfig,
    create_llm_provider,
    load_llm_provider_config,
)


class TestLLMProviderConfig:
    def test_default_config_is_fake(self):
        # Ensure env var is not set
        os.environ.pop("TICKETPILOT_LLM_PROVIDER", None)
        config = load_llm_provider_config()
        assert config.provider_type == "fake"

    def test_fake_config_returns_fake(self):
        os.environ["TICKETPILOT_LLM_PROVIDER"] = "fake"
        config = load_llm_provider_config()
        assert config.provider_type == "fake"

    def test_unknown_provider_raises_value_error(self):
        os.environ["TICKETPILOT_LLM_PROVIDER"] = "openai"
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            load_llm_provider_config()

    def test_unknown_provider_type_raises_value_error(self):
        os.environ["TICKETPILOT_LLM_PROVIDER"] = "claude"
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            load_llm_provider_config()


class TestCreateLLMProvider:
    def test_create_fake_provider_default(self):
        os.environ.pop("TICKETPILOT_LLM_PROVIDER", None)
        provider = create_llm_provider()
        assert isinstance(provider, FakeLLMProvider)
        assert provider.provider_name == "fake"

    def test_create_fake_provider_explicit(self):
        config = LLMProviderConfig(provider_type="fake")
        provider = create_llm_provider(config)
        assert isinstance(provider, FakeLLMProvider)

    def test_unknown_type_raises_value_error(self):
        config = LLMProviderConfig(provider_type="openai")
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_llm_provider(config)


class TestDraftReplyExtended:
    """Tests for new DraftReply fields and cross-field validation."""

    def test_new_fields_defaults(self):
        from ticketpilot.drafting.schemas import DraftReply

        dr = DraftReply(ticket_id="tkt-001", draft_text="您好")
        assert dr.provider_id == ""
        assert dr.escalation_reason is None
        assert dr.safety_notes == []
        assert dr.cited_evidence_ids == []

    def test_provider_id_stored(self):
        from ticketpilot.drafting.schemas import DraftReply

        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="您好",
            provider_id="fake",
        )
        assert dr.provider_id == "fake"

    def test_unsupported_claims_auto_sets_must_human_review(self):
        from ticketpilot.drafting.schemas import DraftReply

        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="您好",
            unsupported_claims=["缺少退款政策引用"],
        )
        assert dr.must_human_review is True

    def test_escalation_reason_auto_sets_must_human_review(self):
        from ticketpilot.drafting.schemas import DraftReply

        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="您好",
            escalation_reason="legal_risk_detected",
        )
        assert dr.must_human_review is True

    def test_cited_evidence_ids_empty_string_rejected(self):
        from pydantic import ValidationError
        from ticketpilot.drafting.schemas import DraftReply

        with pytest.raises(ValidationError):
            DraftReply(
                ticket_id="tkt-001",
                draft_text="您好",
                cited_evidence_ids=["valid-id", ""],
            )

    def test_empty_draft_text_rejected(self):
        from pydantic import ValidationError
        from ticketpilot.drafting.schemas import DraftReply

        with pytest.raises(ValidationError):
            DraftReply(ticket_id="tkt-001", draft_text="")
