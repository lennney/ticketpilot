"""Thin wrapper that calls the retrieval engine and maps results to evidence candidates."""

from typing import Optional

from ticketpilot.retrieval.evidence_mapper import map_fused_to_evidence
from ticketpilot.retrieval.pipeline import hybrid_retrieval
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider
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
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
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
        if hasattr(candidate, 'content') and candidate.content is not None:
            if isinstance(candidate.content, bytes):
                candidate.content = candidate.content.decode('utf-8', errors='replace')

    return candidates, trace
