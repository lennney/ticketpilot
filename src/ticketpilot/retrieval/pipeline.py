"""Hybrid retrieval pipeline combining keyword and vector search with RRF fusion."""

import time
from typing import Optional

from ticketpilot.retrieval.keyword_search import keyword_search
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider, get_fake_embedding_provider
from ticketpilot.retrieval.rrf import DEFAULT_RRF_K, rrf_fusion
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.retrieval.vector_search import get_hnsw_params, vector_search


def hybrid_retrieval(
    query: str,
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
    rrf_k: int = DEFAULT_RRF_K,
) -> RetrievalTrace:
    """
    Perform hybrid retrieval combining keyword and vector search.

    Pipeline:
    1. Generate query embedding using the embedding provider
    2. Run keyword search (FTS + LIKE fallback)
    3. Run vector search (HNSW)
    4. Fuse results using RRF
    5. Return complete trace for debugging and audit

    Args:
        query: Search query string
        top_k: Maximum number of results to return
        doc_types: Optional filter by document types
        embedding_provider: Embedding provider (default: FakeEmbeddingProvider)
        rrf_k: RRF k parameter (default: 60)

    Returns:
        RetrievalTrace with complete pipeline information
    """
    total_start_time = time.perf_counter()

    # Use provided embedding provider or default (matching DB dimension)
    if embedding_provider is None:
        from ticketpilot.retrieval.vector_search import _detect_embedding_dim
        dim = _detect_embedding_dim()
        embedding_provider = get_fake_embedding_provider(dimension=dim)

    # Generate query embedding
    query_embedding = embedding_provider.embed(query)

    # Keyword search
    keyword_start = time.perf_counter()
    keyword_results, keyword_search_method = keyword_search(
        query=query,
        top_k=top_k * 2,  # Fetch more to account for fusion
        doc_types=doc_types,
    )
    keyword_latency_ms = int((time.perf_counter() - keyword_start) * 1000)

    # Get provider name for trace (handles both FakeEmbeddingProvider and others)
    provider_name = getattr(embedding_provider, "provider_name", "unknown")

    # Vector search
    vector_start = time.perf_counter()
    vector_results, vector_latency_ms = vector_search(
        query_embedding=query_embedding,
        top_k=top_k * 2,  # Fetch more to account for fusion
        doc_types=doc_types,
        embedding_provider_name=provider_name,
    )
    vector_latency_ms = int((time.perf_counter() - vector_start) * 1000)

    # RRF Fusion
    fusion_start = time.perf_counter()
    fused_results = rrf_fusion(
        keyword_results=keyword_results,
        vector_results=vector_results,
        k=rrf_k,
    )
    fusion_latency_ms = int((time.perf_counter() - fusion_start) * 1000)

    # Limit to top_k
    fused_results = fused_results[:top_k]
    final_evidence_ids = [r.chunk_id for r in fused_results]

    # Total latency
    total_latency_ms = int((time.perf_counter() - total_start_time) * 1000)

    # Build trace
    trace = RetrievalTrace(
        query=query,
        query_embedding=query_embedding,
        keyword_results=keyword_results,
        keyword_latency_ms=keyword_latency_ms,
        keyword_search_method=keyword_search_method,
        vector_results=vector_results,
        vector_latency_ms=vector_latency_ms,
        fused_results=fused_results,
        fusion_latency_ms=fusion_latency_ms,
        rrf_k=rrf_k,
        final_evidence_ids=final_evidence_ids,
        total_latency_ms=total_latency_ms,
        embedding_provider=provider_name,
        hnsw_params=get_hnsw_params(),
        top_k=top_k,
    )

    return trace


def simple_retrieval(
    query: str,
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
) -> list[str]:
    """
    Simple retrieval interface returning just content.

    Convenience function for cases where trace is not needed.

    Args:
        query: Search query string
        top_k: Maximum number of results
        doc_types: Optional filter by document types

    Returns:
        List of content strings for top-k results
    """
    trace = hybrid_retrieval(query, top_k, doc_types)
    return [r.content for r in trace.fused_results]