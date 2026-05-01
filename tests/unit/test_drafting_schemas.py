"""Unit tests for drafting Pydantic schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from ticketpilot.drafting.schemas import Citation, DraftGenerationTrace, DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType


class TestCitation:
    def test_valid_citation(self):
        chunk_id = uuid4()
        doc_id = uuid4()
        source_id = uuid4()
        c = Citation(
            chunk_id=chunk_id,
            doc_id=doc_id,
            doc_type=DocType.FAQ,
            source_table="knowledge_faq",
            source_id=source_id,
            evidence_excerpt="退货需要在7天内申请",
            claim_supported=True,
        )
        assert c.chunk_id == chunk_id
        assert c.doc_id == doc_id
        assert c.doc_type == DocType.FAQ
        assert c.source_table == "knowledge_faq"
        assert c.source_id == source_id
        assert c.evidence_excerpt == "退货需要在7天内申请"
        assert c.claim_supported is True

    def test_evidence_excerpt_max_length(self):
        with pytest.raises(ValidationError):
            Citation(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type=DocType.POLICY,
                source_table="knowledge_policy",
                source_id=uuid4(),
                evidence_excerpt="x" * 201,
            )

    def test_claim_supported_default_false(self):
        c = Citation(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.CASE,
            source_table="knowledge_case",
            source_id=uuid4(),
            evidence_excerpt="test",
        )
        assert c.claim_supported is False

    def test_invalid_doc_type_rejected(self):
        with pytest.raises(ValidationError):
            Citation(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type="INVALID",  # type: ignore[arg-type]
                source_table="knowledge_case",
                source_id=uuid4(),
                evidence_excerpt="test",
            )


class TestDraftReply:
    def test_valid_draft_reply(self):
        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="您好，关于您的退款问题...",
            citations=[],
            evidence_used=[],
            confidence=0.85,
        )
        assert dr.ticket_id == "tkt-001"
        assert dr.draft_text == "您好，关于您的退款问题..."
        assert dr.confidence == 0.85
        assert dr.must_human_review is False
        assert dr.fallback_reason is None

    def test_confidence_default_zero(self):
        dr = DraftReply(ticket_id="tkt-001", draft_text="您好")
        assert dr.confidence == 0.0

    def test_must_human_review_default_false(self):
        dr = DraftReply(ticket_id="tkt-001", draft_text="您好")
        assert dr.must_human_review is False

    def test_unsupported_claims_default_empty(self):
        dr = DraftReply(ticket_id="tkt-001", draft_text="您好")
        assert dr.unsupported_claims == []

    def test_missing_information_default_empty(self):
        dr = DraftReply(ticket_id="tkt-001", draft_text="您好")
        assert dr.missing_information == []

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            DraftReply(ticket_id="tkt-001", draft_text="您好", confidence=-0.1)

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            DraftReply(ticket_id="tkt-001", draft_text="您好", confidence=1.5)

    def test_fallback_reason_stored(self):
        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="fallback",
            fallback_reason="no_evidence",
        )
        assert dr.fallback_reason == "no_evidence"

    def test_generation_trace_stored(self):
        dr = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            generation_trace={"key": "value"},
        )
        assert dr.generation_trace == {"key": "value"}


class TestDraftGenerationTrace:
    def test_valid_trace(self):
        trace = DraftGenerationTrace(
            ticket_id="tkt-001",
            evidence_count=3,
            total_evidence_available=5,
            confidence_score=0.8,
        )
        assert trace.ticket_id == "tkt-001"
        assert trace.evidence_count == 3
        assert trace.total_evidence_available == 5
        assert trace.confidence_score == 0.8
        assert trace.human_review_required is False
        assert trace.fallback_reason is None

    def test_human_review_required_default_false(self):
        trace = DraftGenerationTrace(ticket_id="tkt-001")
        assert trace.human_review_required is False

    def test_fallback_reason_default_none(self):
        trace = DraftGenerationTrace(ticket_id="tkt-001")
        assert trace.fallback_reason is None

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            DraftGenerationTrace(ticket_id="tkt-001", confidence_score=1.5)
