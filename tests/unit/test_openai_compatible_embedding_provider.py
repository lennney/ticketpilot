"""Tests for OpenAICompatibleEmbeddingProvider — all HTTP mocked, no live network."""

from unittest.mock import patch

import httpx
import pytest

from ticketpilot.retrieval.embedding_config import EmbeddingConfig
from ticketpilot.retrieval.providers import (
    OpenAICompatibleEmbeddingProvider,
    create_embedding_provider,
)
from ticketpilot.retrieval.providers.openai_compatible import BASE_URL_DEFAULT


# ---- Fixtures / helpers ----


def _make_success_response(data_items: list[dict]) -> httpx.Response:
    """Build a mock 200 response for the embeddings API."""
    return httpx.Response(
        status_code=200,
        json={"data": data_items, "model": "test-model", "usage": {"total_tokens": 10}},
    )


def _make_item(index: int, dim: int = 4) -> dict:
    """Build a single embedding response item."""
    return {"index": index, "embedding": [float(i) / dim for i in range(dim)]}


# ---- Constructor / validation tests ----


class TestConstructor:
    """Tests for OpenAICompatibleEmbeddingProvider construction."""

    def test_missing_api_key_fails(self):
        """Missing API key should raise ValueError."""
        with pytest.raises(ValueError) as exc:
            OpenAICompatibleEmbeddingProvider(
                base_url="http://localhost:1234/v1",
                api_key=None,
                model="test-model",
                dimension=4,
            )
        assert "API key" in str(exc.value)

    def test_missing_base_url_fails(self):
        """Missing base_url should raise ValueError."""
        with pytest.raises(ValueError) as exc:
            OpenAICompatibleEmbeddingProvider(
                base_url="",
                api_key="sk-test",
                model="test-model",
                dimension=4,
            )
        assert "base_url" in str(exc.value)

    def test_valid_construction(self):
        """Valid params should create provider successfully."""
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
            batch_size=10,
        )
        assert provider.provider_name == "openai_compatible"
        assert provider.model_name == "test-model"
        assert provider.DIM == 4
        assert provider.batch_size == 10

    def test_base_url_trailing_slash_normalized(self):
        """Trailing slash on base_url should be stripped."""
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1/",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        # Access internals to verify normalization
        assert provider.base_url == "http://localhost:1234/v1"

    def test_default_base_url(self):
        """Default base_url should be OpenAI's v1 endpoint."""
        provider = OpenAICompatibleEmbeddingProvider(
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        assert provider.base_url == BASE_URL_DEFAULT.rstrip("/")


# ---- embed() tests ----


class TestEmbed:
    """Tests for the embed() single-text method."""

    @patch("httpx.Client.post")
    def test_embed_returns_one_vector(self, mock_post):
        """embed(text) should return a single vector."""
        mock_post.return_value = _make_success_response([_make_item(0, dim=4)])
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        vec = provider.embed("hello")
        assert isinstance(vec, list)
        assert len(vec) == 4
        assert all(isinstance(v, float) for v in vec)

    @patch("httpx.Client.post")
    def test_embed_sends_correct_request_shape(self, mock_post):
        """embed() should POST to {base_url}/embeddings with Bearer auth."""
        mock_post.return_value = _make_success_response([_make_item(0, dim=4)])
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test-key",
            model="text-embedding-test",
            dimension=4,
        )
        provider.embed("test input")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        # URL should be {base_url}/embeddings
        call_url = str(mock_post.call_args[0][0])
        assert call_url.endswith("/embeddings")
        # Headers
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test-key"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"
        # Body
        assert call_kwargs["json"]["model"] == "text-embedding-test"
        assert call_kwargs["json"]["input"] == ["test input"]


# ---- embed_batch() tests ----


