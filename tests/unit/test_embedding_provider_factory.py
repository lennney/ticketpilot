"""Tests for embedding provider config and factory."""

import pytest

from ticketpilot.retrieval.embedding_config import (
    EmbeddingConfig,
    load_embedding_config_from_env,
)
from ticketpilot.retrieval.providers import (
    FakeEmbeddingProvider,
    create_embedding_provider,
    get_embedding_provider,
)


class TestEmbeddingConfigDefaults:
    """Tests for embedding config default values."""

    def test_default_provider_is_fake(self):
        """Default provider should be 'fake'."""
        config = EmbeddingConfig()
        assert config.provider == "fake"
        assert config.is_fake is True
        assert config.is_openai_compatible is False

    def test_default_dimension_is_384(self):
        """Default dimension should be 384."""
        config = EmbeddingConfig()
        assert config.dimension == 384

    def test_default_model_is_fake_384(self):
        """Default model should be 'fake-384'."""
        config = EmbeddingConfig()
        assert config.model == "fake-384"

    def test_default_batch_size_is_32(self):
        """Default batch size should be 32."""
        config = EmbeddingConfig()
        assert config.batch_size == 32

    def test_default_base_url_is_none(self):
        """Default base_url should be None."""
        config = EmbeddingConfig()
        assert config.base_url is None

    def test_default_api_key_is_none(self):
        """Default api_key should be None."""
        config = EmbeddingConfig()
        assert config.api_key is None


class TestLoadConfigFromEnv:
    """Tests for loading config from environment variables."""

    def test_load_defaults_when_no_env(self, monkeypatch):
        """Loading config with no env vars should return defaults."""
        for var in ["EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_DIM",
                     "EMBEDDING_BASE_URL", "EMBEDDING_API_KEY", "EMBEDDING_BATCH_SIZE"]:
            monkeypatch.delenv(var, raising=False)

        config = load_embedding_config_from_env()
        assert config.provider == "fake"
        assert config.dimension == 384
        assert config.model == "fake-384"
        assert config.batch_size == 32

    def test_load_custom_provider(self, monkeypatch):
        """Loading config with custom provider should work."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
        monkeypatch.setenv("EMBEDDING_DIM", "1536")
        monkeypatch.setenv("EMBEDDING_BASE_URL", "http://localhost:1234/v1")
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "10")

        config = load_embedding_config_from_env()
        assert config.provider == "openai_compatible"
        assert config.model == "text-embedding-3-small"
        assert config.dimension == 1536
        assert config.base_url == "http://localhost:1234/v1"
        assert config.batch_size == 10
        assert config.is_fake is False
        assert config.is_openai_compatible is True


class TestProviderFactory:
    """Tests for the provider factory."""

    def test_fake_config_returns_fake_provider(self):
        """Fake config should return FakeEmbeddingProvider."""
        config = EmbeddingConfig(provider="fake")
        provider = create_embedding_provider(config)
        assert isinstance(provider, FakeEmbeddingProvider)

    def test_fake_provider_dimension_is_384(self):
        """Fake provider should have dimension 384."""
        provider = FakeEmbeddingProvider()
        assert provider.DIM == 384
        vec = provider.embed("test")
        assert len(vec) == 384

    def test_openai_compatible_missing_api_key_fails(self):
        """OpenAI-compatible provider without API key should raise ValueError."""
        config = EmbeddingConfig(
            provider="openai_compatible",
            model="text-embedding-3-small",
            dimension=1536,
            base_url="http://localhost:1234/v1",
        )
        with pytest.raises(ValueError) as exc:
            create_embedding_provider(config)
        assert "API key" in str(exc.value)

    def test_openai_compatible_missing_base_url_uses_default(self):
        """Factory should use default base_url when none configured."""
        config = EmbeddingConfig(
            provider="openai_compatible",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        # Factory provides default base_url, so this should succeed
        provider = create_embedding_provider(config)
        assert provider.provider_name == "openai_compatible"

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider should raise ValueError."""
        config = EmbeddingConfig(provider="unknown_provider")
        with pytest.raises(ValueError) as exc:
            create_embedding_provider(config)
        assert "unknown" in str(exc.value).lower()


class TestDimensionMismatch:
    """Tests for dimension mismatch detection."""

    def test_dimension_mismatch_raises_value_error(self):
        """Config dimension different from provider dimension should fail."""
        config = EmbeddingConfig(provider="fake", dimension=768)
        with pytest.raises(ValueError) as exc:
            create_embedding_provider(config)
        assert "dimension mismatch" in str(exc.value).lower()
        assert "768" in str(exc.value)
        assert "384" in str(exc.value)

    def test_dimension_match_succeeds(self):
        """Config dimension matching provider dimension should succeed."""
        config = EmbeddingConfig(provider="fake", dimension=384)
        provider = create_embedding_provider(config)
        assert isinstance(provider, FakeEmbeddingProvider)


class TestGetEmbeddingProvider:
    """Tests for the singleton get_embedding_provider function."""

    def test_get_default_provider(self, monkeypatch):
        """Getting default provider should return FakeEmbeddingProvider."""
        for var in ["EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_DIM",
                     "EMBEDDING_BASE_URL", "EMBEDDING_API_KEY", "EMBEDDING_BATCH_SIZE"]:
            monkeypatch.delenv(var, raising=False)

        provider = get_embedding_provider()
        assert isinstance(provider, FakeEmbeddingProvider)

    def test_get_provider_with_config(self):
        """Getting provider with explicit config should respect it."""
        config = EmbeddingConfig(provider="fake", dimension=384)
        provider = get_embedding_provider(config)
        assert isinstance(provider, FakeEmbeddingProvider)

    def test_no_network_required(self):
        """Tests must not require network access."""
        provider = FakeEmbeddingProvider()
        vec = provider.embed("no network test")
        assert len(vec) == 384

    def test_no_api_key_required(self):
        """Tests must not require API key."""
        provider = FakeEmbeddingProvider()
        vec = provider.embed("no api key test")
        assert len(vec) == 384
