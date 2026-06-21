"""Tests for FakeEmbeddingProvider determinism."""

from ticketpilot.retrieval.providers.fake_embedding import (
    FAKE_EMBEDDING_DIM,
    FakeEmbeddingProvider,
)


class TestFakeEmbeddingDeterminism:
    """Tests for FakeEmbeddingProvider determinism."""

    def test_same_text_produces_same_embedding(self):
        """Test that the same text always produces the same embedding."""
        provider = FakeEmbeddingProvider()
        text = "hello world"

        vec1 = provider.embed(text)
        vec2 = provider.embed(text)

        assert vec1 == vec2, "Same text must produce identical embeddings"

    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        provider = FakeEmbeddingProvider()

        vec1 = provider.embed("hello world")
        vec2 = provider.embed("hello world!")

        assert vec1 != vec2, "Different texts must produce different embeddings"

    def test_embedding_dimension_is_384(self):
        """Test that embeddings have the correct dimension."""
        provider = FakeEmbeddingProvider()

        vec = provider.embed("test text")

        assert len(vec) == FAKE_EMBEDDING_DIM, (
            f"Expected {FAKE_EMBEDDING_DIM} dimensions, got {len(vec)}"
        )

    def test_batch_embedding_is_deterministic(self):
        """Test that batch embeddings are deterministic."""
        provider = FakeEmbeddingProvider()
        texts = ["apple", "banana", "cherry"]

        batch1 = provider.embed_batch(texts)
        batch2 = provider.embed_batch(texts)

        assert batch1 == batch2, "Batch embeddings must be deterministic"

    def test_batch_size_matches_input(self):
        """Test that batch returns correct number of embeddings."""
        provider = FakeEmbeddingProvider()
        texts = ["a", "b", "c", "d", "e"]

        batch = provider.embed_batch(texts)

        assert len(batch) == len(texts), (
            f"Expected {len(texts)} embeddings, got {len(batch)}"
        )

    def test_embedding_values_in_range(self):
        """Test that embedding values are in range [-1, 1]."""
        provider = FakeEmbeddingProvider()

        vec = provider.embed("test text")

        for i, val in enumerate(vec):
            assert -1.0 <= val <= 1.0, f"Value at index {i} is out of range: {val}"

    def test_empty_string_is_valid(self):
        """Test that empty string produces valid embedding."""
        provider = FakeEmbeddingProvider()

        vec = provider.embed("")

        assert len(vec) == FAKE_EMBEDDING_DIM, (
            "Empty string must produce valid embedding"
        )

    def test_chinese_text_is_deterministic(self):
        """Test that Chinese text embeddings are deterministic."""
        provider = FakeEmbeddingProvider()
        chinese_text = "退款申请如何处理？"

        vec1 = provider.embed(chinese_text)
        vec2 = provider.embed(chinese_text)

        assert vec1 == vec2, "Chinese text must produce deterministic embeddings"

    def test_long_text_is_deterministic(self):
        """Test that long text embeddings are deterministic."""
        provider = FakeEmbeddingProvider()
        long_text = "A" * 10000

        vec1 = provider.embed(long_text)
        vec2 = provider.embed(long_text)

        assert vec1 == vec2, "Long text must produce deterministic embeddings"

    def test_provider_name_is_fake(self):
        """Test that FakeEmbeddingProvider reports correct provider_name."""
        provider = FakeEmbeddingProvider()
        assert provider.provider_name == "fake"

    def test_model_name_is_sha_256(self):
        """Test that FakeEmbeddingProvider reports correct model_name."""
        provider = FakeEmbeddingProvider()
        assert provider.model_name == "sha-256"

    def test_provider_singleton_reuse(self):
        """Test that singleton provider produces same results."""
        from ticketpilot.retrieval.providers.fake_embedding import (
            get_fake_embedding_provider,
        )

        provider1 = get_fake_embedding_provider()
        provider2 = get_fake_embedding_provider()

        # Should be the same instance
        assert provider1 is provider2

        # And produce same results
        vec1 = provider1.embed("test")
        vec2 = provider2.embed("test")
        assert vec1 == vec2


class TestFakeEmbeddingStatisticalProperties:
    """Tests for statistical properties of fake embeddings."""

    def test_embeddings_are_not_identical(self):
        """Test that different texts produce substantially different embeddings."""
        provider = FakeEmbeddingProvider()

        texts = ["apple", "banana", "cherry", "date", "elderberry"]
        embeddings = [provider.embed(t) for t in texts]

        # Check that embeddings are not all the same
        first_embedding = embeddings[0]
        for i, emb in enumerate(embeddings[1:], 1):
            assert emb != first_embedding, f"Embedding {i} is identical to first"

    def test_embedding_values_are_reasonably_distributed(self):
        """Test that embedding values span a reasonable range."""
        provider = FakeEmbeddingProvider()

        vec = provider.embed("test text distribution")

        min_val = min(vec)
        max_val = max(vec)

        # Should span at least some range
        assert max_val - min_val > 0.1, (
            "Embedding values should span a reasonable range"
        )
