"""Search reformulation strategies for the draft agent.

Functions:
    reformulate_search: Keyword-based second attempt using intent terms.
    llm_guided_search: LLM-suggested query when automated searches return
        nothing.

These functions modify the ``evidence`` and ``search_queries_used`` lists
in place so the caller's agent state is updated without extra copies.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ticketpilot.drafting.llm_utils import (
    _SYSTEM_PROMPT,
    LlmConfig,
    call_llm,
    extract_json,
)
from ticketpilot.retrieval.query_builder import _INTENT_TERMS
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import IntentClass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedup_and_cap(
    evidence: list[EvidenceCandidate],
    new_candidates: list[EvidenceCandidate],
    max_evidence: int,
) -> None:
    """Merge *new_candidates* into *evidence*, deduplicating by chunk_id
    and capping by score."""
    existing_ids = {c.chunk_id for c in evidence}
    for c in new_candidates:
        if c.chunk_id not in existing_ids:
            evidence.append(c)
            existing_ids.add(c.chunk_id)
    evidence.sort(key=lambda e: e.score, reverse=True)
    # Truncate in place so callers see the update
    del evidence[max_evidence:]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def reformulate_search(
    normalized_text: str,
    issue_type: str,
    evidence: list[EvidenceCandidate],
    search_queries_used: list[str],
    search_knowledge_fn: Callable[[str, int], list[dict[str, Any]]],
    raw_results_to_candidates_fn: Callable[
        [list[dict[str, Any]]], list[EvidenceCandidate]
    ],
    max_evidence: int = 15,
) -> None:
    """Try a second search with reformulated keywords.

    Builds an alternative query from intent-specific terms. If the query
    hasn't been used yet, calls *search_knowledge_fn*, converts results
    via *raw_results_to_candidates_fn*, and merges them into *evidence*.

    Args:
        normalized_text: Customer's message text (unused directly, but
            kept for interface consistency).
        issue_type: Classified intent label.
        evidence: Current evidence list (mutated in place).
        search_queries_used: Previously issued queries (mutated in place).
        search_knowledge_fn: Callable accepting ``(query, top_k)``.
        raw_results_to_candidates_fn: Callable converting raw search
            result dicts to ``EvidenceCandidate`` objects.
        max_evidence: Maximum evidence items to retain.
    """
    # Build alternative query using intent terms
    try:
        intent_enum = IntentClass(issue_type)
        extra_terms = _INTENT_TERMS.get(intent_enum, [])
    except ValueError:
        extra_terms = []

    alt_query = " ".join(extra_terms[:3]) if extra_terms else issue_type

    if alt_query not in search_queries_used:
        search_queries_used.append(alt_query)
        raw_results = search_knowledge_fn(alt_query)
        new_candidates = raw_results_to_candidates_fn(raw_results)
        _dedup_and_cap(evidence, new_candidates, max_evidence)

        logger.info(
            "reformulate_search: added %d new results (total %d)",
            len(new_candidates),
            len(evidence),
        )


def llm_guided_search(
    normalized_text: str,
    issue_type: str,
    evidence: list[EvidenceCandidate],
    search_queries_used: list[str],
    search_knowledge_fn: Callable[[str, int], list[dict[str, Any]]],
    raw_results_to_candidates_fn: Callable[
        [list[dict[str, Any]]], list[EvidenceCandidate]
    ],
    llm_config: LlmConfig,
    max_evidence: int = 15,
) -> None:
    """Ask the LLM to suggest a search query when automated searches fail.

    Sends the customer message and issue type to the LLM, expecting a JSON
    response with a ``search_knowledge`` tool call.  The suggested query is
    then executed and results merged into *evidence*.

    Args:
        normalized_text: Customer's message text.
        issue_type: Classified intent label.
        evidence: Current evidence list (mutated in place).
        search_queries_used: Previously issued queries (mutated in place).
        search_knowledge_fn: Callable accepting ``(query, top_k)``.
        raw_results_to_candidates_fn: Callable converting raw result dicts
            to ``EvidenceCandidate`` objects.
        llm_config: LLM endpoint configuration.
        max_evidence: Maximum evidence items to retain.
    """
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"客户消息：{normalized_text}\n"
                f"问题类型：{issue_type}\n\n"
                "之前的搜索没有找到足够证据。请建议一个搜索关键词，"
                "只输出JSON格式：\n"
                '{"tool": "search_knowledge", "query": "建议的关键词"}'
            ),
        },
    ]

    try:
        response = call_llm(messages, llm_config)
        parsed = extract_json(response)
        if parsed and parsed.get("tool") == "search_knowledge":
            query = parsed.get("query", "")
            if query and query not in search_queries_used:
                search_queries_used.append(query)
                raw_results = search_knowledge_fn(query)
                new_candidates = raw_results_to_candidates_fn(raw_results)
                _dedup_and_cap(evidence, new_candidates, max_evidence)

                logger.info(
                    "llm_guided_search: added %d new results (total %d)",
                    len(new_candidates),
                    len(evidence),
                )
    except Exception as e:
        logger.warning("LLM-guided search failed: %s", e)
