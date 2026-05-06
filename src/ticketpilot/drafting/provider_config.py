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
        provider_type: Provider identifier ('fake', 'openai_compatible').
    """

    def __init__(
        self,
        provider_type: str = "fake",
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 30,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        self.provider_type = provider_type
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature

    def __repr__(self) -> str:
        """Safe repr that does not expose API key."""
        return (
            f"LLMProviderConfig(provider_type={self.provider_type!r}, "
            f"base_url={self.base_url!r}, model={self.model!r})"
        )


def load_llm_provider_config() -> LLMProviderConfig:
    """Load LLM provider configuration from environment.

    Reads TICKETPILOT_LLM_* env vars. Defaults to 'fake'.
    Unknown provider types raise ValueError.
    openai_compatible requires TICKETPILOT_LLM_BASE_URL and TICKETPILOT_LLM_API_KEY.

    Returns:
        LLMProviderConfig with provider_type and optional real provider settings.

    Raises:
        ValueError: If provider type unknown or required env vars missing.
    """
    provider_type = os.environ.get("TICKETPILOT_LLM_PROVIDER", "fake")

    allowed = {"fake", "openai_compatible"}
    if provider_type not in allowed:
        msg = (
            f"Unknown LLM provider: '{provider_type}'. "
            f"Allowed values: {', '.join(sorted(allowed))}"
        )
        raise ValueError(msg)

    if provider_type == "openai_compatible":
        base_url = os.environ.get("TICKETPILOT_LLM_BASE_URL")
        api_key = os.environ.get("TICKETPILOT_LLM_API_KEY")

        if not base_url:
            msg = "TICKETPILOT_LLM_BASE_URL is required when TICKETPILOT_LLM_PROVIDER=openai_compatible"
            raise ValueError(msg)
        if not api_key:
            msg = "TICKETPILOT_LLM_API_KEY is required when TICKETPILOT_LLM_PROVIDER=openai_compatible"
            raise ValueError(msg)

        model = os.environ.get("TICKETPILOT_LLM_MODEL", "gpt-4o-mini")
        timeout = int(os.environ.get("TICKETPILOT_LLM_TIMEOUT_SECONDS", "30"))
        max_tokens = int(os.environ.get("TICKETPILOT_LLM_MAX_TOKENS", "512"))
        temperature = float(os.environ.get("TICKETPILOT_LLM_TEMPERATURE", "0.3"))

        return LLMProviderConfig(
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
        )

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
        OpenAICompatibleProvider,
    )

    if config is None:
        config = load_llm_provider_config()

    if config.provider_type == "fake":
        return FakeLLMProvider()

    if config.provider_type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=config.base_url or "",
            api_key=config.api_key or "",
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

    msg = (
        f"Unknown provider type: '{config.provider_type}'. "
        f"Supported: fake, openai_compatible"
    )
    raise ValueError(msg)
