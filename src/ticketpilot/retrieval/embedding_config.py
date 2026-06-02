"""Embedding provider configuration — loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env.local from project root (two levels up from this file)
_env_local = Path(__file__).resolve().parent.parent.parent.parent / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local)


# Environment variable names (matching OpenSpec config spec)
ENV_PROVIDER = "EMBEDDING_PROVIDER"
ENV_MODEL = "EMBEDDING_MODEL"
ENV_DIM = "EMBEDDING_DIM"
ENV_BASE_URL = "EMBEDDING_BASE_URL"
ENV_API_KEY = "EMBEDDING_API_KEY"
ENV_BATCH_SIZE = "EMBEDDING_BATCH_SIZE"

# Safe defaults
_DEFAULT_PROVIDER = "fake"
_DEFAULT_MODEL = "fake-384"
_DEFAULT_DIM = 384
_DEFAULT_BATCH_SIZE = 32


@dataclass
class EmbeddingConfig:
    """Embedding provider configuration.

    Fields:
        provider: Provider name ("fake" or "openai_compatible")
        model: Model name
        dimension: Expected embedding vector dimension
        base_url: Optional API base URL (for openai_compatible)
        api_key: Optional API key (for openai_compatible)
        batch_size: Batch size for embed_texts
    """

    provider: str = _DEFAULT_PROVIDER
    model: str = _DEFAULT_MODEL
    dimension: int = _DEFAULT_DIM
    base_url: str | None = None
    api_key: str | None = None
    batch_size: int = _DEFAULT_BATCH_SIZE

    @property
    def is_fake(self) -> bool:
        """Whether the configured provider is fake."""
        return self.provider == "fake"

    @property
    def is_openai_compatible(self) -> bool:
        """Whether the configured provider is OpenAI-compatible."""
        return self.provider == "openai_compatible"

    @property
    def is_local(self) -> bool:
        """Whether the configured provider is local (sentence-transformers)."""
        return self.provider == "local"

    def __repr__(self) -> str:
        """Safe repr — redacts api_key."""
        key_display = "****" if self.api_key else None
        return (
            f"EmbeddingConfig(provider={self.provider!r}, model={self.model!r}, "
            f"dimension={self.dimension}, base_url={self.base_url!r}, "
            f"api_key={key_display!r}, batch_size={self.batch_size})"
        )


def load_embedding_config_from_env() -> EmbeddingConfig:
    """Load embedding config from environment variables.

    Returns:
        EmbeddingConfig populated from environment (or defaults).
    """
    return EmbeddingConfig(
        provider=os.environ.get(ENV_PROVIDER, _DEFAULT_PROVIDER),
        model=os.environ.get(ENV_MODEL, _DEFAULT_MODEL),
        dimension=int(os.environ.get(ENV_DIM, str(_DEFAULT_DIM))),
        base_url=os.environ.get(ENV_BASE_URL),
        api_key=os.environ.get(ENV_API_KEY),
        batch_size=int(os.environ.get(ENV_BATCH_SIZE, str(_DEFAULT_BATCH_SIZE))),
    )
