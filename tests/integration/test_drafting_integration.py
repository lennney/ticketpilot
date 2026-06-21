"""Integration tests for the optional drafting workflow (run_pipeline_with_draft)."""

import pytest

from ticketpilot.drafting.pipeline import run_pipeline_with_draft
from ticketpilot.drafting.schemas import (
    DraftedTicketResult,
    DraftReply,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.ticket import (
    RawTicket,
    RiskFlag,
    TicketOutput,
)


class TestDraftingIntegration:
    """Integration tests for run_pipeline_with_draft with live DB."""

    @pytest.fixture
    def db_available(self):
        """Check if database is available."""
        try:
            from ticketpilot.retrieval.db.connection import get_db_connection

            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    @pytest.fixture
    def ensure_seeded(self, db_available):
        """Ensure database is seeded with test data."""
        if not db_available:
            pytest.skip("Database not available")
        try:
            from ticketpilot.retrieval.db.seeding import (
                seed_knowledge_chunks,
                get_chunk_count,
            )

            if get_chunk_count() == 0:
                seed_knowledge_chunks(clear_existing=True)
        except Exception as e:
            pytest.skip(f"Could not seed database: {e}")

    @staticmethod
    def _make_ticket(text: str) -> RawTicket:
        from datetime import datetime

        return RawTicket(
            original_text=text,
            submitted_at=datetime(2026, 5, 2, 12, 0, 0),
            customer_id="test-drafting-integration-001",
        )

    def test_returns_drafted_ticket_result(self, db_available, ensure_seeded):
        """run_pipeline_with_draft returns DraftedTicketResult with both halves."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        assert isinstance(result, DraftedTicketResult)
        assert isinstance(result.ticket_output, TicketOutput)
        assert isinstance(result.draft_reply, DraftReply)

    def test_ticket_output_preserved(self, db_available, ensure_seeded):
        """TicketOutput fields are preserved through the drafting workflow."""
        if not db_available:
            pytest.skip("Database not available")

        raw_ticket = self._make_ticket("我申请退款，订单号123456")
        result = run_pipeline_with_draft(raw_ticket)

        assert (
            result.ticket_output.raw_ticket.original_text == "我申请退款，订单号123456"
        )
        assert result.ticket_output.ticket_id != ""
        assert result.ticket_output.ticket_id == result.draft_reply.ticket_id
        assert isinstance(result.ticket_output.evidence_candidates, list)

    def test_draft_reply_has_expected_structure(self, db_available, ensure_seeded):
        """DraftReply has deterministic fields regardless of evidence."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        draft = result.draft_reply
        assert isinstance(draft.draft_text, str)
        assert len(draft.draft_text) > 0
        assert isinstance(draft.citations, list)
        assert isinstance(draft.evidence_used, list)
        assert isinstance(draft.unsupported_claims, list)
        assert isinstance(draft.confidence, float)
        assert isinstance(draft.must_human_review, bool)
        assert draft.fallback_reason is None or isinstance(draft.fallback_reason, str)

    def test_draft_is_chinese(self, db_available, ensure_seeded):
        """Draft reply text is in Chinese."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        assert result.draft_reply.draft_text.startswith("您好")
        assert (
            "退款" in result.draft_reply.draft_text
            or "人工" in result.draft_reply.draft_text
        )

    def test_evidence_backed_case_has_citations(self, db_available, ensure_seeded):
        """When evidence exists, draft has citations referencing real evidence."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        evidence = result.ticket_output.evidence_candidates
        draft = result.draft_reply

        if evidence:
            assert len(draft.citations) > 0
            assert len(draft.citations) <= len(evidence)
            for citation in draft.citations:
                assert citation.chunk_id is not None
                assert citation.doc_id is not None
                assert isinstance(citation.doc_type, DocType)
                assert isinstance(citation.source_table, str)
                assert citation.source_table != ""
                assert isinstance(citation.evidence_excerpt, str)
                assert len(citation.evidence_excerpt) > 0
            # Every citation doc_type should be a valid DocType enum
            for citation in draft.citations:
                assert citation.doc_type in (DocType.FAQ, DocType.POLICY, DocType.CASE)
        else:
            # No evidence → fallback
            assert draft.citations == []
            assert draft.confidence == 0.0
            assert draft.fallback_reason == "no_evidence"

    def test_high_risk_preserves_must_human_review(self, db_available, ensure_seeded):
        """High-risk ticket preserves must_human_review=True in draft."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(
            self._make_ticket("律师函警告 我要起诉你们 要求赔偿")
        )

        assert result.ticket_output.risk_assessment.must_human_review is True
        assert RiskFlag.LEGAL_RISK in result.ticket_output.risk_assessment.flags
        assert result.draft_reply.must_human_review is True

    def test_confidence_is_bounded(self, db_available, ensure_seeded):
        """Confidence is always in [0.0, 1.0]."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        assert 0.0 <= result.draft_reply.confidence <= 1.0

    def test_low_confidence_not_raise(self, db_available, ensure_seeded):
        """Empty or low-confidence input does not raise — falls back safely."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket(""))

        draft = result.draft_reply
        assert isinstance(draft, DraftReply)
        # Either we got a fallback or a deterministic low-confidence draft
        if not result.ticket_output.evidence_candidates:
            assert draft.confidence == 0.0
            assert draft.citations == []
        else:
            assert draft.confidence < 0.5

    def test_draft_deterministic_for_same_ticket(self, db_available, ensure_seeded):
        """Repeated calls with same input produce identical draft."""
        if not db_available:
            pytest.skip("Database not available")

        raw_ticket = self._make_ticket("我申请退款，订单号123456")
        r1 = run_pipeline_with_draft(raw_ticket)
        r2 = run_pipeline_with_draft(raw_ticket)

        assert r1.draft_reply.draft_text == r2.draft_reply.draft_text
        assert r1.draft_reply.confidence == r2.draft_reply.confidence
        assert len(r1.draft_reply.citations) == len(r2.draft_reply.citations)

    def test_draft_does_not_make_unsupported_policy_claims(
        self, db_available, ensure_seeded
    ):
        """Draft does not make policy promises without supporting citations."""
        if not db_available:
            pytest.skip("Database not available")

        result = run_pipeline_with_draft(self._make_ticket("我申请退款，订单号123456"))

        draft = result.draft_reply
        evidence = result.ticket_output.evidence_candidates

        if not evidence:
            # Fallback — safe text, no substantive claims
            assert "无法确认具体政策条款" in draft.draft_text
            assert draft.citations == []
            assert draft.confidence == 0.0
        else:
            # Evidence exists — every substantive claim should have a citation
            # The provider template always places [N] markers alongside content
            assert len(draft.citations) > 0
            # The draft text must contain citation markers [1], [2], etc.
            assert "[1]" in draft.draft_text or len(draft.citations) == 0
            # confidence should be proportional to evidence
            assert draft.confidence > 0.0
