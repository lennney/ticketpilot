"""Local embedding provider using sentence-transformers.

Uses BGE-small-zh-v1.5 model for Chinese text embedding.
No API key required, runs locally.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Cache the model to avoid reloading
_model_cache: dict[str, object] = {}


class LocalEmbeddingProvider:
    """Local embedding provider using sentence-transformers.

    Uses BAAI/bge-small-zh-v1.5 model for Chinese text embedding.
    No API key required, runs locally on CPU.

    Attributes:
        provider_name: Provider identifier.
        model_name: Model name.
        dimension: Embedding dimension.
    """

    DIM = 512  # Class-level constant for rebuild_embeddings.py compatibility

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        dimension: int = 512,
    ) -> None:
        self.provider_name = "local"
        self.model_name = model_name
        self.dimension = dimension
        self.DIM = dimension  # Instance-level override
        self.batch_size = 32
        self._model = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                if self.model_name not in _model_cache:
                    logger.info("Loading local embedding model: %s", self.model_name)
                    _model_cache[self.model_name] = SentenceTransformer(self.model_name)
                    logger.info("Model loaded successfully")

                self._model = _model_cache[self.model_name]
            except ImportError:
                msg = (
                    "sentence-transformers is required for local embedding. "
                    "Install it with: uv pip install sentence-transformers"
                )
                raise ImportError(msg)
        return self._model

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return embeddings.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Alias for embed_texts — used by rebuild_embeddings.py."""
        return self.embed_texts(texts)


def get_local_embedding_provider(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    dimension: int = 512,
) -> LocalEmbeddingProvider:
    """Get a local embedding provider instance.

    Args:
        model_name: Model name (default: BAAI/bge-small-zh-v1.5)
        dimension: Embedding dimension (default: 512)

    Returns:
        LocalEmbeddingProvider instance.
    """
    return LocalEmbeddingProvider(model_name=model_name, dimension=dimension)
