"""Retrieval module for TicketPilot knowledge retrieval."""

from ticketpilot.retrieval.chunker import chunk_text, compute_content_hash
from ticketpilot.retrieval.keyword_search import keyword_search
from ticketpilot.retrieval.pipeline import (
    hybrid_retrieval,
    simple_retrieval,
)
from ticketpilot.retrieval.providers.fake_embedding import (
    FAKE_EMBEDDING_DIM,
    FakeEmbeddingProvider,
    get_fake_embedding_provider,
)
from ticketpilot.retrieval.rrf import DEFAULT_RRF_K, format_rrf_explanation, rrf_fusion
from ticketpilot.retrieval.schema.knowledge import (
    BusinessDomain,
    CaseDocument,
    ChunkLevel,
    DocType,
    FAQDocument,
    KnowledgeChunk,
    PolicyDocument,
    RiskLevel,
)
from ticketpilot.retrieval.schema.retrieval import (
    RetrievalQuery,
    RetrievalResult,
)
from ticketpilot.retrieval.schema.seeds import (
    load_case_seed_data,
    load_faq_seed_data,
    load_policy_seed_data,
    load_seed_data,
)
from ticketpilot.retrieval.traces import (
    FusedResult,
    KeywordResult,
    RetrievalTrace,
    VectorResult,
)
from ticketpilot.retrieval.vector_search import (
    HNSW_EF_SEARCH,
    HNSW_M,
    get_hnsw_params,
    vector_search,
)

__all__ = [
    # Knowledge schemas
    "DocType",
    "ChunkLevel",
    "BusinessDomain",
    "RiskLevel",
    "FAQDocument",
    "PolicyDocument",
    "CaseDocument",
    "KnowledgeChunk",
    # Retrieval schemas
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalTrace",
    # Seed data loaders
    "load_faq_seed_data",
    "load_policy_seed_data",
    "load_case_seed_data",
    "load_seed_data",
    # Chunker
    "chunk_text",
    "compute_content_hash",
    # Fake embeddings
    "FAKE_EMBEDDING_DIM",
    "FakeEmbeddingProvider",
    "get_fake_embedding_provider",
    # Keyword search
    "keyword_search",
    # Vector search
    "vector_search",
    "get_hnsw_params",
    "HNSW_M",
    "HNSW_EF_SEARCH",
    # RRF fusion
    "rrf_fusion",
    "format_rrf_explanation",
    "DEFAULT_RRF_K",
    # Pipeline
    "hybrid_retrieval",
    "simple_retrieval",
    # Traces
    "RetrievalTrace",
    "KeywordResult",
    "VectorResult",
    "FusedResult",
    # Query builder + evidence mapper + retrieve_evidence
    "build_retrieval_query",
    "map_fused_to_evidence",
    "retrieve_evidence",
]


_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "build_retrieval_query": (
        "ticketpilot.retrieval.query_builder",
        "build_retrieval_query",
    ),
    "map_fused_to_evidence": (
        "ticketpilot.retrieval.evidence_mapper",
        "map_fused_to_evidence",
    ),
    "retrieve_evidence": (
        "ticketpilot.retrieval.retrieve_evidence",
        "retrieve_evidence",
    ),
}


def __getattr__(name: str):
    """Lazy-import symbols that would create circular imports at module init."""
    import importlib

    if name in _LAZY_IMPORTS:
        mod_name, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr)
        # Cache in module namespace so __getattr__ fires only once
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
