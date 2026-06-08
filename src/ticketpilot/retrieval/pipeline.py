"""Hybrid retrieval pipeline combining keyword and vector search with RRF fusion.

Enhanced with:
- Multi-query expansion (LLM-generated query variants)
- Hybrid reranking (multi-signal weighted fusion)
"""
import logging
import time
from typing import Optional

from ticketpilot.retrieval.keyword_search import keyword_search
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider, get_fake_embedding_provider
from ticketpilot.retrieval.reranker_config import RerankerConfig
from ticketpilot.retrieval.hybrid_reranker import HybridReranker, RerankResult
from ticketpilot.retrieval.query_expander import MultiQueryExpander
from ticketpilot.retrieval.result_merger import merge_retrieval_results

logger = logging.getLogger(__name__)
from ticketpilot.retrieval.rrf import DEFAULT_RRF_K, rrf_fusion
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import FusedResult, RetrievalTrace
from ticketpilot.retrieval.vector_search import get_hnsw_params, vector_search


def _single_query_retrieval(
    query: str,
    query_embedding: list[float],
    top_k: int,
    doc_types: Optional[list[DocType]],
    exclude_business_domains: Optional[list[str]],
    embedding_provider,
    rrf_k: int,
) -> tuple[list[FusedResult], list, str, int, list, int]:
    """Run keyword + vector + RRF for a single query.

    Returns (fused_results, keyword_results, search_method, keyword_latency,
             vector_results, vector_latency).
    """
    provider_name = getattr(embedding_provider, "provider_name", "unknown")

    # Keyword search
    kw_start = time.perf_counter()
    kw_results, kw_method = keyword_search(
        query=query,
        top_k=top_k * 2,
        doc_types=doc_types,
        exclude_business_domains=exclude_business_domains,
    )
    kw_latency = int((time.perf_counter() - kw_start) * 1000)

    # Vector search
    vec_start = time.perf_counter()
    vec_results, _ = vector_search(
        query_embedding=query_embedding,
        top_k=top_k * 2,
        doc_types=doc_types,
        exclude_business_domains=exclude_business_domains,
        embedding_provider_name=provider_name,
    )
    vec_latency = int((time.perf_counter() - vec_start) * 1000)

    # RRF fusion
    fused = rrf_fusion(keyword_results=kw_results, vector_results=vec_results, k=rrf_k)

    return fused, kw_results, kw_method, kw_latency, vec_results, vec_latency


