"""
Lightweight re-ranking using embedding similarity.
Uses existing BGE-small-zh embeddings to re-rank RRF results.
"""
from typing import Optional
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import FusedResult


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
    
    This is a lightweight re-ranking approach that:
    1. Takes top-k RRF results (e.g., top 20)
    2. Computes embedding similarity between query and each document
    3. Re-ranks by similarity score
    
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
    
    # If no embedding provider, use a simple hybrid score
    # Combine RRF score with a weight for the embedding similarity
    # For now, we'll use the existing embeddings from the database
    
    # Compute embedding similarity for each result
    scored_results = []
    for result in fused_results:
        # Get document embedding from database
        doc_embedding = _get_document_embedding(result.chunk_id)
        
        if doc_embedding:
            # Compute cosine similarity
            similarity = cosine_similarity(query_embedding, doc_embedding)
            
            # Combine RRF score with embedding similarity
            # Weight: 0.6 RRF + 0.4 embedding similarity
            combined_score = 0.6 * result.rrf_score + 0.4 * similarity
        else:
            # Fallback to RRF score only
            combined_score = result.rrf_score
            similarity = 0.0
        
        scored_results.append((result, combined_score, similarity))
    
    # Sort by combined score descending
    scored_results.sort(key=lambda x: x[1], reverse=True)
    
    # Build re-ranked results
    reranked = []
    for i, (result, combined_score, similarity) in enumerate(scored_results[:top_k], 1):
        # Create new FusedResult with updated score
        reranked_result = FusedResult(
            chunk_id=result.chunk_id,
            doc_id=result.doc_id,
            doc_type=result.doc_type,
            content=result.content,
            rrf_score=combined_score,  # Use combined score
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
                    (str(chunk_id),)
                )
                row = cur.fetchone()
                if row and row[0]:
                    # Parse pgvector format: [0.1,0.2,...]
                    embedding_str = row[0]
                    if isinstance(embedding_str, str):
                        # Remove brackets and split by comma
                        embedding_str = embedding_str.strip('[]')
                        return [float(x) for x in embedding_str.split(',')]
                    elif isinstance(embedding_str, list):
                        return embedding_str
    except Exception as e:
        # Silently fail - will use RRF score only
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
