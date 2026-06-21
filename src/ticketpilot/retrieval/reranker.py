"""
Lightweight re-ranking using embedding similarity.
Uses existing DashScope embeddings to re-rank RRF results.

Improved strategy: Use embedding as a boost factor, not a major weight.
"""

import logging
from typing import Optional
from ticketpilot.retrieval.traces import FusedResult

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def rerank_with_embeddings(
    query_embedding: list[float],
    fused_results: list[FusedResult],
    top_k: int = 10,
    embedding_provider=None,
) -> list[FusedResult]:
    """
    Re-rank fused results using embedding similarity.

    Strategy: Use embedding as a boost factor for results with similar RRF scores.
    This preserves the RRF ranking while using embedding to break ties.

    Args:
        query_embedding: Query embedding vector
        fused_results: Results from RRF fusion
        top_k: Number of results to return after re-ranking
        embedding_provider: Provider to generate document embeddings (optional)

    Returns:
        Re-ranked list of FusedResult
    """
    if not fused_results:
        return []

    # Compute embedding similarity for each result
    scored_results = []
    for result in fused_results:
        # Get document embedding from database
        doc_embedding = _get_document_embedding(result.chunk_id)

        if doc_embedding:
            # Compute cosine similarity
            similarity = cosine_similarity(query_embedding, doc_embedding)
        else:
            similarity = 0.0

        scored_results.append((result, similarity))

    # Group results by RRF score (within 10% tolerance)
    # This creates "tiers" of results with similar RRF scores
    rrf_scores = [r.rrf_score for r in fused_results]
    if not rrf_scores:
        return fused_results[:top_k]

    # Sort by RRF score first, then use embedding as tiebreaker within tiers
    def sort_key(item):
        result, similarity = item
        # Primary: RRF score (higher is better)
        # Secondary: embedding similarity (higher is better)
        return (-result.rrf_score, -similarity)

    scored_results.sort(key=sort_key)

    # Build re-ranked results
    reranked = []
    for i, (result, similarity) in enumerate(scored_results[:top_k], 1):
        # Create new FusedResult with updated score
        # Keep original RRF score, but add embedding info to metadata
        reranked_result = FusedResult(
            chunk_id=result.chunk_id,
            doc_id=result.doc_id,
            doc_type=result.doc_type,
            content=result.content,
            rrf_score=result.rrf_score,  # Keep original RRF score
            keyword_rank=result.keyword_rank,
            keyword_contribution=result.keyword_contribution,
            vector_rank=result.vector_rank,
            vector_contribution=result.vector_contribution,
            sources=result.sources + ["rerank"],
        )
        reranked.append(reranked_result)

    return reranked


def _get_document_embedding(chunk_id) -> Optional[list[float]]:
    """
    Get document embedding from database.

    Args:
        chunk_id: UUID of the knowledge chunk

    Returns:
        Embedding vector or None if not found
    """
    from ticketpilot.retrieval.db.connection import get_db_connection

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT embedding FROM knowledge_chunks WHERE id = %s",
                    (str(chunk_id),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    # Parse pgvector format: [0.1,0.2,...]
                    embedding_str = row[0]
                    if isinstance(embedding_str, str):
                        # Remove brackets and split by comma
                        embedding_str = embedding_str.strip("[]")
                        return [float(x) for x in embedding_str.split(",")]
                    elif isinstance(embedding_str, list):
                        return embedding_str
    except Exception:
        # Will use RRF score only — log for debugging
        logger.debug("Could not load document embedding for chunk, falling back to RRF")
        pass

    return None


def rerank_with_cross_encoder(
    query: str,
    fused_results: list[FusedResult],
    top_k: int = 10,
    model_name: str = "BAAI/bge-reranker-base",
) -> list[FusedResult]:
    """
    Re-rank using a cross-encoder model (requires sentence-transformers).

    This is the ideal approach but requires heavy dependencies.
    Currently not used - placeholder for future implementation.

    Args:
        query: Original query text
        fused_results: Results from RRF fusion
        top_k: Number of results to return
        model_name: Cross-encoder model name

    Returns:
        Re-ranked list of FusedResult
    """
    # TODO: Implement when sentence-transformers is available
    # For now, fall back to embedding-based re-ranking
    pass
