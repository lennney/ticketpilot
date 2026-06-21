"""Unit tests for run_pipeline_with_draft()."""

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from ticketpilot.drafting.pipeline import run_pipeline_with_draft
from ticketpilot.drafting.schemas import (
    Citation,
    DraftedTicketResult,
    DraftReply,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskSeverity,
    TicketOutput,
)


def _make_ticket_output(
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
    evidence_count: int = 1,
) -> TicketOutput:
    evidence = [
        EvidenceCandidate(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid4(),
            source_table="knowledge_faq",
            content="退货需要在7天内申请。",
            score=0.8,
            rank=i + 1,
        )
        for i in range(evidence_count)
    ]
    return TicketOutput(
        ticket_id=str(uuid4()),
        raw_ticket=RawTicket(
            original_text="我要退款",
            submitted_at=datetime.utcnow(),
        ),
        normalized_ticket=NormalizedTicket(
            text="我要退款",
            language="zh",
            cleaned_at=datetime.utcnow(),
        ),
        classification=ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=datetime.utcnow(),
        ),
        risk_assessment=RiskAssessment(
            flags=set(),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=datetime.utcnow(),
        ),
        output_at=datetime.utcnow(),
        evidence_candidates=evidence,
    )


def _make_draft_reply(ticket_id: str, must_human_review: bool = False) -> DraftReply:
    return DraftReply(
        ticket_id=ticket_id,
        draft_text="您好，关于您反馈的退款问题，根据相关政策，未发货订单可申请全额退款。",
        citations=[
            Citation(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table="knowledge_faq",
                source_id=uuid4(),
                evidence_excerpt="退货需要在7天内申请。",
            )
        ],
        evidence_used=[],
        unsupported_claims=[],
        missing_information=[],
        confidence=0.8,
        must_human_review=must_human_review,
    )


class TestRunPipelineWithDraft:
    """Tests for the optional pipeline+draft entrypoint."""

    def test_returns_drafted_ticket_result(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            result = run_pipeline_with_draft(ticket_output.raw_ticket)

        assert isinstance(result, DraftedTicketResult)
        assert isinstance(result.ticket_output, TicketOutput)
        assert isinstance(result.draft_reply, DraftReply)

    def test_has_ticket_output_fields(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            result = run_pipeline_with_draft(ticket_output.raw_ticket)

        assert result.ticket_output.ticket_id == ticket_output.ticket_id
        assert result.ticket_output.raw_ticket.original_text == "我要退款"
        assert result.ticket_output.classification.intent == IntentClass.REFUND

    def test_has_draft_reply_fields(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            result = run_pipeline_with_draft(ticket_output.raw_ticket)

        assert result.draft_reply.draft_text == draft_reply.draft_text
        assert len(result.draft_reply.citations) == 1
        assert result.draft_reply.confidence == 0.8

    def test_calls_pipeline_exactly_once(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with patch(
            "ticketpilot.drafting.pipeline.intake_risk_pipeline",
            return_value=ticket_output,
        ) as mock_pipeline:
            with patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ):
                run_pipeline_with_draft(ticket_output.raw_ticket)

        mock_pipeline.assert_called_once()

    def test_calls_generate_draft_exactly_once_with_ticket_output(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with patch(
            "ticketpilot.drafting.pipeline.intake_risk_pipeline",
            return_value=ticket_output,
        ):
            with patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ) as mock_generate:
                run_pipeline_with_draft(ticket_output.raw_ticket)

        mock_generate.assert_called_once_with(ticket_output)

    def test_preserves_high_risk_must_human_review(self):
        ticket_output = _make_ticket_output(
            must_human_review=True, severity=RiskSeverity.HIGH
        )
        draft_reply = _make_draft_reply(ticket_output.ticket_id, must_human_review=True)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            result = run_pipeline_with_draft(ticket_output.raw_ticket)

        assert result.ticket_output.risk_assessment.must_human_review is True
        assert result.draft_reply.must_human_review is True

    def test_does_not_mutate_ticket_output(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        original_id = ticket_output.ticket_id
        original_evidence_count = len(ticket_output.evidence_candidates)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            result = run_pipeline_with_draft(ticket_output.raw_ticket)

        assert result.ticket_output.ticket_id == original_id
        assert len(result.ticket_output.evidence_candidates) == original_evidence_count

    def test_deterministic_output(self):
        ticket_output = _make_ticket_output()
        raw_ticket = ticket_output.raw_ticket
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        with (
            patch(
                "ticketpilot.drafting.pipeline.intake_risk_pipeline",
                return_value=ticket_output,
            ),
            patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ),
        ):
            r1 = run_pipeline_with_draft(raw_ticket)
            r2 = run_pipeline_with_draft(raw_ticket)

        assert r1.ticket_output.ticket_id == r2.ticket_output.ticket_id
        assert r1.draft_reply.draft_text == r2.draft_reply.draft_text
        assert r1.draft_reply.confidence == r2.draft_reply.confidence

    def test_pipeline_called_with_raw_ticket(self):
        ticket_output = _make_ticket_output()
        draft_reply = _make_draft_reply(ticket_output.ticket_id)
        raw_ticket = RawTicket(
            original_text="我的订单怎么还没到？",
            submitted_at=datetime.utcnow(),
        )
        with patch(
            "ticketpilot.drafting.pipeline.intake_risk_pipeline",
            return_value=ticket_output,
        ) as mock_pipeline:
            with patch(
                "ticketpilot.drafting.pipeline.generate_draft",
                return_value=draft_reply,
            ):
                run_pipeline_with_draft(raw_ticket)

        mock_pipeline.assert_called_once_with(raw_ticket)