def hybrid_retrieval(
    query: str,
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
    exclude_business_domains: Optional[list[str]] = None,
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
    rrf_k: int = DEFAULT_RRF_K,
    enable_reranking: bool = True,
    # New params for hybrid reranking (backward compatible)
    intent: Optional[str] = None,
    enable_query_expansion: bool = False,
    reranker_config: Optional[RerankerConfig] = None,
) -> RetrievalTrace:
    """
    Perform hybrid retrieval combining keyword and vector search.

    Pipeline:
    1. (Optional) Expand query into variants via LLM
    2. For each query variant: keyword search + vector search + RRF fusion
    3. Merge results from all variants (sum_score dedup)
    4. (Optional) Hybrid rerank with multi-signal fusion
    5. Return complete trace for debugging and audit

    Args:
        query: Search query string
        top_k: Maximum number of results to return
        doc_types: Optional filter by document types
        embedding_provider: Embedding provider (default: FakeEmbeddingProvider)
        rrf_k: RRF k parameter (default: 60)
        enable_reranking: Enable re-ranking step (default: True)
        intent: Classified intent string (for intent-aware reranking)
        enable_query_expansion: Enable LLM-based query expansion (default: False)
        reranker_config: Custom reranker config (default: from YAML or built-in)

    Returns:
        RetrievalTrace with complete pipeline information
    """
    total_start_time = time.perf_counter()

    # Use provided embedding provider or default
    if embedding_provider is None:
        from ticketpilot.retrieval.vector_search import _detect_embedding_dim  # noqa: PLC0415
        dim = _detect_embedding_dim()
        embedding_provider = get_fake_embedding_provider(dimension=dim)

    provider_name = getattr(embedding_provider, "provider_name", "unknown")
    is_real = provider_name not in ("fake", "unknown", "")

    # Generate query embedding for the original query
    query_embedding = embedding_provider.embed(query)

    # --- Step 0: Query Expansion ---
    expansion_start = time.perf_counter()
    query_variants = [query]
    expansion_latency = 0
    if enable_query_expansion:
        expander = MultiQueryExpander()
        query_variants = expander.expand(query, intent or "")
    expansion_latency = int((time.perf_counter() - expansion_start) * 1000)

    # --- Step 1-3: Per-query retrieval + RRF ---
    all_fused: list[list[FusedResult]] = []
    # Use the first query's keyword/vector results for the trace
    first_kw_results = []
    first_kw_method = "fts"
    first_kw_latency = 0
    first_vec_results = []
    first_vec_latency = 0

    for i, q in enumerate(query_variants):
        # Generate embedding for variant (reuse original for first query)
        if i == 0:
            q_emb = query_embedding
        else:
            q_emb = embedding_provider.embed(q)

        fused, kw_res, kw_meth, kw_lat, vec_res, vec_lat = _single_query_retrieval(
            query=q,
            query_embedding=q_emb,
            top_k=top_k,
            doc_types=doc_types,
            exclude_business_domains=exclude_business_domains,
            embedding_provider=embedding_provider,
            rrf_k=rrf_k,
        )
        all_fused.append(fused)

        if i == 0:
            first_kw_results = kw_res
            first_kw_method = kw_meth
            first_kw_latency = kw_lat
            first_vec_results = vec_res
            first_vec_latency = vec_lat

    # --- Step 4: Merge results from all query variants ---
    merge_start = time.perf_counter()
    if len(all_fused) > 1:
        merged = merge_retrieval_results(all_fused, strategy="sum_score")
    else:
        merged = all_fused[0] if all_fused else []
    merge_latency = int((time.perf_counter() - merge_start) * 1000)
    merged_count = len(merged)

    # --- Step 5: Reranking ---
    rerank_latency = 0
    rerank_signals_data = None
    reranker_weights_data = None
    final_fused: list[FusedResult] = []

    if enable_reranking and merged:
        rerank_start = time.perf_counter()

        # Load reranker config
        if reranker_config is None:
            try:
                reranker_config = RerankerConfig.from_yaml("config/reranker.yaml")
            except Exception as e:
                logger.warning("Failed to load reranker config from YAML, using default: %s", e)
                reranker_config = RerankerConfig.default()

        # Take top candidates for reranking
        candidates = merged[: max(top_k * 3, 20)]

        reranker = HybridReranker(
            config=reranker_config,
            embedding_provider=embedding_provider,
        )
        reranked: list[RerankResult] = reranker.rerank(
            candidates=candidates,
            query=query,
            query_embedding=query_embedding,
            intent=intent,
            top_k=top_k,
        )

        # Convert RerankResult back to FusedResult for downstream compatibility
        final_fused = [r.to_fused_result() for r in reranked]

        # Extract trace data
        if reranked:
            rerank_signals_data = []
            for r in reranked:
                sig_data = {
                    "chunk_id": str(r.chunk_id),
                    "final_score": round(r.final_score, 6),
                    "signals": [
                        {
                            "name": s.name,
                            "weight": round(s.weight, 4),
                            "raw": round(s.raw_value, 6),
                            "normalized": round(s.normalized_value, 6),
                            "contribution": round(s.contribution, 6),
                        }
                        for s in r.signals
                    ],
                }
                rerank_signals_data.append(sig_data)

            # Get actual weights from the first result's signals
            if reranked[0].signals:
                reranker_weights_data = {
                    s.name: round(s.weight, 4) for s in reranked[0].signals
                }

        rerank_latency = int((time.perf_counter() - rerank_start) * 1000)
    else:
        final_fused = merged[:top_k]

    final_evidence_ids = [r.chunk_id for r in final_fused]

    # Total latency
    total_latency = int((time.perf_counter() - total_start_time) * 1000)

    # Build trace
    trace = RetrievalTrace(
        query=query,
        query_embedding=query_embedding,
        keyword_results=first_kw_results,
        keyword_latency_ms=first_kw_latency,
        keyword_search_method=first_kw_method,
        vector_results=first_vec_results,
        vector_latency_ms=first_vec_latency,
        fused_results=final_fused,
        fusion_latency_ms=merge_latency,
        rrf_k=rrf_k,
        final_evidence_ids=final_evidence_ids,
        total_latency_ms=total_latency,
        embedding_provider=provider_name,
        hnsw_params=get_hnsw_params(),
        top_k=top_k,
        rerank_latency_ms=rerank_latency,
        reranking_enabled=enable_reranking,
        # Hybrid reranking fields
        query_variants=query_variants if len(query_variants) > 1 else None,
        expansion_latency_ms=expansion_latency,
        merged_result_count=merged_count,
        rerank_signals=rerank_signals_data,
        reranker_weights=reranker_weights_data,
        has_real_embedding=is_real,
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
    """
    trace = hybrid_retrieval(query, top_k, doc_types)
    return [r.content for r in trace.fused_results]
