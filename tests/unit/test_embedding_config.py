"""Tests for embedding_config — env loading, .env.local, secret safety."""

import os

import pytest
from dotenv import load_dotenv

from ticketpilot.retrieval.embedding_config import (
    EmbeddingConfig,
    load_embedding_config_from_env,
)


class TestFallbackToFake:
    """When no env or .env.local is present, config must fall back to fake."""

    def test_no_env_no_dotenv_returns_fake(self, monkeypatch):
        for var in [
            "EMBEDDING_PROVIDER",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIM",
            "EMBEDDING_BASE_URL",
            "EMBEDDING_API_KEY",
            "EMBEDDING_BATCH_SIZE",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = load_embedding_config_from_env()
        assert config.provider == "fake"
        assert config.is_fake is True
        assert config.dimension == 384
        assert config.model == "fake-384"
        assert config.api_key is None

    def test_default_config_dataclass_is_fake(self):
        config = EmbeddingConfig()
        assert config.provider == "fake"
        assert config.is_fake is True


class TestDotEnvLocalLoading:
    """When .env.local exists, its values are loaded into os.environ (no override)."""

    def test_dotenv_loads_env_vars(self, tmp_path, monkeypatch):
        dotenv_path = tmp_path / ".env.local"
        dotenv_path.write_text(
            "EMBEDDING_PROVIDER=openai_compatible\n"
            "EMBEDDING_MODEL=text-embedding-v4\n"
            "EMBEDDING_DIM=1024\n"
            "EMBEDDING_BASE_URL=https://dashscope.example.com/v1\n"
            "EMBEDDING_API_KEY=sk-test-dotenv-key-12345\n"
            "EMBEDDING_BATCH_SIZE=10\n"
        )
        # Clear env first
        for var in [
            "EMBEDDING_PROVIDER",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIM",
            "EMBEDDING_BASE_URL",
            "EMBEDDING_API_KEY",
            "EMBEDDING_BATCH_SIZE",
        ]:
            monkeypatch.delenv(var, raising=False)

        load_dotenv(str(dotenv_path), override=False)

        config = load_embedding_config_from_env()
        assert config.provider == "openai_compatible"
        assert config.model == "text-embedding-v4"
        assert config.dimension == 1024
        assert config.base_url == "https://dashscope.example.com/v1"
        assert config.api_key == "sk-test-dotenv-key-12345"
        assert config.batch_size == 10
        assert config.is_fake is False
        assert config.is_openai_compatible is True


class TestShellEnvPriority:
    """Shell environment variables always take priority over .env.local."""

    def test_shell_env_wins_over_dotenv(self, tmp_path, monkeypatch):
        dotenv_path = tmp_path / ".env.local"
        dotenv_path.write_text(
            "EMBEDDING_PROVIDER=fake\nEMBEDDING_MODEL=fake-384\nEMBEDDING_DIM=384\n"
        )
        # Shell env says openai_compatible
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v4")
        monkeypatch.setenv("EMBEDDING_DIM", "1024")

        # load_dotenv with override=False — must not overwrite shell env
        load_dotenv(str(dotenv_path), override=False)

        config = load_embedding_config_from_env()
        assert config.provider == "openai_compatible", (
            "shell env must win over .env.local"
        )
        assert config.model == "text-embedding-v4"
        assert config.dimension == 1024

    def test_shell_api_key_wins_over_dotenv(self, tmp_path, monkeypatch):
        dotenv_path = tmp_path / ".env.local"
        dotenv_path.write_text("EMBEDDING_API_KEY=sk-from-dotenv\n")
        monkeypatch.setenv("EMBEDDING_API_KEY", "sk-from-shell")

        load_dotenv(str(dotenv_path), override=False)

        assert os.environ.get("EMBEDDING_API_KEY") == "sk-from-shell", (
            "shell env API key must not be overridden by .env.local"
        )


class TestApiKeyNotLeaked:
    """API key must never appear in repr, logs, or error messages."""

    def test_repr_does_not_contain_api_key(self):
        config = EmbeddingConfig(
            provider="openai_compatible",
            api_key="sk-secret-value-abc123",
        )
        r = repr(config)
        assert "sk-secret-value-abc123" not in r, f"repr leaked API key: {r}"
        assert "****" in r, f"repr should show masked key: {r}"

    def test_repr_with_no_api_key_shows_none(self):
        config = EmbeddingConfig(provider="fake")
        r = repr(config)
        assert "api_key=None" in r, f"repr for no key: {r}"
        assert "****" not in r, "**** should not appear when api_key is None"

    def test_str_does_not_contain_api_key(self):
        config = EmbeddingConfig(
            provider="openai_compatible",
            api_key="sk-another-secret",
        )
        s = str(config)
        assert "sk-another-secret" not in s, f"str leaked API key: {s}"

    def test_factory_error_does_not_print_key(self):
        config = EmbeddingConfig(
            provider="openai_compatible",
            model="text-embedding-v4",
            dimension=1024,
            base_url="https://api.example.com/v1",
        )
        # This config has no api_key — factory should complain about missing key,
        # but must NOT print the key value (which is None here anyway)
        from ticketpilot.retrieval.providers import create_embedding_provider

        with pytest.raises(ValueError) as exc:
            create_embedding_provider(config)
        msg = str(exc.value)
        assert "API key" in msg
        # Message should not contain any "sk-" pattern
        assert "sk-" not in msg, f"error message contains sk- prefix: {msg}"


class TestModuleLevelDotenvPath:
    """Verify the module correctly resolves the project-root .env.local path."""

    def test_dotenv_path_is_project_root(self):
        import ticketpilot.retrieval.embedding_config as ec

        env_local_path = ec._env_local  # type: Path
        assert env_local_path.name == ".env.local"
        # The parent should be the project root (contains pyproject.toml)
        assert (env_local_path.parent / "pyproject.toml").exists(), (
            f"{env_local_path.parent} should be project root (contain pyproject.toml)"
        )
