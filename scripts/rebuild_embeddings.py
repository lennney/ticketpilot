#!/usr/bin/env python3
"""Rebuild knowledge base embeddings with the configured embedding provider.

CLI to regenerate all knowledge_chunks embeddings, update the database,
and record build metadata. Requires --confirm to make any changes; defaults
to dry-run mode that prints what would be done.

Usage:
    # Dry-run (default)  --  shows what would happen
    uv run python scripts/rebuild_embeddings.py

    # Actual rebuild with current EMBEDDING_* env vars
    uv run python scripts/rebuild_embeddings.py --confirm

    # Override provider/model/dimension
    uv run python scripts/rebuild_embeddings.py --provider openai_compatible --dimension 1024 --confirm

    # Allow changing DB column dimension (e.g. 384  ->  1024)
    uv run python scripts/rebuild_embeddings.py --provider openai_compatible --dimension 1024 --allow-dimension-reset --confirm
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ticketpilot.retrieval.db.connection import get_db_connection
from ticketpilot.retrieval.embedding_config import (
    EmbeddingConfig,
    load_embedding_config_from_env,
)
from ticketpilot.retrieval.embedding_metadata import (
    EmbeddingIndexMetadata,
    read_metadata,
    write_metadata,
)
from ticketpilot.retrieval.providers import create_embedding_provider


def _build_config_from_args(args: argparse.Namespace) -> EmbeddingConfig:
    """Build EmbeddingConfig from CLI args (override env vars)."""
    base = load_embedding_config_from_env()
    return EmbeddingConfig(
        provider=args.provider or base.provider,
        model=args.model or base.model,
        dimension=args.dimension or base.dimension,
        base_url=base.base_url,
        api_key=base.api_key,
        batch_size=args.batch_size or base.batch_size,
    )


def _get_chunks_for_rebuild(conn) -> list[dict[str, Any]]:
    """Fetch all knowledge chunks that need embeddings.

    Returns list of dicts with 'id' and 'content'.
    """
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, content FROM knowledge_chunks
               ORDER BY doc_type, id"""
        )
        return [
            {"id": row[0], "content": row[1]}
            for row in cur.fetchall()
        ]


def _get_source_counts(conn) -> dict[str, int]:
    """Get source document counts."""
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in ("knowledge_faq", "knowledge_policy", "knowledge_case"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    return counts


def _get_db_column_dimension(conn) -> int | None:
    """Get the current vector dimension of the embedding column."""
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


def _check_hnsw_index_exists(conn) -> bool:
    """Check whether the HNSW index exists on the embedding column."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT 1 FROM pg_indexes
               WHERE tablename = 'knowledge_chunks'
               AND indexname = 'idx_chunks_embedding_hnsw'"""
        )
        return cur.fetchone() is not None


def _drop_hnsw_index(conn) -> None:
    """Drop the HNSW index to allow column type change."""
    with conn.cursor() as cur:
        cur.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")


def _recreate_hnsw_index(conn) -> None:
    """Recreate the HNSW index after rebuilding embeddings."""
    with conn.cursor() as cur:
        cur.execute(
            """CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
               ON knowledge_chunks
               USING hnsw (embedding vector_cosine_ops)
               WITH (m = 16, ef_construction = 200)"""
        )


def _alter_vector_dimension(conn, new_dim: int) -> None:
    """Change the embedding column to a new vector dimension.

    pgvector requires existing embeddings to be NULL before changing
    dimension, since there is no valid cast between different dimensions.
    """
    with conn.cursor() as cur:
        cur.execute("UPDATE knowledge_chunks SET embedding = NULL")
        cur.execute(
            f"ALTER TABLE knowledge_chunks "
            f"ALTER COLUMN embedding TYPE vector({new_dim})"
        )


def _update_chunk_embedding(conn, chunk_id, embedding_str: str) -> None:
    """Update a single chunk's embedding."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE knowledge_chunks SET embedding = %s::vector WHERE id = %s",
            (embedding_str, chunk_id),
        )


def _get_source_record_count(conn) -> int:
    """Get total source documents across all source tables."""
    total = 0
    with conn.cursor() as cur:
        for table in ("knowledge_faq", "knowledge_policy", "knowledge_case"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total += cur.fetchone()[0]
    return total


def _get_chunk_count(conn) -> int:
    """Get total number of chunks in knowledge_chunks."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        return cur.fetchone()[0]


