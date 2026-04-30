"""Integration tests for end-to-end pipeline with evidence retrieval."""

import pytest

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    RawTicket,
    RiskFlag,
    TicketOutput,
)


class TestPipelineRetrievalIntegration:
    """Integration tests for the 4-stage pipeline with live DB retrieval."""

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
    def _make_ticket(text):
        from datetime import datetime

        return RawTicket(
            original_text=text,
            submitted_at=datetime(2026, 4, 30, 12, 0, 0),
            customer_id="test-integration-001",
        )

    def test_refund_ticket_returns_valid_output_with_trace(
        self, db_available, ensure_seeded
    ):
        """Full pipeline for Chinese refund query returns TicketOutput with trace."""
        if not db_available:
            pytest.skip("Database not available")

        output = intake_risk_pipeline(self._make_ticket("我申请退款，订单号123456"))

        assert isinstance(output, TicketOutput)
        assert isinstance(output.retrieval_trace, RetrievalTrace)
        assert output.retrieval_trace is not None
        assert output.retrieval_trace.query != ""
        assert isinstance(output.evidence_candidates, list)

    def test_account_security_ticket_returns_valid_output_with_trace(
        self, db_available, ensure_seeded
    ):
        """Full pipeline for account/security query returns TicketOutput with trace."""
        if not db_available:
            pytest.skip("Database not available")

        output = intake_risk_pipeline(
            self._make_ticket("我的账号被盗了，有人盗刷了我的订单")
        )

        assert isinstance(output, TicketOutput)
        assert isinstance(output.retrieval_trace, RetrievalTrace)
        assert output.retrieval_trace is not None
        assert output.retrieval_trace.query != ""

    def test_high_risk_ticket_preserves_must_human_review(
        self, db_available, ensure_seeded
    ):
        """High-risk ticket keeps must_human_review=True regardless of retrieval."""
        if not db_available:
            pytest.skip("Database not available")

        output = intake_risk_pipeline(
            self._make_ticket("律师函警告 我要起诉你们 要求赔偿")
        )

        assert output.risk_assessment.must_human_review is True
        assert RiskFlag.LEGAL_RISK in output.risk_assessment.flags
        assert isinstance(output.retrieval_trace, RetrievalTrace)

    def test_low_confidence_does_not_block_retrieval(
        self, db_available, ensure_seeded
    ):
        """LOW_CONFIDENCE classification does not prevent retrieval from running."""
        if not db_available:
            pytest.skip("Database not available")

        # Empty text → intake fallback → OTHER + LOW_CONFIDENCE
        output = intake_risk_pipeline(self._make_ticket(""))

        assert RiskFlag.LOW_CONFIDENCE in output.risk_assessment.flags
        # Retrieval still ran — trace should exist
        assert isinstance(output.retrieval_trace, RetrievalTrace)
        assert output.retrieval_trace is not None

    def test_evidence_candidates_have_required_fields(
        self, db_available, ensure_seeded
    ):
        """Evidence candidates, if non-empty, contain all required fields."""
        if not db_available:
            pytest.skip("Database not available")

        output = intake_risk_pipeline(self._make_ticket("我申请退款，订单号123456"))

        for candidate in output.evidence_candidates:
            assert isinstance(candidate, EvidenceCandidate)
            assert candidate.chunk_id is not None
            assert candidate.doc_id is not None
            assert isinstance(candidate.doc_type, DocType)
            assert candidate.doc_type in (DocType.FAQ, DocType.POLICY, DocType.CASE)
            assert candidate.source_id is not None
            assert isinstance(candidate.source_table, str)
            assert candidate.source_table != ""
            assert isinstance(candidate.content, str)
            assert candidate.content != ""
            assert isinstance(candidate.score, float)
            assert isinstance(candidate.rank, int)
            assert candidate.rank >= 1

    def test_retrieval_trace_has_expected_fields(
        self, db_available, ensure_seeded
    ):
        """RetrievalTrace contains expected structured fields."""
        if not db_available:
            pytest.skip("Database not available")

        output = intake_risk_pipeline(self._make_ticket("退款政策说明"))

        trace = output.retrieval_trace
        assert isinstance(trace, RetrievalTrace)
        assert isinstance(trace.query, str)
        assert trace.query != ""
        assert isinstance(trace.query_embedding, list)
        assert isinstance(trace.keyword_results, list)
        assert isinstance(trace.vector_results, list)
        assert isinstance(trace.fused_results, list)
        assert isinstance(trace.final_evidence_ids, list)
        assert isinstance(trace.total_latency_ms, int)
        assert trace.total_latency_ms >= 0
        assert trace.top_k == 10
        assert isinstance(trace.rrf_k, int)
