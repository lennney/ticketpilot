"""Retrieval schema models for queries, results, and traces."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ticketpilot.retrieval.schema.knowledge import BusinessDomain, DocType


class RetrievalQuery(BaseModel):
    """Retrieval query model."""

    query_text: str
    doc_types: Optional[list[DocType]] = None
    business_domains: Optional[list[BusinessDomain]] = None
    top_k: int = Field(default=10, ge=1, le=100)


class RetrievalResult(BaseModel):
    """Retrieval result model."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    content: str
    score: float = Field(..., ge=0.0, le=1.0)
    rank: int = Field(..., ge=1)


class RetrievalSchema(BaseModel):
    """Retrieval trace model for debugging and analysis."""

    query: Optional[str] = None
    query_embedding: Optional[list[float]] = None
    keyword_results: Optional[list[dict[str, Any]]] = None
    vector_results: Optional[list[dict[str, Any]]] = None
    fused_results: Optional[list[dict[str, Any]]] = None
    final_evidence: Optional[dict[str, Any]] = None
    retrieved_doc_ids: Optional[list[UUID]] = None
    retrieval_latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
