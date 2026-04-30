"""Evidence candidate schema bridging retrieval results to pipeline output."""

from uuid import UUID

from pydantic import BaseModel, Field

from ticketpilot.retrieval.schema.knowledge import DocType


class EvidenceCandidate(BaseModel):
    """A single evidence candidate from retrieval, ready for downstream review."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    source_id: UUID
    source_table: str
    content: str
    score: float
    rank: int = Field(..., ge=1)
    title: str | None = None
