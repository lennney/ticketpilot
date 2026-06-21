"""Thin wrapper that calls the retrieval engine and maps results to evidence candidates."""

from typing import Optional

from ticketpilot.retrieval.evidence_mapper import map_fused_to_evidence
from ticketpilot.retrieval.pipeline import hybrid_retrieval
from ticketpilot.retrieval.providers.fake_embedding import EmbeddingProvider
from ticketpilot.retrieval.query_builder import build_retrieval_query
from ticketpilot.retrieval.reranker_config import RerankerConfig
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import IntentClass, RiskFlag


def retrieve_evidence(
    normalized_text: str,
    intent: IntentClass,
    risk_flags: set[RiskFlag],
    top_k: int = 10,
    doc_types: list[DocType] | None = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    # New params for hybrid reranking (backward compatible)
    enable_query_expansion: bool = False,
    reranker_config: Optional[RerankerConfig] = None,
) -> tuple[list[EvidenceCandidate], RetrievalTrace]:
    """Retrieve evidence candidates from the knowledge base.

    Constructs a retrieval query from ticket state, runs hybrid
    retrieval with optional query expansion and hybrid reranking,
    and maps fused results to evidence candidates.
    Always returns a RetrievalTrace, even when no results are found.
    """
    query = build_retrieval_query(normalized_text, intent, risk_flags)
    trace = hybrid_retrieval(
        query=query,
        top_k=top_k,
        doc_types=doc_types,
        embedding_provider=embedding_provider,
        intent=intent.value if intent else None,
        enable_query_expansion=enable_query_expansion,
        reranker_config=reranker_config,
    )
    candidates = map_fused_to_evidence(trace.fused_results)

    # 安全处理每个 candidate 的内容，避免损坏的 UTF-8 导致下游崩溃
    for candidate in candidates:
        if hasattr(candidate, "content") and candidate.content is not None:
            if isinstance(candidate.content, bytes):
                candidate.content = candidate.content.decode("utf-8", errors="replace")

    return candidates, trace


def assess_retrieval_sufficiency(
    results: list[dict],
    min_results: int = 3,
    min_avg_score: float = 0.7,
) -> dict:
    """Evaluate if retrieval results are sufficient for draft generation."""
    if not results:
        return {
            "sufficient": False,
            "reason": "no results",
            "avg_score": 0.0,
            "result_count": 0,
        }
    scores = [r.get("score", 0) for r in results]
    avg_score = sum(scores) / len(scores)
    above_threshold = sum(1 for s in scores if s >= min_avg_score)
    sufficient = len(results) >= min_results and avg_score >= min_avg_score
    return {
        "sufficient": sufficient,
        "avg_score": round(avg_score, 3),
        "result_count": len(results),
        "above_threshold_count": above_threshold,
        "reason": None
        if sufficient
        else f"{len(results)} results, avg {avg_score:.2f} < {min_avg_score}",
    }


import re

_SYNONYM_MAP = {
    "refund": "退款",
    "退货": "退款退货",
    "物流": "快递物流配送",
    "bug": "故障问题",
    "vip": "会员",
}


def rewrite_query(query: str) -> str:
    """Rule-based query rewriting for better retrieval recall."""
    rewritten = query
    for short, expanded in _SYNONYM_MAP.items():
        if short.lower() in rewritten.lower() and expanded not in rewritten:
            rewritten = f"{rewritten} {expanded}"
    if len(rewritten) > 30:
        clauses = re.split(r"[，。？！、和还有以及]", rewritten)
        if clauses and len(clauses[0]) > 5:
            rewritten = clauses[0].strip()
    return rewritten.strip()
