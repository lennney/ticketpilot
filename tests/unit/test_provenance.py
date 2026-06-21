"""Tests for Provenance schema — full-chain traceability."""

import uuid
from datetime import datetime


from ticketpilot.tracing.provenance import ClaimProvenance, ResponseProvenance


class TestClaimProvenance:
    """Tests for ClaimProvenance schema."""

    def _make_claim(self, **overrides) -> ClaimProvenance:
        """Helper to create ClaimProvenance with defaults."""
        defaults = {
            "claim_text": "根据退款政策，7天内可无理由退款",
            "citation_index": 1,
            "source_chunk_id": uuid.uuid4(),
            "source_doc_id": uuid.uuid4(),
            "source_doc_type": "policy",
            "retrieval_method": "fused",
            "retrieval_score": 0.85,
            "confidence": 0.9,
        }
        defaults.update(overrides)
        return ClaimProvenance(**defaults)

    def test_create_claim_provenance(self):
        """ClaimProvenance can be created with all fields."""
        claim = self._make_claim()
        assert claim.claim_text == "根据退款政策，7天内可无理由退款"
        assert claim.citation_index == 1
        assert isinstance(claim.source_chunk_id, uuid.UUID)
        assert isinstance(claim.source_doc_id, uuid.UUID)
        assert claim.source_doc_type == "policy"
        assert claim.retrieval_method == "fused"
        assert claim.retrieval_score == 0.85
        assert claim.confidence == 0.9

    def test_claim_provenance_serialization(self):
        """ClaimProvenance can serialize to dict and back."""
        claim = self._make_claim()
        d = claim.model_dump()
        restored = ClaimProvenance(**d)
        assert restored.claim_text == claim.claim_text
        assert restored.source_chunk_id == claim.source_chunk_id

    def test_claim_provenance_uuid_fields(self):
        """chunk_id and doc_id must be UUID type."""
        claim = self._make_claim()
        assert isinstance(claim.source_chunk_id, uuid.UUID)
        assert isinstance(claim.source_doc_id, uuid.UUID)

    def test_claim_provenance_confidence_range(self):
        """Confidence must be between 0 and 1."""
        # Valid range
        claim = self._make_claim(confidence=0.0)
        assert claim.confidence == 0.0
        claim = self._make_claim(confidence=1.0)
        assert claim.confidence == 1.0

    def test_claim_provenance_retrieval_methods(self):
        """Supports keyword, vector, and fused methods."""
        for method in ("keyword", "vector", "fused"):
            claim = self._make_claim(retrieval_method=method)
            assert claim.retrieval_method == method


class TestResponseProvenance:
    """Tests for ResponseProvenance schema."""

    def _make_provenance(self, num_claims: int = 2) -> ResponseProvenance:
        """Helper to create ResponseProvenance with N claims."""
        claims = [
            ClaimProvenance(
                claim_text=f"Claim {i}",
                citation_index=i,
                source_chunk_id=uuid.uuid4(),
                source_doc_id=uuid.uuid4(),
                source_doc_type="faq",
                retrieval_method="fused",
                retrieval_score=0.8,
                confidence=0.85,
            )
            for i in range(1, num_claims + 1)
        ]
        return ResponseProvenance(
            response_id=str(uuid.uuid4()),
            ticket_id=str(uuid.uuid4()),
            claims=claims,
            overall_confidence=0.85,
            generated_at=datetime.utcnow(),
        )

    def test_create_response_provenance(self):
        """ResponseProvenance can be created with claims list."""
        prov = self._make_provenance(num_claims=3)
        assert len(prov.claims) == 3
        assert prov.overall_confidence == 0.85
        assert isinstance(prov.generated_at, datetime)

    def test_response_provenance_empty_claims(self):
        """ResponseProvenance can have empty claims list."""
        prov = ResponseProvenance(
            response_id=str(uuid.uuid4()),
            ticket_id=str(uuid.uuid4()),
            claims=[],
            overall_confidence=0.0,
            generated_at=datetime.utcnow(),
        )
        assert len(prov.claims) == 0

    def test_response_provenance_serialization(self):
        """ResponseProvenance can serialize to dict and back."""
        prov = self._make_provenance()
        d = prov.model_dump()
        restored = ResponseProvenance(**d)
        assert len(restored.claims) == len(prov.claims)
        assert restored.response_id == prov.response_id

    def test_response_provenance_json_roundtrip(self):
        """ResponseProvenance survives JSON serialization roundtrip."""
        prov = self._make_provenance()
        json_str = prov.model_dump_json()
        restored = ResponseProvenance.model_validate_json(json_str)
        assert restored.response_id == prov.response_id
        assert len(restored.claims) == len(prov.claims)

    def test_provenance_is_pydantic_model(self):
        """Provenance classes are Pydantic BaseModel (not dataclass)."""
        from pydantic import BaseModel

        assert issubclass(ClaimProvenance, BaseModel)
        assert issubclass(ResponseProvenance, BaseModel)
