"""Tests for EmbeddingIndexMetadata dataclass — no DB, no network."""

from datetime import datetime, timezone

from ticketpilot.retrieval.embedding_metadata import EmbeddingIndexMetadata


class TestEmbeddingIndexMetadata:
    """Tests for the metadata dataclass."""

    def test_default_fingerprint_computed(self):
        """Fingerprint should be auto-computed from provider/model/dim."""
        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
        )
        assert len(meta.config_fingerprint) == 16
        # Deterministic: same inputs → same fingerprint
        meta2 = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
        )
        assert meta.config_fingerprint == meta2.config_fingerprint

    def test_fingerprint_matches_config(self):
        """fingerprint_matches_config should return True for matching params."""
        meta = EmbeddingIndexMetadata(
            provider_name="openai_compatible",
            model_name="text-embedding-v4",
            dimension=1024,
        )
        assert meta.fingerprint_matches_config("openai_compatible", "text-embedding-v4", 1024)

    def test_fingerprint_mismatch_detected(self):
        """fingerprint_matches_config should return False for different params."""
        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
        )
        assert not meta.fingerprint_matches_config("openai_compatible", "text-embedding-v4", 1024)
        assert not meta.fingerprint_matches_config("fake", "sha-256", 768)
        assert not meta.fingerprint_matches_config("fake", "other-model", 384)

    def test_built_at_defaults_to_now(self):
        """built_at should default to current time if not provided."""
        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
        )
        assert meta.built_at is not None
        assert isinstance(meta.built_at, datetime)
        # Should be close to now (within 10 seconds)
        delta = abs((datetime.now(timezone.utc) - meta.built_at).total_seconds())
        assert delta < 10

    def test_explicit_built_at_preserved(self):
        """Explicit built_at should not be overwritten."""
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
            built_at=dt,
        )
        assert meta.built_at == dt

    def test_explicit_fingerprint_preserved(self):
        """Explicit config_fingerprint should not be overwritten."""
        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
            config_fingerprint="custom-fp-1234",
        )
        assert meta.config_fingerprint == "custom-fp-1234"

    def test_to_dict_contains_all_fields(self):
        """to_dict should include all key fields."""
        meta = EmbeddingIndexMetadata(
            provider_name="openai_compatible",
            model_name="text-embedding-v4",
            dimension=1024,
            batch_size=10,
            source_record_count=95,
            chunk_count=95,
            embedding_count=95,
            notes="test build",
        )
        d = meta.to_dict()
        assert d["provider_name"] == "openai_compatible"
        assert d["model_name"] == "text-embedding-v4"
        assert d["dimension"] == 1024
        assert d["batch_size"] == 10
        assert d["source_record_count"] == 95
        assert d["chunk_count"] == 95
        assert d["embedding_count"] == 95
        assert d["notes"] == "test build"
        assert "built_at" in d
        assert "config_fingerprint" in d

    def test_from_dict_roundtrip(self):
        """from_dict should reconstruct a metadata object."""
        original = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="sha-256",
            dimension=384,
            batch_size=32,
            source_record_count=40,
            chunk_count=95,
            embedding_count=95,
            notes="roundtrip test",
        )
        d = original.to_dict()
        reconstructed = EmbeddingIndexMetadata.from_dict(d)
        assert reconstructed.provider_name == original.provider_name
        assert reconstructed.model_name == original.model_name
        assert reconstructed.dimension == original.dimension
        assert reconstructed.batch_size == original.batch_size
        assert reconstructed.config_fingerprint == original.config_fingerprint
        assert reconstructed.source_record_count == original.source_record_count
        assert reconstructed.chunk_count == original.chunk_count
        assert reconstructed.embedding_count == original.embedding_count
        assert reconstructed.notes == original.notes

    def test_from_dict_with_string_built_at(self):
        """from_dict should parse ISO format built_at string."""
        d = {
            "provider_name": "fake",
            "model_name": "sha-256",
            "dimension": 384,
            "built_at": "2026-05-04T12:00:00+00:00",
        }
        meta = EmbeddingIndexMetadata.from_dict(d)
        assert meta.built_at is not None
        assert meta.built_at.year == 2026
        assert meta.built_at.month == 5
        assert meta.built_at.day == 4

    def test_different_providers_have_different_fingerprints(self):
        """Different provider/model/dim combos should produce unique fingerprints."""
        m1 = EmbeddingIndexMetadata(provider_name="fake", model_name="sha-256", dimension=384)
        m2 = EmbeddingIndexMetadata(provider_name="openai_compatible", model_name="text-embedding-v4", dimension=1024)
        m3 = EmbeddingIndexMetadata(provider_name="fake", model_name="sha-256", dimension=768)
        fingerprints = {m1.config_fingerprint, m2.config_fingerprint, m3.config_fingerprint}
        assert len(fingerprints) == 3
