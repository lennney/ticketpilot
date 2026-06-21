"""Deterministic fake embedding provider — PIPELINE VERIFICATION ONLY.

WARNING: Fake embeddings verify pipeline mechanics (wiring, RRF, trace capture)
but do NOT provide semantic retrieval quality. Cosine similarity between fake
embeddings has no semantic meaning. Real embeddings will replace this provider
in a future phase.
"""

import hashlib
import random
from typing import Protocol

# Fixed embedding dimension for fake embeddings
FAKE_EMBEDDING_DIM = 384


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def embed(self, text: str) -> list[float]:
        """Embed a single text into a vector."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""
        ...


class FakeEmbeddingProvider:
    """
    Deterministic fake embeddings for testing.

    Uses SHA-256 hash of text as seed for random number generator
    to ensure the same text always produces the same embedding.

    Attributes:
        DIM: Embedding dimension (configurable, default 384)
        provider_name: "fake"
        model_name: "sha-256" (indicating deterministic hash-based generation)

    Example:
        >>> provider = FakeEmbeddingProvider()
        >>> vec1 = provider.embed("hello world")
        >>> vec2 = provider.embed("hello world")
        >>> vec1 == vec2  # True - deterministic
    """

    DIM: int
    provider_name: str = "fake"
    model_name: str = "sha-256"
    batch_size: int = 32

    def __init__(self, dimension: int = FAKE_EMBEDDING_DIM):
        self.DIM = dimension

    def embed(self, text: str) -> list[float]:
        """
        Generate a deterministic fake embedding for a single text.

        Uses the first 8 characters of the SHA-256 hash as a hex integer
        to seed the random number generator, ensuring deterministic results.

        Args:
            text: Input text to embed

        Returns:
            List of 384 floats in range [-1, 1]
        """
        # Create deterministic seed from text hash
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(text_hash[:8], 16)
        rng = random.Random(seed)

        # Generate embedding vector
        return [rng.uniform(-1, 1) for _ in range(self.DIM)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate deterministic fake embeddings for a batch of texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors (384-d each)
        """
        return [self.embed(text) for text in texts]


# Singleton instance for convenience
_default_provider: FakeEmbeddingProvider | None = None
_default_provider_dim: int | None = None


def get_fake_embedding_provider(
    dimension: int = FAKE_EMBEDDING_DIM,
) -> FakeEmbeddingProvider:
    """Get the default fake embedding provider instance.

    Args:
        dimension: Embedding dimension (default 384). If the dimension changes,
                   a new provider is created.
    """
    global _default_provider, _default_provider_dim
    if _default_provider is None or _default_provider_dim != dimension:
        _default_provider = FakeEmbeddingProvider(dimension=dimension)
        _default_provider_dim = dimension
    return _default_provider
