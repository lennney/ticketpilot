"""Retrieval trace schema for debugging and explainability."""

from datetime import datetime, timezone, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ticketpilot.retrieval.schema.knowledge import DocType


class KeywordResult(BaseModel):
    """Individual keyword search result with explainability."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    content: str
    score: float = Field(..., description="Keyword match score")
    rank: int = Field(..., ge=1, description="Rank in keyword results")
    search_method: str = Field(
        default="fts",
        description="Search method: 'fts' or 'like'",
    )
    fts_rank: Optional[int] = Field(
        default=None,
        description="Rank within FTS results (if applicable)",
    )
    like_rank: Optional[int] = Field(
        default=None,
        description="Rank within LIKE results (if applicable)",
    )


class VectorResult(BaseModel):
    """Individual vector search result with explainability."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    content: str
    score: float = Field(..., description="Cosine similarity score")
    rank: int = Field(..., ge=1, description="Rank in vector results")
    embedding_provider: str = Field(
        default="fake",
        description="Embedding provider used",
    )


class FusedResult(BaseModel):
    """
    Fused retrieval result with per-ranker contribution explainability.

    Shows exactly how the RRF score was calculated from keyword and vector ranks.
    """

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    content: str

    # RRF score components
    rrf_score: float = Field(..., description="Final RRF score")

    # Keyword contribution (if present in keyword results)
    keyword_rank: Optional[int] = Field(
        default=None,
        description="Rank in keyword results",
    )
    keyword_contribution: Optional[float] = Field(
        default=None,
        description="1/(k + keyword_rank)",
    )

    # Vector contribution (if present in vector results)
    vector_rank: Optional[int] = Field(
        default=None,
        description="Rank in vector results",
    )
    vector_contribution: Optional[float] = Field(
        default=None,
        description="1/(k + vector_rank)",
    )

    # Source tracking
    sources: list[str] = Field(
        default_factory=list,
        description="Which rankers found this doc: ['keyword'], ['vector'], or ['keyword', 'vector']",
    )


class RetrievalTrace(BaseModel):
    """
    Complete retrieval trace for debugging, audit, and explainability.

    Captures the full retrieval pipeline:
    - Query and embedding
    - Keyword path (FTS + LIKE fallback)
    - Vector path (HNSW)
    - RRF fusion with per-ranker contributions
    - Final evidence selection
    """

    # Query information
    query: str = Field(..., description="Original query text")
    query_embedding: list[float] = Field(
        default_factory=list,
        description="384-d query embedding",
    )

    # Keyword path
    keyword_results: list[KeywordResult] = Field(
        default_factory=list,
        description="Keyword search results with ranks and scores",
    )
    keyword_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Keyword search latency in milliseconds",
    )
    keyword_search_method: str = Field(
        default="fts",
        description="Primary search method used: 'fts' or 'like'",
    )

    # Vector path
    vector_results: list[VectorResult] = Field(
        default_factory=list,
        description="Vector search results with ranks and scores",
    )
    vector_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Vector search latency in milliseconds",
    )

    # Fusion
    fused_results: list[FusedResult] = Field(
        default_factory=list,
        description="RRF fused results with per-ranker contributions",
    )
    fusion_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Fusion latency in milliseconds",
    )
    rrf_k: int = Field(
        default=60,
        description="RRF k parameter used",
    )

    # Final results
    final_evidence_ids: list[UUID] = Field(
        default_factory=list,
        description="Final selected evidence chunk IDs",
    )

    # Timing
    total_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Total retrieval latency in milliseconds",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Trace creation timestamp",
    )

    # Metadata for audit
    embedding_provider: str = Field(
        default="fake",
        description="Embedding provider identifier",
    )
    hnsw_params: dict[str, Any] = Field(
        default_factory=dict,
        description="HNSW parameters used (m, ef_search)",
    )
    top_k: int = Field(
        default=10,
        description="Requested top-k",
    )
    
    # Re-ranking metadata
    rerank_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Re-ranking latency in milliseconds",
    )
    reranking_enabled: bool = Field(
        default=False,
        description="Whether re-ranking was enabled",
    )

    def get_result_by_chunk_id(self, chunk_id: UUID) -> Optional[FusedResult]:
        """Get fused result by chunk ID."""
        for result in self.fused_results:
            if result.chunk_id == chunk_id:
                return result
        return None

    def get_keyword_result_by_chunk_id(self, chunk_id: UUID) -> Optional[KeywordResult]:
        """Get keyword result by chunk ID."""
        for result in self.keyword_results:
            if result.chunk_id == chunk_id:
                return result
        return None

    def get_vector_result_by_chunk_id(self, chunk_id: UUID) -> Optional[VectorResult]:
        """Get vector result by chunk ID."""
        for result in self.vector_results:
            if result.chunk_id == chunk_id:
                return result
        return None

    def explain_result(self, chunk_id: UUID) -> str:
        """
        Generate human-readable explanation for a result.

        Args:
            chunk_id: Chunk ID to explain

        Returns:
            Formatted string explaining how the result was retrieved and fused
        """
        fused = self.get_result_by_chunk_id(chunk_id)
        if fused is None:
            return f"Chunk {chunk_id} not found in results"

        lines = [
            f"Chunk ID: {chunk_id}",
            f"Doc Type: {fused.doc_type.value}",
            f"RRF Score: {fused.rrf_score:.6f}",
            "",
            "Contributions:",
        ]

        if fused.keyword_rank is not None:
            lines.append(
                f"  Keyword: rank={fused.keyword_rank}, "
                f"contribution=1/({self.rrf_k}+{fused.keyword_rank})={fused.keyword_contribution:.6f}"
            )

        if fused.vector_rank is not None:
            lines.append(
                f"  Vector: rank={fused.vector_rank}, "
                f"contribution=1/({self.rrf_k}+{fused.vector_rank})={fused.vector_contribution:.6f}"
            )

        lines.append("")
        lines.append(f"Sources: {', '.join(fused.sources)}")
        lines.append("")
        lines.append("Content preview:")
        lines.append(f"  {fused.content[:200]}...")

        return "\n".join(lines)