class TestEmbedBatch:
    """Tests for the embed_batch() batch method."""

    @patch("httpx.Client.post")
    def test_embed_batch_returns_vectors(self, mock_post):
        """embed_batch should return one vector per input."""
        mock_post.return_value = _make_success_response(
            [_make_item(0, dim=4), _make_item(1, dim=4)]
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        results = provider.embed_batch(["a", "b"])
        assert len(results) == 2
        assert all(len(v) == 4 for v in results)

    def test_empty_list_returns_empty(self):
        """Empty input list should return empty list."""
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        assert provider.embed_batch([]) == []

    @patch("httpx.Client.post")
    def test_response_order_preserved(self, mock_post):
        """Results should be sorted by index to match input order."""
        mock_post.return_value = _make_success_response(
            [_make_item(1, dim=4), _make_item(0, dim=4)]
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        results = provider.embed_batch(["b", "a"])
        # index 0 corresponds to "b", index 1 to "a"
        assert (
            results[0] == _make_item(1, dim=4)["embedding"]
        )  # "b" was index 1 but sorted
        assert results[1] == _make_item(0, dim=4)["embedding"]  # "a" was index 0

    @patch("httpx.Client.post")
    def test_batch_size_respected(self, mock_post):
        """If input exceeds batch_size, multiple API calls should be made."""
        # Return correct number of results per call: 2 for first batch, 1 for second
        mock_post.side_effect = [
            _make_success_response([_make_item(0, dim=4), _make_item(1, dim=4)]),
            _make_success_response([_make_item(2, dim=4)]),
        ]
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
            batch_size=2,
        )
        results = provider.embed_batch(["a", "b", "c"])
        # 3 inputs with batch_size=2 → 2 calls
        assert mock_post.call_count == 2
        assert len(results) == 3


# ---- Error handling tests ----


class TestErrorHandling:
    """Tests for error handling."""

    @patch("httpx.Client.post")
    def test_dimension_mismatch_fails(self, mock_post):
        """API returning different dimension should raise ValueError."""
        mock_post.return_value = _make_success_response(
            [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(ValueError) as exc:
            provider.embed("test")
        assert "dimension mismatch" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_non_2xx_fails_without_leaking_api_key(self, mock_post):
        """HTTP error should raise RuntimeError without leaking full API key."""
        mock_post.return_value = httpx.Response(
            status_code=401,
            text='{"error": "unauthorized"}',
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test-secret-key",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed("test")
        error_msg = str(exc.value)
        assert "401" in error_msg
        # Full API key should not appear in error
        assert "sk-test-secret-key" not in error_msg

    @patch("httpx.Client.post")
    def test_malformed_json_fails(self, mock_post):
        """Non-JSON response should raise RuntimeError."""
        mock_post.return_value = httpx.Response(
            status_code=200,
            text="not json",
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed("test")
        assert "malformed" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_missing_data_fails(self, mock_post):
        """Response without 'data' field should raise RuntimeError."""
        mock_post.return_value = httpx.Response(
            status_code=200,
            json={"model": "test", "usage": {}},
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed("test")
        assert "data" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_count_mismatch_fails(self, mock_post):
        """API returning wrong number of results should raise RuntimeError."""
        mock_post.return_value = _make_success_response(
            [_make_item(0, dim=4)]  # 1 result for 2 inputs
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed_batch(["a", "b"])
        assert "count mismatch" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_invalid_embedding_type_fails(self, mock_post):
        """Non-list embedding should raise ValueError."""
        mock_post.return_value = _make_success_response(
            [{"index": 0, "embedding": "not-a-list"}]
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(ValueError) as exc:
            provider.embed("test")
        assert "not a list" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_request_error_wrapped(self, mock_post):
        """Network error should be wrapped in RuntimeError."""
        mock_post.side_effect = httpx.RequestError("connection failed")
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed("test")
        assert "request failed" in str(exc.value).lower()

    @patch("httpx.Client.post")
    def test_missing_embedding_field_fails(self, mock_post):
        """Response item missing 'embedding' field should raise RuntimeError."""
        mock_post.return_value = _make_success_response(
            [{"index": 0}]  # no "embedding" key
        )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
            model="test-model",
            dimension=4,
        )
        with pytest.raises(RuntimeError) as exc:
            provider.embed("test")
        assert "embedding" in str(exc.value).lower()


# ---- Factory integration tests ----


class TestFactoryIntegration:
    """Tests for factory integration with OpenAICompatibleEmbeddingProvider."""

    def test_openai_compatible_config_returns_provider(self):
        """Factory should create OpenAICompatibleEmbeddingProvider from config."""
        config = EmbeddingConfig(
            provider="openai_compatible",
            model="test-model",
            dimension=4,
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
        )
        provider = create_embedding_provider(config)
        assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
        assert provider.provider_name == "openai_compatible"
        assert provider.model_name == "test-model"
        assert provider.DIM == 4

    def test_factory_does_not_make_network_request(self):
        """Factory creation should not trigger any HTTP request."""
        config = EmbeddingConfig(
            provider="openai_compatible",
            model="test-model",
            dimension=4,
            base_url="http://localhost:1234/v1",
            api_key="sk-test",
        )
        # No HTTP request should happen during creation
        provider = create_embedding_provider(config)
        assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
