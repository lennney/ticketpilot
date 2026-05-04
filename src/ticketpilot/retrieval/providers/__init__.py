"""Retrieval providers module.

Provider factory and all embedding provider implementations.
FakeEmbeddingProvider is the default; real providers are opt-in.
"""

from ticketpilot.retrieval.embedding_config import EmbeddingConfig
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider

__all__ = [
    "FakeEmbeddingProvider",
    "create_embedding_provider",
    "get_embedding_provider",
]


def _get_provider_dimension(provider) -> int:
    """Get the effective dimension from a provider instance."""
    return provider.DIM if hasattr(provider, "DIM") else len(provider.embed(""))


def create_embedding_provider(config: EmbeddingConfig) -> FakeEmbeddingProvider:
    """Create an embedding provider based on configuration.

    Args:
        config: Embedding configuration with provider selection.

    Returns:
        An EmbeddingProvider instance.

    Raises:
        ValueError: If the provider type is unknown.
        ValueError: If the config dimension does not match the provider dimension.
    """
    provider_name = config.provider

    if provider_name == "fake":
        provider = FakeEmbeddingProvider()
    elif provider_name == "openai_compatible":
        raise NotImplementedError(
            "OpenAI-compatible provider is not yet implemented. "
            "It will be available in Phase 8 Batch 3."
        )
    else:
        raise ValueError(
            f"Unknown embedding provider: '{provider_name}'. "
            f"Supported values: 'fake', 'openai_compatible'."
        )

    # Validate dimension: fail loudly on mismatch
    actual_dim = _get_provider_dimension(provider)
    if actual_dim != config.dimension:
        raise ValueError(
            f"Dimension mismatch: configured EMBEDDING_DIM={config.dimension} "
            f"but provider '{provider_name}' (model: {config.model}) "
            f"produces dimension {actual_dim}. "
            f"Set EMBEDDING_DIM={actual_dim} or use a different provider."
        )

    return provider


# Module-level singleton cache
_default_config: EmbeddingConfig | None = None
_default_provider: FakeEmbeddingProvider | None = None


def get_embedding_provider(
    config: EmbeddingConfig | None = None,
) -> FakeEmbeddingProvider:
    """Get the embedding provider (cached singleton per config).

    Args:
        config: Optional config override. If None, loads from env defaults.

    Returns:
        An EmbeddingProvider instance.
    """
    global _default_config, _default_provider

    if config is None:
        from ticketpilot.retrieval.embedding_config import load_embedding_config_from_env

        config = load_embedding_config_from_env()

    # Return cached provider only if config matches
    if _default_provider is not None and _default_config == config:
        return _default_provider

    _default_config = config
    _default_provider = create_embedding_provider(config)
    return _default_provider
