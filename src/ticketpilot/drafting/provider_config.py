"""LLM provider configuration and factory.

Follows the same pattern as the embedding provider config:
- Default provider is fake (deterministic, no API key).
- Real providers are opt-in via environment variable.
- API keys are never committed (read from .env.local only).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticketpilot.drafting.llm_provider import LLMProvider


class LLMProviderConfig:
    """Configuration for an LLM draft generation provider.

    Attributes:
        provider_type: Provider identifier ('fake' or future types).
    """

    def __init__(self, provider_type: str = "fake") -> None:
        self.provider_type = provider_type


def load_llm_provider_config() -> LLMProviderConfig:
    """Load LLM provider configuration from environment.

    Reads TICKETPILOT_LLM_PROVIDER env var. Defaults to 'fake'.
    Unknown provider types raise ValueError.

    Returns:
        LLMProviderConfig with provider_type set.

    Raises:
        ValueError: If TICKETPILOT_LLM_PROVIDER is set to an unknown value.
    """
    provider_type = os.environ.get("TICKETPILOT_LLM_PROVIDER", "fake")

    allowed = {"fake"}
    if provider_type not in allowed:
        msg = (
            f"Unknown LLM provider: '{provider_type}'. "
            f"Allowed values: {', '.join(sorted(allowed))}"
        )
        raise ValueError(msg)

    return LLMProviderConfig(provider_type=provider_type)


def create_llm_provider(
    config: LLMProviderConfig | None = None,
) -> LLMProvider:
    """Factory: create an LLMProvider from config.

    Args:
        config: Provider configuration. If None, loaded from environment.

    Returns:
        An LLMProvider instance matching the config.

    Raises:
        ValueError: If config specifies an unknown provider type.
    """
    from ticketpilot.drafting.llm_provider import (
        FakeLLMProvider,
    )

    if config is None:
        config = load_llm_provider_config()

    if config.provider_type == "fake":
        return FakeLLMProvider()

    msg = (
        f"Unknown provider type: '{config.provider_type}'. "
        f"Supported: fake"
    )
    raise ValueError(msg)
