"""Unit tests for generate_draft()."""

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.schemas import DraftReply
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


def _make_output(
    evidence: list | None = None,
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
    intent: IntentClass = IntentClass.REFUND,
    text: str = "我要退款",
) -> TicketOutput:
    return TicketOutput(
        ticket_id=str(uuid4()),
        raw_ticket=RawTicket(
            original_text=text,
            submitted_at=datetime.utcnow(),
        ),
        normalized_ticket=NormalizedTicket(
            text=text,
            language="zh",
            cleaned_at=datetime.utcnow(),
        ),
        classification=ClassificationResult(
            intent=intent,
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
        evidence_candidates=evidence or [],
    )


def _make_evidence(
    rank: int = 1,
    score: float = 0.8,
    content: str = "退货需要在7天内申请，超过7天需要特殊审批。",
    doc_type: DocType = DocType.FAQ,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        doc_type=doc_type,
        source_id=uuid4(),
        source_table=f"knowledge_{doc_type.value.lower()}",
        content=content,
        score=score,
        rank=rank,
    )


class TestGenerateDraft:
    def test_returns_draft_reply_with_evidence(self):
        output = _make_output(evidence=[_make_evidence()])
        result = generate_draft(output)
        assert isinstance(result, DraftReply)
        assert result.draft_text
        assert len(result.citations) == 1
        assert result.confidence > 0.0
        assert result.ticket_id == output.ticket_id

    def test_empty_evidence_fallback(self):
        output = _make_output(evidence=[])
        result = generate_draft(output)
        assert (
            result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        )
        assert result.citations == []
        assert result.evidence_used == []
        assert result.confidence == 0.0
        assert result.must_human_review is True
        assert result.fallback_reason == "no_evidence"
        # Safe fallback text makes no substantive claims; no false positives
        assert result.unsupported_claims == []

    def test_preserves_ticket_id(self):
        output = _make_output(evidence=[_make_evidence()])
        result = generate_draft(output)
        assert result.ticket_id == output.ticket_id

    def test_high_risk_preserves_must_human_review(self):
        output = _make_output(
            evidence=[_make_evidence()],
            must_human_review=True,
        )
        result = generate_draft(output)
        assert result.must_human_review is True

    def test_high_severity_sets_must_human_review(self):
        output = _make_output(
            evidence=[_make_evidence()],
            severity=RiskSeverity.HIGH,
        )
        result = generate_draft(output)
        assert result.must_human_review is True

    def test_unsupported_claims_populated_when_validator_fails(self):
        """When CitationValidator detects issues, unsupported_claims is populated and must_human_review=True."""
        # Patch provider to return a draft with an uncited claim keyword
        with patch("ticketpilot.drafting.generate.FakeDraftProvider") as MockProvider:
            mock_instance = MockProvider.return_value
            # Return a DraftReply whose text triggers the validator
            mock_instance.generate.return_value = DraftReply(
                ticket_id="",
                draft_text="根据公司政策，客户可以申请全额赔偿。",
                citations=[],
            )
            output = _make_output(evidence=[_make_evidence()])
            result = generate_draft(output)
            assert len(result.unsupported_claims) > 0
            assert result.must_human_review is True

    def test_no_mutation_of_ticket_output(self):
        output = _make_output(evidence=[_make_evidence()])
        original_id = output.ticket_id
        original_evidence_count = len(output.evidence_candidates)
        generate_draft(output)
        assert output.ticket_id == original_id
        assert len(output.evidence_candidates) == original_evidence_count

    def test_deterministic_output(self):
        evs = [_make_evidence(rank=1, score=0.8)]
        output = _make_output(evidence=evs)
        r1 = generate_draft(output)
        r2 = generate_draft(output)
        assert r1.draft_text == r2.draft_text
        assert r1.confidence == r2.confidence
        assert len(r1.citations) == len(r2.citations)
        assert r1.must_human_review == r2.must_human_review

    def test_citations_reference_evidence(self):
        ev = _make_evidence(rank=1, score=0.9)
        output = _make_output(evidence=[ev])
        result = generate_draft(output)
        assert len(result.citations) == 1
        assert result.citations[0].chunk_id == ev.chunk_id
        assert result.citations[0].doc_id == ev.doc_id

    def test_handles_exception_gracefully(self):
        """When provider raises, generate_draft returns safe fallback DraftReply."""
        with patch("ticketpilot.drafting.generate.FakeDraftProvider") as MockProvider:
            mock_instance = MockProvider.return_value
            mock_instance.generate.side_effect = RuntimeError("provider failure")
            output = _make_output(evidence=[_make_evidence()])
            result = generate_draft(output)
            assert isinstance(result, DraftReply)
            assert (
                result.draft_text
                == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
            )
            assert result.citations == []
            assert result.confidence == 0.0
            assert result.must_human_review is True
            assert result.fallback_reason == "generation_error"
            assert result.ticket_id == output.ticket_id
            assert result.unsupported_claims == ["生成回复时发生异常"]

    def test_low_risk_no_human_review(self):
        output = _make_output(
            evidence=[_make_evidence()],
            must_human_review=False,
            severity=RiskSeverity.LOW,
        )
        result = generate_draft(output)
        # With normal evidence, no unsupported claims should be detected
        assert result.unsupported_claims == []
        assert result.must_human_review is False

    def test_ticket_id_in_fallback(self):
        output = _make_output(evidence=[])
        result = generate_draft(output)
        assert result.ticket_id == output.ticket_id
