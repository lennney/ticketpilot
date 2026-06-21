"""Tests for ProvenanceStore — in-memory provenance persistence."""

import uuid
from datetime import datetime


from ticketpilot.tracing.provenance import ClaimProvenance, ResponseProvenance
from ticketpilot.tracing.store import ProvenanceStore


class TestProvenanceStore:
    """Tests for ProvenanceStore CRUD and query."""

    def _make_provenance(
        self, chunk_ids: list[uuid.UUID] | None = None
    ) -> ResponseProvenance:
        """Create provenance with claims referencing given chunk_ids."""
        if chunk_ids is None:
            chunk_ids = [uuid.uuid4()]
        claims = [
            ClaimProvenance(
                claim_text=f"Claim for chunk {cid}",
                citation_index=i + 1,
                source_chunk_id=cid,
                source_doc_id=uuid.uuid4(),
                source_doc_type="faq",
                retrieval_method="fused",
                retrieval_score=0.8,
                confidence=0.85,
            )
            for i, cid in enumerate(chunk_ids)
        ]
        return ResponseProvenance(
            response_id=str(uuid.uuid4()),
            ticket_id=str(uuid.uuid4()),
            claims=claims,
            overall_confidence=0.85,
            generated_at=datetime.utcnow(),
        )

    def test_store_and_get_by_response(self):
        """Can store and retrieve by response_id."""
        store = ProvenanceStore()
        prov = self._make_provenance()
        store.store(prov)
        assert store.count == 1
        retrieved = store.get_by_response(prov.response_id)
        assert retrieved is not None
        assert retrieved.response_id == prov.response_id

    def test_get_by_response_not_found(self):
        """Returns None for unknown response_id."""
        store = ProvenanceStore()
        assert store.get_by_response("nonexistent") is None

    def test_get_by_chunk(self):
        """Can find all responses referencing a specific chunk."""
        store = ProvenanceStore()
        shared_chunk = uuid.uuid4()
        prov1 = self._make_provenance(chunk_ids=[shared_chunk, uuid.uuid4()])
        prov2 = self._make_provenance(chunk_ids=[shared_chunk])
        prov3 = self._make_provenance(chunk_ids=[uuid.uuid4()])  # different chunk

        store.store(prov1)
        store.store(prov2)
        store.store(prov3)

        results = store.get_by_chunk(shared_chunk)
        assert len(results) == 2
        response_ids = {r.response_id for r in results}
        assert prov1.response_id in response_ids
        assert prov2.response_id in response_ids

    def test_get_by_chunk_not_found(self):
        """Returns empty list for unknown chunk_id."""
        store = ProvenanceStore()
        assert store.get_by_chunk(uuid.uuid4()) == []

    def test_clear(self):
        """Clear removes all records."""
        store = ProvenanceStore()
        store.store(self._make_provenance())
        store.store(self._make_provenance())
        assert store.count == 2
        store.clear()
        assert store.count == 0

    def test_store_overwrites_same_response_id(self):
        """Storing same response_id twice overwrites the first."""
        store = ProvenanceStore()
        prov = self._make_provenance()
        store.store(prov)
        store.store(prov)  # same response_id
        assert store.count == 1
