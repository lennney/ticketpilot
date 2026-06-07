"""Provenance schema for full-chain traceability.

Connects retrieval traces to generated claims, enabling:
- "Which knowledge chunk did this answer come from?"
- "How was this chunk retrieved (keyword/vector/fused)?"
- "What was the retrieval confidence?"

Uses Pydantic BaseModel (consistent with all TicketPilot schemas).
Uses UUID for chunk_id/doc_id (consistent with FusedResult, Citation).
"""

from __future__ import annotations

from datetime import datetime, timezone, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClaimProvenance(BaseModel):
    """Provenance for a single claim in a draft reply.

    Traces a claim (typically backed by a [N] citation marker) back to
    the exact knowledge chunk it was derived from, including how that
    chunk was retrieved and with what confidence.
    """

    claim_text: str = Field(description="The claim text from the draft reply")
    citation_index: int = Field(ge=1, description="[N] citation marker index")
    source_chunk_id: UUID = Field(description="Knowledge chunk UUID (matches FusedResult.chunk_id)")
    source_doc_id: UUID = Field(description="Source document UUID (matches FusedResult.doc_id)")
    source_doc_type: str = Field(description="Document type: faq / policy / case")
    retrieval_method: str = Field(description="How chunk was retrieved: keyword / vector / fused")
    retrieval_score: float = Field(ge=0, description="Retrieval score (RRF or raw)")
    confidence: float = Field(ge=0, le=1, description="Provenance confidence (0-1)")


class ResponseProvenance(BaseModel):
    """Full provenance for a draft reply.

    Links every cited claim in the reply back to its source chunk,
    providing end-to-end traceability from answer → citation → chunk → document.
    """

    response_id: str = Field(description="Unique response identifier")
    ticket_id: str = Field(description="Original ticket identifier")
    claims: list[ClaimProvenance] = Field(default_factory=list, description="Provenance for each cited claim")
    overall_confidence: float = Field(ge=0, le=1, description="Overall provenance confidence")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When provenance was generated")