def _embedding_to_str(embedding: list[float]) -> str:
    """Convert embedding list to PostgreSQL vector array string."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def run_rebuild(config: EmbeddingConfig, args: argparse.Namespace) -> dict[str, Any]:
    """Execute the rebuild workflow.

    Args:
        config: The embedding configuration to use.
        args: CLI arguments (dry_run, confirm, allow_dimension_reset, etc.)

    Returns:
        Dictionary with rebuild results and summary.
    """
    result: dict[str, Any] = {
        "status": "pending",
        "errors": [],
        "warnings": [],
        "steps": [],
    }

    # Step 1: Create provider
    try:
        provider = create_embedding_provider(config)
    except ValueError as e:
        result["status"] = "failed"
        result["errors"].append(f"Provider creation failed: {e}")
        return result

    result["provider_name"] = provider.provider_name
    result["model_name"] = provider.model_name
    result["dimension"] = provider.DIM
    result["batch_size"] = provider.batch_size
    result["steps"].append(
        f"Provider: {provider.provider_name} / {provider.model_name} "
        f"(dim={provider.DIM}, batch_size={provider.batch_size})"
    )

    # Step 2: Read current metadata
    try:
        current_metadata = read_metadata()
    except Exception as e:
        result["warnings"].append(f"Could not read current metadata: {e}")
        current_metadata = None

    if current_metadata:
        result["current_metadata"] = current_metadata.to_dict()
        match = current_metadata.fingerprint_matches_config(
            provider.provider_name, provider.model_name, provider.DIM
        )
        if match:
            result["steps"].append(
                f"Metadata fingerprint matches current config  --  embeddings are up-to-date "
                f"(provider={current_metadata.provider_name}, "
                f"model={current_metadata.model_name}, "
                f"dim={current_metadata.dimension})"
            )
        else:
            result["steps"].append(
                f"Metadata fingerprint differs: "
                f"current=({current_metadata.provider_name}|"
                f"{current_metadata.model_name}|{current_metadata.dimension}) "
                f" ->  requested=({provider.provider_name}|"
                f"{provider.model_name}|{provider.DIM})"
            )
    else:
        result["steps"].append("No existing metadata found  --  fresh build")

    # Step 3: Check DB vector dimension
    with get_db_connection() as conn:
        db_dim = _get_db_column_dimension(conn)
        has_index = _check_hnsw_index_exists(conn)

    result["db_dimension"] = db_dim

    if db_dim is not None and db_dim != provider.DIM:
        result["steps"].append(
            f"DB vector column is vector({db_dim}) but provider produces "
            f"vector({provider.DIM})  --  dimension mismatch"
        )
        if not args.allow_dimension_reset:
            result["status"] = "failed"
            result["errors"].append(
                f"Embedding dimension mismatch: database vector dimension is {db_dim} "
                f"but provider '{provider.provider_name}' (model: {provider.model_name}) "
                f"produces dimension {provider.DIM}. "
                f"Use --allow-dimension-reset to change the column type. "
                f"This will drop and recreate the HNSW index."
            )
            return result
    elif db_dim is None:
        result["warnings"].append(
            "Could not detect DB vector dimension  --  may be empty or table missing"
        )
    else:
        result["steps"].append(f"DB vector dimension: {db_dim} (matches provider)")

    # Step 4: Fetch chunks
    with get_db_connection() as conn:
        chunks = _get_chunks_for_rebuild(conn)
        source_counts = _get_source_counts(conn)
        total_source = sum(source_counts.values())

    result["chunk_count"] = len(chunks)
    result["source_record_count"] = total_source

    if not chunks:
        result["status"] = "skipped"
        result["steps"].append("No chunks found in knowledge_chunks  --  nothing to rebuild")
        return result

    result["steps"].append(
        f"Found {len(chunks)} chunks, {total_source} source documents"
    )

    # Step 5: If dry-run, stop here
    if args.dry_run:
        result["status"] = "dry_run"
        result["steps"].append("DRY RUN  --  no changes written to database")
        return result

    # Step 6: Execute rebuild
    if not args.confirm:
        result["status"] = "blocked"
        result["errors"].append(
            "Dry-run mode is active (default). Pass --confirm to write changes."
        )
        return result

    try:
        with get_db_connection() as conn:
            with conn.transaction():
                # 6a: Drop HNSW index if dimension changes
                if db_dim is not None and db_dim != provider.DIM:
                    if has_index:
                        _drop_hnsw_index(conn)
                        result["steps"].append(
                            f"Dropped HNSW index (dimension change {db_dim}  ->  {provider.DIM})"
                        )
                    _alter_vector_dimension(conn, provider.DIM)
                    result["steps"].append(
                        f"Changed embedding column to vector({provider.DIM})"
                    )

                # 6b: Generate and update embeddings in batches
                texts = [c["content"] for c in chunks]
                embeddings = provider.embed_batch(texts)

                if len(embeddings) != len(chunks):
                    raise RuntimeError(
                        f"Provider returned {len(embeddings)} embeddings "
                        f"for {len(chunks)} inputs  --  count mismatch"
                    )

                for chunk, vec in zip(chunks, embeddings):
                    emb_str = _embedding_to_str(vec)
                    _update_chunk_embedding(conn, chunk["id"], emb_str)

                result["embedding_count"] = len(embeddings)
                result["steps"].append(
                    f"Updated {len(embeddings)} embeddings in database"
                )

                # 6c: Recreate HNSW index if it was dropped
                if db_dim is not None and db_dim != provider.DIM:
                    _recreate_hnsw_index(conn)
                    result["steps"].append("Recreated HNSW index")

                # 6d: Write metadata
                metadata = EmbeddingIndexMetadata(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    dimension=provider.DIM,
                    batch_size=provider.batch_size,
                    source_record_count=total_source,
                    chunk_count=len(chunks),
                    embedding_count=len(embeddings),
                    notes="Rebuild via scripts/rebuild_embeddings.py",
                )
                write_metadata(metadata)
                result["steps"].append("Wrote build metadata")

        result["status"] = "completed"
        result["steps"].append("Rebuild complete")

    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Rebuild failed: {e}")

    return result


def print_summary(result: dict[str, Any]) -> None:
    """Print a human-readable summary of the rebuild result."""
    status = result.get("status", "unknown")
    print(f"\n{'='*60}")
    print(f"  Embedding Rebuild: {status.upper()}")
    print(f"{'='*60}")

    if result.get("provider_name"):
        print(f"  Provider : {result['provider_name']}")
        print(f"  Model    : {result['model_name']}")
        print(f"  Dim      : {result['dimension']}")
        print(f"  Batch    : {result.get('batch_size', '?')}")
    if result.get("chunk_count") is not None:
        print(f"  Chunks   : {result['chunk_count']}")
    if result.get("db_dimension") is not None:
        print(f"  DB dim   : {result['db_dimension']}")

    print("\n  Steps:")
    for step in result.get("steps", []):
        print(f"    - {step}")

    if result.get("warnings"):
        print("\n  Warnings:")
        for w in result["warnings"]:
            print(f"    [!] {w}")

    if result.get("errors"):
        print("\n  Errors:")
        for e in result["errors"]:
            print(f"    [x] {e}")

    print(f"{'='*60}\n")


def main() -> None:
    """Parse CLI arguments and run the rebuild workflow."""
    parser = argparse.ArgumentParser(
        description="Rebuild knowledge base embeddings with the configured provider.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be done without writing (default: True)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        default=False,
        help="Actually write to the database",
    )
    parser.add_argument(
        "--allow-dimension-reset",
        action="store_true",
        default=False,
        help="Allow changing the vector column dimension (drops/recreates HNSW index)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Override EMBEDDING_PROVIDER",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override EMBEDDING_MODEL",
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=None,
        help="Override EMBEDDING_DIM",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override EMBEDDING_BATCH_SIZE",
    )

    args = parser.parse_args()
    # --confirm disables dry-run
    args.dry_run = not args.confirm

    config = _build_config_from_args(args)
    result = run_rebuild(config, args)
    print_summary(result)

    if result["status"] in ("failed", "blocked"):
        sys.exit(1)


if __name__ == "__main__":
    main()
