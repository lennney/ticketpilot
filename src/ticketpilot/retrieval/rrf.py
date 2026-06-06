"""Reciprocal Rank Fusion (RRF) for combining keyword and vector results."""

from typing import Optional
from uuid import UUID

from ticketpilot.retrieval.traces import FusedResult, KeywordResult, VectorResult

# Default RRF k parameter
DEFAULT_RRF_K = 60


def rrf_fusion(
    keyword_results: list[KeywordResult],
    vector_results: list[VectorResult],
    k: int = DEFAULT_RRF_K,
) -> list[FusedResult]:
    """
    Perform Reciprocal Rank Fusion (RRF) on keyword and vector results.

    RRF formula: score(doc) = sum(1 / (k + rank))

    This function is fully explainable - it tracks per-ranker contributions
    for each document, showing exactly how the final RRF score was calculated.

    Args:
        keyword_results: List of keyword search results (sorted by rank)
        vector_results: List of vector search results (sorted by rank)
        k: RRF k parameter (default: 60). Higher values reduce the impact
           of rank differences between rankers.

    Returns:
        List of FusedResult sorted by rrf_score descending, with per-ranker
        contributions explaining the score calculation.

    Example explainable output:
        doc_abc123:
          keyword_rank: 2 → contribution: 1/(60+2) = 0.01613
          vector_rank: 5 → contribution: 1/(60+5) = 0.01538
          RRF score: 0.03151
    """
    # Build lookup maps for fast access
    keyword_map: dict[UUID, KeywordResult] = {
        r.chunk_id: r for r in keyword_results
    }
    vector_map: dict[UUID, VectorResult] = {
        r.chunk_id: r for r in vector_results
    }

    # Get all unique chunk IDs
    all_chunk_ids: set[UUID] = set(keyword_map.keys()) | set(vector_map.keys())

    # Calculate RRF scores with per-ranker contributions
    fused_scores: list[tuple[UUID, float, Optional[int], Optional[float], Optional[int], Optional[float], list[str]]] = []

    for chunk_id in all_chunk_ids:
        sources = []
        keyword_rank: Optional[int] = None
        keyword_contribution: Optional[float] = None
        vector_rank: Optional[int] = None
        vector_contribution: Optional[float] = None

        # Keyword contribution
        if chunk_id in keyword_map:
            kw_result = keyword_map[chunk_id]
            keyword_rank = kw_result.rank
            keyword_contribution = 1.0 / (k + keyword_rank)
            sources.append("keyword")

        # Vector contribution
        if chunk_id in vector_map:
            vec_result = vector_map[chunk_id]
            vector_rank = vec_result.rank
            vector_contribution = 1.0 / (k + vector_rank)
            sources.append("vector")

        # Sum contributions
        rrf_score = 0.0
        if keyword_contribution is not None:
            rrf_score += keyword_contribution
        if vector_contribution is not None:
            rrf_score += vector_contribution

        fused_scores.append((
            chunk_id,
            rrf_score,
            keyword_rank,
            keyword_contribution,
            vector_rank,
            vector_contribution,
            sources,
        ))

    # Sort by RRF score descending
    fused_scores.sort(key=lambda x: x[1], reverse=True)

    # Build FusedResult list with full information, deduplicating by content
    results = []
    seen_content: set[str] = set()
    for (chunk_id, rrf_score, keyword_rank, kw_contrib, vector_rank, vec_contrib, sources) in fused_scores:
        # Get content and doc info from either result
        if chunk_id in keyword_map:
            kw = keyword_map[chunk_id]
            doc_type = kw.doc_type
            content = kw.content
            doc_id = kw.doc_id
        else:
            vec = vector_map[chunk_id]
            doc_type = vec.doc_type
            content = vec.content
            doc_id = vec.doc_id

        # Deduplicate by content (keep highest-scored)
        if content in seen_content:
            continue
        seen_content.add(content)

        results.append(
            FusedResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                doc_type=doc_type,
                content=content,
                rrf_score=rrf_score,
                keyword_rank=keyword_rank,
                keyword_contribution=kw_contrib,
                vector_rank=vector_rank,
                vector_contribution=vec_contrib,
                sources=sources,
            )
        )

    return results


def format_rrf_explanation(
    fused_result: FusedResult,
    k: int = DEFAULT_RRF_K,
) -> str:
    """
    Generate human-readable explanation for an RRF result.

    Args:
        fused_result: The fused result to explain
        k: RRF k parameter used

    Returns:
        Formatted string showing the RRF calculation
    """
    lines = [
        f"Chunk ID: {fused_result.chunk_id}",
        f"RRF Score: {fused_result.rrf_score:.6f}",
        "",
        "Per-ranker contributions:",
    ]

    if fused_result.keyword_rank is not None:
        lines.append(
            f"  keyword: rank={fused_result.keyword_rank}, "
            f"contribution = 1/({k}+{fused_result.keyword_rank}) = {fused_result.keyword_contribution:.6f}"
        )

    if fused_result.vector_rank is not None:
        lines.append(
            f"  vector: rank={fused_result.vector_rank}, "
            f"contribution = 1/({k}+{fused_result.vector_rank}) = {fused_result.vector_contribution:.6f}"
        )

    kw_contrib = fused_result.keyword_contribution if fused_result.keyword_rank else 0
    vec_contrib = fused_result.vector_contribution if fused_result.vector_rank else 0
    lines.append("")
    lines.append(f"Total: {kw_contrib:.6f} + {vec_contrib:.6f} = {fused_result.rrf_score:.6f}")

    return "\n".join(lines)