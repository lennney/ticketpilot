"""Tests for scripts/rebuild_embeddings.py — all mocked, no live DB, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ticketpilot.retrieval.embedding_config import EmbeddingConfig
from ticketpilot.retrieval.embedding_metadata import EmbeddingIndexMetadata


# ---- Helpers ----


def _make_mock_chunks(count: int = 5):
    """Create mock chunk rows as tuples (id, content) matching DB cursor fetchall."""
    return [
        (f"00000000-0000-0000-0000-{i:012d}", f"chunk content {i}")
        for i in range(count)
    ]


def _make_mock_embeddings(count: int = 5, dim: int = 4):
    """Create mock embedding vectors."""
    return [[float(j) / dim for j in range(dim)] for _ in range(count)]


@pytest.fixture
def mock_config():
    """Create a minimal EmbeddingConfig for testing."""
    return EmbeddingConfig(
        provider="fake",
        model="fake-384",
        dimension=4,
        batch_size=10,
    )


@pytest.fixture
def mock_provider():
    """Create a mock embedding provider."""
    provider = MagicMock()
    provider.provider_name = "fake"
    provider.model_name = "fake-384"
    provider.DIM = 4
    provider.batch_size = 10
    provider.embed_batch.return_value = _make_mock_embeddings(5, 4)
    return provider


def _make_dry_run_args():
    args = MagicMock()
    args.dry_run = True
    args.confirm = False
    args.allow_dimension_reset = False
    return args


def _make_confirm_args():
    args = MagicMock()
    args.dry_run = False
    args.confirm = True
    args.allow_dimension_reset = False
    return args


def _make_dimension_reset_args():
    args = MagicMock()
    args.dry_run = False
    args.confirm = True
    args.allow_dimension_reset = True
    return args


def _make_mock_conn(dim_check_cb=None, chunks_cb=None):
    """Create a mock DB connection where each cursor() call returns a fresh cursor.

    Cursor sequence:
      0: _get_db_column_dimension (fetchone)
      1: _check_hnsw_index_exists (fetchone)
      2: _get_chunks_for_rebuild (fetchall)
      3: _get_source_counts (3× fetchone)

    Args:
        dim_check_cb: Callable(cursor) to set up cursor 0-1 for dimension check.
        chunks_cb: Callable(cursor) to set up cursor 2-3 for data fetch.
    """
    mock_conn = MagicMock()
    cursor_index = [0]

    def side_effect():
        idx = cursor_index[0]
        cursor_index[0] += 1

        if idx <= 1 and dim_check_cb:
            c = MagicMock()
            dim_check_cb(c)
            return c
        elif chunks_cb:
            c = MagicMock()
            chunks_cb(c)
            return c
        return MagicMock()

    mock_conn.cursor.side_effect = side_effect
    mock_conn.transaction.return_value.__enter__.return_value = None
    return mock_conn


def _setup_dim_check_cursor(c, db_dim: int = 4, hnsw_exists: bool = True):
    """Set up a cursor for the dimension-check query block.

    Must support psycopg's ``with conn.cursor() as cur:`` pattern (__enter__ returns self).
    """
    c.__enter__.return_value = c
    c.fetchone.side_effect = [
        (db_dim << 16,),  # _get_db_column_dimension: atttypmod
        (1 if hnsw_exists else None,),  # _check_hnsw_index_exists
    ]


def _setup_chunks_cursor(c, chunks=None, faq=10, policy=15, case=5):
    """Set up a cursor for the chunk-fetching query block.

    Supports both _get_chunks_for_rebuild (fetchall) and
    _get_source_counts (fetchone × 3).
    Must support psycopg's ``with conn.cursor() as cur:`` pattern.
    """
    c.__enter__.return_value = c
    c.fetchall.side_effect = [
        chunks
        if chunks is not None
        else _make_mock_chunks(5),  # _get_chunks_for_rebuild
    ]
    c.fetchone.side_effect = [
        (faq,),
        (policy,),
        (case,),
    ]


# ---- Dry-run behavior ----


class TestDryRunBehavior:
    """Tests for dry-run mode."""

    def test_dry_run_shows_status(self, mock_config, mock_provider):
        """Dry-run should return 'dry_run' status without writing."""
        import scripts.rebuild_embeddings as rebuild

        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            result = rebuild.run_rebuild(mock_config, _make_dry_run_args())

        assert result["status"] == "dry_run"
        assert "DRY RUN" in " ".join(result.get("steps", []))

    def test_confirm_required_for_write(self, mock_config, mock_provider):
        """Without --confirm, rebuild should block."""
        import scripts.rebuild_embeddings as rebuild

        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="fake-384",
            dimension=4,
        )
        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=meta),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            args = MagicMock()
            args.dry_run = False
            args.confirm = False
            args.allow_dimension_reset = False

            result = rebuild.run_rebuild(mock_config, args)

        assert result["status"] == "blocked"
        assert any("--confirm" in e for e in result.get("errors", []))


# ---- Dimension handling ----


class TestDimensionHandling:
    """Tests for dimension mismatch behavior."""

    def test_dimension_mismatch_fails_without_reset_flag(
        self, mock_config, mock_provider
    ):
        """DB column dimension differs from provider → fail without --allow-dimension-reset."""
        import scripts.rebuild_embeddings as rebuild

        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c, db_dim=8),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            args = MagicMock()
            args.dry_run = False
            args.confirm = True
            args.allow_dimension_reset = False

            result = rebuild.run_rebuild(mock_config, args)

        assert result["status"] == "failed"
        assert any("dimension mismatch" in e.lower() for e in result.get("errors", []))

    def test_dimension_mismatch_succeeds_with_reset_flag(
        self, mock_config, mock_provider
    ):
        """With --allow-dimension-reset, dimension mismatch should proceed."""
        import scripts.rebuild_embeddings as rebuild

        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c, db_dim=8),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "write_metadata"),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            result = rebuild.run_rebuild(mock_config, _make_dimension_reset_args())

        assert result["status"] == "completed"


# ---- Edge cases ----


class TestEdgeCases:
    """Tests for edge cases in rebuild."""

    def test_empty_chunks_skipped(self, mock_config, mock_provider):
        """Empty knowledge_chunks should result in skipped rebuild."""
        import scripts.rebuild_embeddings as rebuild

        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c, chunks=[]),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            result = rebuild.run_rebuild(mock_config, _make_confirm_args())

        assert result["status"] == "skipped"

    def test_provider_failure_handled(self, mock_config):
        """Provider creation failure should result in failed status."""
        import scripts.rebuild_embeddings as rebuild

        with (
            patch.object(
                rebuild,
                "create_embedding_provider",
                side_effect=ValueError("Missing API key"),
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
        ):
            result = rebuild.run_rebuild(mock_config, _make_dry_run_args())

        assert result["status"] == "failed"
        assert any("api key" in e.lower() for e in result.get("errors", []))

    def test_build_config_from_args(self):
        """_build_config_from_args should merge CLI overrides with env defaults."""
        import scripts.rebuild_embeddings as rebuild

        import os

        os.environ["EMBEDDING_PROVIDER"] = "fake"
        os.environ["EMBEDDING_MODEL"] = "fake-384"
        os.environ["EMBEDDING_DIM"] = "384"

        args = MagicMock()
        args.provider = None
        args.model = None
        args.dimension = None
        args.batch_size = None

        config = rebuild._build_config_from_args(args)
        assert config.provider == "fake"
        assert config.model == "fake-384"
        assert config.dimension == 384

        args.provider = "openai_compatible"
        args.model = "text-embedding-v4"
        args.dimension = 1024
        args.batch_size = 10

        config2 = rebuild._build_config_from_args(args)
        assert config2.provider == "openai_compatible"
        assert config2.model == "text-embedding-v4"
        assert config2.dimension == 1024
        assert config2.batch_size == 10

    def test_metadata_fingerprint_match_noted(self, mock_config, mock_provider):
        """If metadata fingerprint matches, rebuild should note it (not error)."""
        import scripts.rebuild_embeddings as rebuild

        meta = EmbeddingIndexMetadata(
            provider_name="fake",
            model_name="fake-384",
            dimension=4,
        )
        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=meta),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            result = rebuild.run_rebuild(mock_config, _make_dry_run_args())

        steps_text = " ".join(result.get("steps", []))
        assert "fingerprint" in steps_text.lower()


# ---- Full rebuild flow ----


class TestFullRebuildFlow:
    """Tests for the complete rebuild flow with confirmation."""

    def test_full_rebuild_writes_metadata(self, mock_config, mock_provider):
        """Successful rebuild should write metadata."""
        import scripts.rebuild_embeddings as rebuild

        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "write_metadata") as mock_write_meta,
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            result = rebuild.run_rebuild(mock_config, _make_confirm_args())

        assert result["status"] == "completed"
        assert mock_write_meta.called
        assert result["embedding_count"] == 5

    def test_rebuild_uses_provider_batch(self, mock_config, mock_provider):
        """Rebuild should call provider.embed_batch with correct texts."""
        import scripts.rebuild_embeddings as rebuild

        chunks = _make_mock_chunks(3)
        conn = _make_mock_conn(
            dim_check_cb=lambda c: _setup_dim_check_cursor(c),
            chunks_cb=lambda c: _setup_chunks_cursor(c, chunks=chunks),
        )

        with (
            patch.object(
                rebuild, "create_embedding_provider", return_value=mock_provider
            ),
            patch.object(rebuild, "read_metadata", return_value=None),
            patch.object(rebuild, "write_metadata"),
            patch.object(rebuild, "get_db_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__enter__.return_value = conn

            rebuild.run_rebuild(mock_config, _make_confirm_args())

        mock_provider.embed_batch.assert_called_once()
        called_texts = mock_provider.embed_batch.call_args[0][0]
        assert len(called_texts) == 3
        assert called_texts[0] == "chunk content 0"
