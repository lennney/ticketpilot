"""Embedding index metadata — tracks which provider/model/dimension built the current index."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from ticketpilot.retrieval.db.connection import get_db_connection


@dataclass
class EmbeddingIndexMetadata:
    """Metadata record for a knowledge embedding index build.

    Fields:
        provider_name: Embedding provider name (e.g. "fake", "openai_compatible")
        model_name: Model name (e.g. "sha-256", "text-embedding-v4")
        dimension: Vector dimension
        batch_size: Batch size used during embedding
        built_at: Timestamp when the index was built
        source_record_count: Number of source documents processed
        chunk_count: Number of chunks embedded
        embedding_count: Number of embeddings generated
        config_fingerprint: Hash of provider+model+dimension for quick comparison
        notes: Optional notes about this build
    """

    provider_name: str
    model_name: str
    dimension: int
    batch_size: int = 32
    built_at: datetime | None = None
    source_record_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    config_fingerprint: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.config_fingerprint:
            self.config_fingerprint = self._compute_fingerprint()
        if self.built_at is None:
            self.built_at = datetime.now(timezone.utc)

    def _compute_fingerprint(self) -> str:
        raw = f"{self.provider_name}|{self.model_name}|{self.dimension}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def fingerprint_matches_config(
        self, provider_name: str, model_name: str, dimension: int
    ) -> bool:
        """Check if given config matches this metadata's fingerprint."""
        expected = hashlib.sha256(
            f"{provider_name}|{model_name}|{dimension}".encode()
        ).hexdigest()[:16]
        return self.config_fingerprint == expected

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "config_fingerprint": self.config_fingerprint,
            "source_record_count": self.source_record_count,
            "chunk_count": self.chunk_count,
            "embedding_count": self.embedding_count,
            "notes": self.notes,
        }
        if self.built_at:
            result["built_at"] = self.built_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingIndexMetadata:
        d = dict(data)
        built_at = d.pop("built_at", None)
        if built_at and isinstance(built_at, str):
            d["built_at"] = datetime.fromisoformat(built_at)
        return cls(**d)


# ---- DB helpers ----


CREATE_METADATA_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS embedding_index_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    dimension INTEGER NOT NULL,
    batch_size INTEGER NOT NULL DEFAULT 32,
    built_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_record_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_count INTEGER NOT NULL DEFAULT 0,
    config_fingerprint VARCHAR(64) NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""


def ensure_metadata_table() -> None:
    """Create the metadata table if it does not exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_METADATA_TABLE_SQL)
        conn.commit()


def read_metadata() -> EmbeddingIndexMetadata | None:
    """Read the latest (most recent) metadata record from DB.

    Returns:
        EmbeddingIndexMetadata or None if no record exists.
    """
    ensure_metadata_table()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT provider_name, model_name, dimension, batch_size,
                          built_at, source_record_count, chunk_count,
                          embedding_count, config_fingerprint, notes
                   FROM embedding_index_metadata
                   ORDER BY built_at DESC NULLS LAST
                   LIMIT 1"""
            )
            row = cur.fetchone()
            if row is None:
                return None
            return EmbeddingIndexMetadata(
                provider_name=row[0],
                model_name=row[1],
                dimension=row[2],
                batch_size=row[3],
                built_at=row[4],
                source_record_count=row[5],
                chunk_count=row[6],
                embedding_count=row[7],
                config_fingerprint=row[8],
                notes=row[9] or "",
            )


def write_metadata(metadata: EmbeddingIndexMetadata) -> None:
    """Write a new metadata record to the database.

    Args:
        metadata: The metadata record to persist.
    """
    ensure_metadata_table()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO embedding_index_metadata
                    (provider_name, model_name, dimension, batch_size,
                     built_at, source_record_count, chunk_count,
                     embedding_count, config_fingerprint, notes)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    metadata.provider_name,
                    metadata.model_name,
                    metadata.dimension,
                    metadata.batch_size,
                    metadata.built_at,
                    metadata.source_record_count,
                    metadata.chunk_count,
                    metadata.embedding_count,
                    metadata.config_fingerprint,
                    metadata.notes,
                ),
            )
        conn.commit()


def get_vector_dimension_from_db() -> int | None:
    """Detect the vector dimension of knowledge_chunks.embedding column.

    Queries pg_attribute to find the vector dimension constraint.
    Returns None if the table, column, or constraint does not exist.
    """
    from ticketpilot.retrieval.db.connection import get_db_connection

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT atttypmod FROM pg_attribute
                       WHERE attrelid = 'knowledge_chunks'::regclass
                       AND attname = 'embedding'
                       AND attnum > 0"""
                )
                row = cur.fetchone()
                if row is None:
                    return None
                typmod = row[0]
                if typmod is None or typmod <= 0:
                    return None
                if typmod > 0xFFFF:  # pgvector < 0.7: encoded as dim << 16
                    dim = typmod >> 16
                else:  # pgvector >= 0.7: raw dimension
                    dim = typmod
                return dim if dim > 0 else None
    except Exception as exc:
        logger.error("Failed to detect vector dimension from DB", exc_info=exc)
        return None


def get_vector_dimension_from_data() -> int | None:
    """Get vector dimension from an actual embedding row.

    Falls back to querying vector_dims() on the first non-null embedding.
    Returns None if no embeddings exist.
    """
    from ticketpilot.retrieval.db.connection import get_db_connection

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT vector_dims(embedding) FROM knowledge_chunks
                       WHERE embedding IS NOT NULL
                       LIMIT 1"""
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as exc:
        logger.error("Failed to detect vector dimension from data", exc_info=exc)
        return None
