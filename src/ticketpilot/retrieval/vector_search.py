"""Vector search using pgvector HNSW index."""

import time
from typing import Optional

from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import VectorResult

# HNSW parameters
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 200
HNSW_EF_SEARCH = 100


def vector_search(
    query_embedding: list[float],
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
    exclude_business_domains: Optional[list[str]] = None,
    ef_search: int = HNSW_EF_SEARCH,
    embedding_dim: Optional[int] = None,
    embedding_provider_name: str = "fake",
) -> tuple[list[VectorResult], int]:
    """
    Perform vector search using pgvector HNSW index.

    Uses cosine similarity: 1 - (embedding <=> query_vector)

    Args:
        query_embedding: Query embedding vector
        top_k: Maximum number of results to return
        doc_types: Optional filter by document types
        ef_search: HNSW ef_search parameter (default: 100)
        embedding_dim: Expected embedding dimension. If None, detected from
                       the DB column or defaults to 384.
        embedding_provider_name: Embedding provider identifier for trace

    Returns:
        Tuple of (list of VectorResult, latency_ms)
    """
    # Lazy import to avoid dependency at module load
    from ticketpilot.retrieval.db.connection import get_db_connection

    # Detect expected dimension if not provided
    if embedding_dim is None:
        embedding_dim = _detect_embedding_dim()

    start_time = time.perf_counter()

    # Validate embedding dimension
    if len(query_embedding) != embedding_dim:
        raise ValueError(
            f"Expected {embedding_dim}-d embedding, got {len(query_embedding)}-d"
        )

    # Build doc_types filter if provided
    doc_types_filter = ""
    domain_filter = ""
    params: list = []
    if doc_types:
        placeholders = ", ".join("%s" for _ in doc_types)
        doc_types_filter = f"AND doc_type IN ({placeholders})"
        params = [dt.value for dt in doc_types]
    if exclude_business_domains:
        placeholders = ", ".join("%s" for _ in exclude_business_domains)
        domain_filter = f"AND business_domain NOT IN ({placeholders})"
        params.extend(exclude_business_domains)

    # Convert embedding to PostgreSQL array format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = f"""
        SELECT
            id as chunk_id,
            doc_id,
            doc_type,
            content,
            -- Cosine similarity: 1 - (embedding <=> query_vector)
            1 - (embedding <=> '{embedding_str}'::vector) as score,
            ROW_NUMBER() OVER (ORDER BY embedding <=> '{embedding_str}'::vector ASC, id) as rank
        FROM knowledge_chunks
        WHERE embedding IS NOT NULL
        {doc_types_filter}
        {domain_filter}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT %s
    """

    params.append(top_k)

    results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Set HNSW ef_search parameter
            cur.execute(f"SET hnsw.ef_search = {ef_search}")
            cur.execute(sql, params)
            for row in cur.fetchall():
                results.append(
                    VectorResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        doc_type=DocType(row[2]),
                        content=row[3],
                        score=float(row[4]),
                        rank=int(row[5]),
                        embedding_provider=embedding_provider_name,
                    )
                )

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    return results, latency_ms


def vector_search_for_testing(
    query_embedding: list[float],
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
) -> list[VectorResult]:
    """
    Vector search wrapper for testing (returns results only).

    Args:
        query_embedding: 384-d query embedding vector
        top_k: Maximum number of results
        doc_types: Optional filter by document types

    Returns:
        List of VectorResult
    """
    results, _ = vector_search(query_embedding, top_k, doc_types)
    return results


def _detect_embedding_dim() -> int:
    """Detect the embedding dimension from the DB column or metadata.

    Tries:
    1. pg_attribute vector dimension from knowledge_chunks.embedding column
    2. vector_dims() from actual data
    3. Fallback to 384

    Returns:
        Detected dimension (defaults to 384 on failure).
    """
    try:
        from ticketpilot.retrieval.embedding_metadata import (
            get_vector_dimension_from_db,
            get_vector_dimension_from_data,
        )

        dim = get_vector_dimension_from_db()
        if dim is not None and dim > 0:
            return dim
        dim = get_vector_dimension_from_data()
        if dim is not None and dim > 0:
            return dim
    except Exception:
        pass
    return 384


def get_hnsw_params() -> dict[str, int]:
    """Get current HNSW parameters."""
    return {
        "m": HNSW_M,
        "ef_construction": HNSW_EF_CONSTRUCTION,
        "ef_search": HNSW_EF_SEARCH,
    }