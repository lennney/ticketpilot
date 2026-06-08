"""Merge retrieval results from multiple query variants.

Supports three merge strategies:
- max_score: keep highest RRF score per chunk_id
- sum_score: sum RRF scores across queries (boosts docs found by multiple queries)
- rrf_again: treat each query as a ranker, apply second-level RRF
"""
from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from ticketpilot.retrieval.traces import FusedResult


def merge_retrieval_results(
    result_sets: list[list[FusedResult]],
    strategy: str = "sum_score",
) -> list[FusedResult]:
    """Merge multiple retrieval result sets, deduplicating by chunk_id.

    Args:
        result_sets: List of FusedResult lists, one per query variant.
        strategy: Merge strategy - "max_score", "sum_score", or "rrf_again".

    Returns:
        Merged and deduplicated list of FusedResult, sorted by score descending.
    """
    if not result_sets:
        return []

    # Flatten and filter empty sets
    non_empty = [rs for rs in result_sets if rs]
    if not non_empty:
        return []
    if len(non_empty) == 1:
        return list(non_empty[0])

    if strategy == "sum_score":
        return _merge_sum_score(non_empty)
    elif strategy == "max_score":
        return _merge_max_score(non_empty)
    elif strategy == "rrf_again":
        return _merge_rrf_again(non_empty)
    else:
        return _merge_sum_score(non_empty)


def _merge_sum_score(
    result_sets: list[list[FusedResult]],
) -> list[FusedResult]:
    """Sum RRF scores for the same chunk_id across query variants.

    Docs found by multiple queries get higher scores (multi-path validation).
    """
    best: dict[UUID, FusedResult] = {}
    score_sums: dict[UUID, float] = defaultdict(float)

    for result_set in result_sets:
        for r in result_set:
            score_sums[r.chunk_id] += r.rrf_score
            # Keep the version with most info (prefer one with both keyword+vector)
            if r.chunk_id not in best or len(r.sources) > len(best[r.chunk_id].sources):
                best[r.chunk_id] = r

    # Build merged results with summed scores
    merged: list[FusedResult] = []
    for cid, representative in best.items():
        merged.append(FusedResult(
            chunk_id=cid,
            doc_id=representative.doc_id,
            doc_type=representative.doc_type,
            content=representative.content,
            rrf_score=score_sums[cid],
            keyword_rank=representative.keyword_rank,
            keyword_contribution=representative.keyword_contribution,
            vector_rank=representative.vector_rank,
            vector_contribution=representative.vector_contribution,
            sources=representative.sources + ["multi_query"],
        ))

    merged.sort(key=lambda r: r.rrf_score, reverse=True)
    return merged


def _merge_max_score(
    result_sets: list[list[FusedResult]],
) -> list[FusedResult]:
    """Keep the highest RRF score per chunk_id."""
    best: dict[UUID, FusedResult] = {}

    for result_set in result_sets:
        for r in result_set:
            if r.chunk_id not in best or r.rrf_score > best[r.chunk_id].rrf_score:
                best[r.chunk_id] = r

    merged = list(best.values())
    merged.sort(key=lambda r: r.rrf_score, reverse=True)
    return merged


def _merge_rrf_again(
    result_sets: list[list[FusedResult]],
) -> list[FusedResult]:
    """Apply second-level RRF: treat each query variant as a ranker.

    Uses RRF k=60 on the rank positions within each query's results.
    """
    k = 60
    # Build per-query rank maps
    rank_maps: list[dict[UUID, int]] = []
    representative: dict[UUID, FusedResult] = {}

    for result_set in result_sets:
        rank_map: dict[UUID, int] = {}
        for i, r in enumerate(result_set, 1):
            rank_map[r.chunk_id] = i
            if r.chunk_id not in representative:
                representative[r.chunk_id] = r
        rank_maps.append(rank_map)

    # Compute second-level RRF scores
    rrf_scores: dict[UUID, float] = defaultdict(float)
    for rm in rank_maps:
        for cid, rank in rm.items():
            rrf_scores[cid] += 1.0 / (k + rank)

    # Build merged results
    merged: list[FusedResult] = []
    for cid, score in rrf_scores.items():
        rep = representative[cid]
        merged.append(FusedResult(
            chunk_id=cid,
            doc_id=rep.doc_id,
            doc_type=rep.doc_type,
            content=rep.content,
            rrf_score=score,
            keyword_rank=rep.keyword_rank,
            keyword_contribution=rep.keyword_contribution,
            vector_rank=rep.vector_rank,
            vector_contribution=rep.vector_contribution,
            sources=rep.sources + ["rrf_again"],
        ))

    merged.sort(key=lambda r: r.rrf_score, reverse=True)
    return merged
