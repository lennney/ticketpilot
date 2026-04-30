"""Tests for pipeline retrieval integration (Stage 4)."""

import uuid
from datetime import datetime
from unittest.mock import patch

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import RetrievalTrace
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    IntentClass,
    RawTicket,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)


def _make_ticket(text="我要投诉并要求赔偿"):
    return RawTicket(
        original_text=text,
        submitted_at=datetime(2026, 4, 30, 12, 0, 0),
        customer_id="test-001",
    )


def _make_candidates():
    return [
        EvidenceCandidate(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid.uuid4(),
            source_table="knowledge_faq",
            content="退款政策说明",
            score=0.95,
            rank=1,
        )
    ]


def _make_trace():
    return RetrievalTrace(query="test query", query_embedding=[0.0] * 384, top_k=10)


class TestPipelineRetrievalIntegration:
    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_retrieval_called_after_risk_assessment_with_populated_args(
        self, mock_retrieve
    ):
        """Stage 4 must receive intent and risk_flags already populated by prior stages."""
        mock_retrieve.return_value = ([], _make_trace())

        ticket = _make_ticket("我要投诉并要求赔偿")
        output = intake_risk_pipeline(ticket)

        assert mock_retrieve.called
        call_kwargs = mock_retrieve.call_args.kwargs
        assert call_kwargs["normalized_text"] == ticket.original_text
        assert call_kwargs["intent"] in IntentClass
        # "投诉" triggers COMPLAINT_RISK, "赔偿" triggers COMPENSATION_RISK
        assert RiskFlag.COMPLAINT_RISK in call_kwargs["risk_flags"] or (
            RiskFlag.COMPENSATION_RISK in call_kwargs["risk_flags"]
        )
        # intent in call args matches classification output
        assert call_kwargs["intent"] == output.classification.intent

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_successful_retrieval_populates_evidence_and_trace(self, mock_retrieve):
        candidates = _make_candidates()
        trace = _make_trace()
        mock_retrieve.return_value = (candidates, trace)

        output = intake_risk_pipeline(_make_ticket())

        assert output.evidence_candidates == candidates
        assert output.retrieval_trace is trace

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_empty_evidence_adds_insufficient_evidence_flag(self, mock_retrieve):
        mock_retrieve.return_value = ([], _make_trace())

        ticket = _make_ticket("我要投诉你们的客服服务质量太差")
        output = intake_risk_pipeline(ticket)

        assert RiskFlag.INSUFFICIENT_EVIDENCE in output.risk_assessment.flags
        assert output.risk_assessment.must_human_review is True

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_empty_evidence_does_not_mutate_original_flags(self, mock_retrieve):
        """_with_added_risk_flag must create a new set, not mutate the original."""
        captured_flags: list[set[RiskFlag]] = []

        def side_effect(normalized_text, intent, risk_flags, **kwargs):
            captured_flags.append(risk_flags)
            return ([], _make_trace())

        mock_retrieve.side_effect = side_effect

        ticket = _make_ticket("我要投诉你们的客服服务质量太差")
        output = intake_risk_pipeline(ticket)

        # The flags set passed to retrieve_evidence must NOT contain
        # INSUFFICIENT_EVIDENCE — it was added later on a new set.
        original_flags = captured_flags[0]
        assert RiskFlag.INSUFFICIENT_EVIDENCE not in original_flags
        assert RiskFlag.INSUFFICIENT_EVIDENCE in output.risk_assessment.flags
        # The output flags set is a different object from the captured set
        assert output.risk_assessment.flags is not original_flags

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_high_risk_ticket_keeps_human_review_after_retrieval(self, mock_retrieve):
        """must_human_review must not be downgraded by successful retrieval."""
        mock_retrieve.return_value = (_make_candidates(), _make_trace())

        output = intake_risk_pipeline(_make_ticket("律师函警告 我要起诉你们"))

        assert output.risk_assessment.must_human_review is True
        assert RiskFlag.LEGAL_RISK in output.risk_assessment.flags
        assert output.evidence_candidates == mock_retrieve.return_value[0]

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_retrieval_exception_graceful_degradation(self, mock_retrieve):
        mock_retrieve.side_effect = RuntimeError("database connection lost")

        output = intake_risk_pipeline(_make_ticket())

        assert isinstance(output, TicketOutput)
        assert output.evidence_candidates == []
        assert RiskFlag.INSUFFICIENT_EVIDENCE in output.risk_assessment.flags
        assert output.risk_assessment.must_human_review is True

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_exception_does_not_fabricate_evidence(self, mock_retrieve):
        mock_retrieve.side_effect = RuntimeError("boom")

        output = intake_risk_pipeline(_make_ticket())

        assert output.evidence_candidates == []
        assert len(output.evidence_candidates) == 0

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_no_reply_or_draft_field_on_output(self, mock_retrieve):
        mock_retrieve.return_value = (_make_candidates(), _make_trace())

        output = intake_risk_pipeline(_make_ticket())

        assert not hasattr(output, "reply")
        assert not hasattr(output, "draft")
        assert not hasattr(output, "generated_response")

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_retrieval_trace_preserved_on_output(self, mock_retrieve):
        trace = _make_trace()
        mock_retrieve.return_value = (_make_candidates(), trace)

        output = intake_risk_pipeline(_make_ticket())

        assert output.retrieval_trace is trace

    @patch("ticketpilot.pipeline.retrieve_evidence")
    def test_meta_flag_does_not_change_severity(self, mock_retrieve):
        """INSUFFICIENT_EVIDENCE is a meta flag and must not increase severity."""
        mock_retrieve.return_value = ([], _make_trace())

        ticket = _make_ticket("正常客户查询物流配送进度")
        output = intake_risk_pipeline(ticket)

        assert RiskFlag.INSUFFICIENT_EVIDENCE in output.risk_assessment.flags
        assert output.risk_assessment.severity == RiskSeverity.LOW
