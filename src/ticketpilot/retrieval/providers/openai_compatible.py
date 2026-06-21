"""OpenAI-compatible embedding provider.

Implement the OpenAI-compatible embeddings API format
(e.g., DashScope text-embedding-v4, OpenAI text-embedding-3-*).
Provider name: "openai_compatible"
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL_DEFAULT = "https://api.openai.com/v1"


class OpenAICompatibleEmbeddingProvider:
    """Embedding provider for OpenAI-compatible APIs.

    Args:
        base_url: API base URL (e.g., "https://api.openai.com/v1")
        api_key: API key for authentication
        model: Model name (e.g., "text-embedding-v4", "text-embedding-3-small")
        dimension: Expected embedding vector dimension
        batch_size: Max texts per API request
    """

    provider_name: str = "openai_compatible"

    def __init__(
        self,
        base_url: str = BASE_URL_DEFAULT,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimension: int = 768,
        batch_size: int = 32,
    ) -> None:
        if not api_key:
            raise ValueError(
                "API key is required for openai_compatible provider. "
                "Set EMBEDDING_API_KEY in environment or .env.local."
            )
        if not base_url:
            raise ValueError(
                "base_url is required for openai_compatible provider. "
                "Set EMBEDDING_BASE_URL in environment."
            )

        # Normalize base_url: strip trailing slash
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.DIM = dimension
        self.model_name = model
        self.batch_size = batch_size

    def embed(self, text: str) -> list[float]:
        """Embed a single text into a vector.

        Args:
            text: Input text to embed

        Returns:
            List of floats (the embedding vector)
        """
        results = self.embed_batch([text])
        if not results:
            raise RuntimeError("Embedding returned empty result for single text")
        return results[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If dimension mismatch is detected
            RuntimeError: If API call fails or response is malformed
        """
        if not texts:
            return []

        # Split into sub-batches if needed
        all_results: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            batch_results = self._call_api(batch)
            all_results.extend(batch_results)

        return all_results

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Make the actual API call to the embeddings endpoint.

        Args:
            texts: Batch of texts to embed (already within batch_size limit)

        Returns:
            List of embedding vectors in input order
        """

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }

        try:
            # SSL verification disabled per-client only (not global env)
            with httpx.Client(timeout=60.0, verify=False) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Embedding API request failed: {e.__class__.__name__}"
            ) from e

        if response.status_code != 200:
            # Build a safe error message without leaking the full API key
            safe_msg = (
                f"Embedding API returned status {response.status_code}: "
                f"{response.text[:200]}"
            )
            raise RuntimeError(safe_msg)

        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"Embedding API returned malformed JSON: {e}") from e

        if "data" not in data or not isinstance(data["data"], list):
            raise RuntimeError("Embedding API response missing 'data' field")

        # Sort by index to preserve input order
        data_items = sorted(data["data"], key=lambda x: x.get("index", 0))

        if len(data_items) != len(texts):
            raise RuntimeError(
                f"Embedding API returned {len(data_items)} results "
                f"for {len(texts)} inputs — count mismatch"
            )

        results: list[list[float]] = []
        for item in data_items:
            embedding = item.get("embedding")
            if embedding is None:
                raise RuntimeError(
                    "Embedding API response item missing 'embedding' field"
                )
            if not isinstance(embedding, list):
                raise ValueError(
                    f"Embedding is not a list: got {type(embedding).__name__}"
                )
            # Normalize int → float if needed
            vec = [float(v) for v in embedding]
            if len(vec) != self.DIM:
                raise ValueError(
                    f"Dimension mismatch: configured EMBEDDING_DIM={self.DIM} "
                    f"but provider '{self.provider_name}' (model: {self.model}) "
                    f"returned dimension {len(vec)}. "
                    f"Set EMBEDDING_DIM={len(vec)} or use a different model."
                )
            results.append(vec)

        return results
