"""Tests for DraftReply provenance extension and updated confidence tiers."""

import uuid
from datetime import datetime

import pytest

from ticketpilot.drafting.schemas import Citation, DraftReply
from ticketpilot.tracing.provenance import ClaimProvenance, ResponseProvenance
from ticketpilot.retrieval.schema.knowledge import DocType


class TestDraftReplyProvenance:
    """Tests for DraftReply provenance field (backward compatible)."""

    def _make_draft(self, **overrides) -> DraftReply:
        """Helper to create DraftReply with defaults."""
        defaults = {
            "ticket_id": str(uuid.uuid4()),
            "draft_text": "根据退款政策，7天内可无理由退款[1]。",
            "confidence": 0.85,
        }
        defaults.update(overrides)
        return DraftReply(**defaults)

    def _make_provenance(self) -> ResponseProvenance:
        """Helper to create ResponseProvenance."""
        return ResponseProvenance(
            response_id=str(uuid.uuid4()),
            ticket_id=str(uuid.uuid4()),
            claims=[
                ClaimProvenance(
                    claim_text="根据退款政策，7天内可无理由退款",
                    citation_index=1,
                    source_chunk_id=uuid.uuid4(),
                    source_doc_id=uuid.uuid4(),
                    source_doc_type="policy",
                    retrieval_method="fused",
                    retrieval_score=0.85,
                    confidence=0.9,
                )
            ],
            overall_confidence=0.9,
            generated_at=datetime.utcnow(),
        )

    def test_draft_without_provenance(self):
        """DraftReply works without provenance (backward compatible)."""
        draft = self._make_draft()
        assert draft.provenance is None
        assert draft.confidence == 0.85

    def test_draft_with_provenance(self):
        """DraftReply accepts provenance field."""
        prov = self._make_provenance()
        draft = self._make_draft(provenance=prov)
        assert draft.provenance is not None
        assert len(draft.provenance.claims) == 1
        assert draft.provenance.overall_confidence == 0.9

    def test_draft_provenance_serialization(self):
        """DraftReply with provenance serializes correctly."""
        prov = self._make_provenance()
        draft = self._make_draft(provenance=prov)
        d = draft.model_dump()
        assert "provenance" in d
        assert d["provenance"] is not None
        restored = DraftReply(**d)
        assert restored.provenance.response_id == prov.response_id


class TestConfidenceTiers:
    """Tests for updated 4-tier confidence levels."""

    def _make_draft(self, confidence: float) -> DraftReply:
        return DraftReply(
            ticket_id=str(uuid.uuid4()),
            draft_text="测试回复内容",
            confidence=confidence,
        )

    def test_high_confidence(self):
        """confidence > 0.8 → high, autonomous, no human review."""
        draft = self._make_draft(0.9)
        assert draft.confidence_level == "high"
        assert draft.routing_decision == "autonomous"
        assert draft.must_human_review is False

    def test_medium_confidence(self):
        """0.6 <= confidence <= 0.8 → medium, auto_send_cautious, no human review."""
        draft = self._make_draft(0.7)
        assert draft.confidence_level == "medium"
        assert draft.routing_decision == "auto_send_cautious"
        assert draft.must_human_review is False

    def test_low_confidence(self):
        """0.4 <= confidence < 0.6 → low, human_review, must human review."""
        draft = self._make_draft(0.5)
        assert draft.confidence_level == "low"
        assert draft.routing_decision == "human_review"
        assert draft.must_human_review is True
        assert "low_confidence" in (draft.escalation_reason or "")

    def test_critical_confidence(self):
        """confidence < 0.4 → critical, human_escalation, must human review."""
        draft = self._make_draft(0.3)
        assert draft.confidence_level == "critical"
        assert draft.routing_decision == "human_escalation"
        assert draft.must_human_review is True
        assert "critical_confidence" in (draft.escalation_reason or "")

    def test_boundary_high_medium(self):
        """confidence == 0.8 → medium (not high, since high requires > 0.8)."""
        draft = self._make_draft(0.8)
        assert draft.confidence_level == "medium"

    def test_boundary_medium_low(self):
        """confidence == 0.6 → medium."""
        draft = self._make_draft(0.6)
        assert draft.confidence_level == "medium"

    def test_boundary_low_critical(self):
        """confidence == 0.4 → low."""
        draft = self._make_draft(0.4)
        assert draft.confidence_level == "low"

    def test_critical_sets_escalation_reason(self):
        """Critical confidence auto-sets escalation_reason."""
        draft = self._make_draft(0.2)
        assert draft.escalation_reason is not None
        assert "critical_confidence" in draft.escalation_reason
