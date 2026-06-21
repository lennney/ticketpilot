"""Knowledge-base search tools for the draft agent.

Exports:
    search_knowledge: Hybrid retrieval against the knowledge base,
        returning a list of result dicts.
"""

from __future__ import annotations

import logging
from typing import Any

from ticketpilot.retrieval.evidence_mapper import map_fused_to_evidence
from ticketpilot.retrieval.pipeline import hybrid_retrieval
from ticketpilot.retrieval.schema.knowledge import DocType

logger = logging.getLogger(__name__)


def search_knowledge(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """Search the knowledge base using hybrid retrieval.

    Args:
        query: Natural-language search query.
        top_k: Maximum number of results to return.

    Returns:
        A list of dicts with keys:
        ``chunk_id``, ``doc_id``, ``doc_type``, ``content`` (truncated to 300
        characters), ``score``, ``rank``, ``title``, ``source_table``,
        ``source_id``.
    """
    try:
        trace = hybrid_retrieval(query=query, top_k=top_k)
        candidates = map_fused_to_evidence(trace.fused_results)
        results: list[dict[str, Any]] = []
        for c in candidates:
            results.append({
                "chunk_id": str(c.chunk_id),
                "doc_id": str(c.doc_id),
                "doc_type": c.doc_type.value,
                "content": c.content[:300],
                "score": round(c.score, 4),
                "rank": c.rank,
                "title": c.title,
                "source_table": c.source_table,
                "source_id": str(c.source_id),
            })
        return results
    except Exception as e:
        logger.error("search_knowledge failed: %s", e)
        return []
