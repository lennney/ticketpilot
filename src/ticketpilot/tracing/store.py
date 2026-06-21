"""ProvenanceStore — in-memory provenance persistence and query.

Stores ResponseProvenance objects and provides query methods:
- get_by_response: lookup by response_id
- get_by_chunk: find all responses that cited a specific chunk

Demo/portfolio implementation (dict-based, no DB).
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from ticketpilot.tracing.provenance import ResponseProvenance


class ProvenanceStore:
    """In-memory store for ResponseProvenance objects."""

    def __init__(self) -> None:
        self._by_response: dict[str, ResponseProvenance] = {}
        self._by_chunk: dict[UUID, list[str]] = {}  # chunk_id → [response_ids]

    def store(self, provenance: ResponseProvenance) -> None:
        """Store a provenance record and index by chunk_id."""
        self._by_response[provenance.response_id] = provenance
        for claim in provenance.claims:
            if claim.source_chunk_id not in self._by_chunk:
                self._by_chunk[claim.source_chunk_id] = []
            if provenance.response_id not in self._by_chunk[claim.source_chunk_id]:
                self._by_chunk[claim.source_chunk_id].append(provenance.response_id)

    def get_by_response(self, response_id: str) -> Optional[ResponseProvenance]:
        """Get provenance by response_id. Returns None if not found."""
        return self._by_response.get(response_id)

    def get_by_chunk(self, chunk_id: UUID) -> list[ResponseProvenance]:
        """Get all provenance records that reference a specific chunk."""
        response_ids = self._by_chunk.get(chunk_id, [])
        return [
            self._by_response[rid] for rid in response_ids if rid in self._by_response
        ]

    def clear(self) -> None:
        """Clear all stored provenance records."""
        self._by_response.clear()
        self._by_chunk.clear()

    @property
    def count(self) -> int:
        """Number of stored provenance records."""
        return len(self._by_response)
