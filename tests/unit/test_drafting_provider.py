"""Unit tests for FakeDraftProvider."""

from datetime import datetime
from uuid import uuid4

import pytest

from ticketpilot.drafting.provider import (
    NO_EVIDENCE_FALLBACK_TEXT,
    AbstractDraftProvider,
    FakeDraftProvider,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    RiskAssessment,
    RiskSeverity,
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


def _make_risk(
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
) -> RiskAssessment:
    return RiskAssessment(
        flags=set(),
        severity=severity,
        must_human_review=must_human_review,
        assessed_at=datetime.utcnow(),
    )


def _make_classification(intent: IntentClass = IntentClass.REFUND) -> ClassificationResult:
    return ClassificationResult(
        intent=intent,
        confidence=0.9,
        classified_at=datetime.utcnow(),
    )


class TestAbstractDraftProvider:
    def test_abstract_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            AbstractDraftProvider()  # type: ignore[abstract]


class TestFakeDraftProvider:
    def test_provider_returns_draft_reply(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence()],
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="我要退款",
        )
        assert result.ticket_id == ""
        assert result.draft_text
        assert len(result.citations) == 1
        assert result.confidence > 0.0

    def test_citations_match_evidence(self):
        provider = FakeDraftProvider()
        ev = _make_evidence(rank=1, score=0.9)
        result = provider.generate(
            evidence_candidates=[ev],
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert result.citations[0].chunk_id == ev.chunk_id
        assert result.citations[0].doc_id == ev.doc_id
        assert result.citations[0].doc_type == ev.doc_type

    def test_multiple_evidence_candidates(self):
        provider = FakeDraftProvider()
        evs = [_make_evidence(rank=i, score=0.8) for i in range(1, 4)]
        result = provider.generate(
            evidence_candidates=evs,
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert len(result.citations) == 3

    def test_top_three_evidence_used(self):
        provider = FakeDraftProvider()
        evs = [_make_evidence(rank=i, score=0.8) for i in range(1, 6)]
        result = provider.generate(
            evidence_candidates=evs,
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="test",
        )
        # Should only use top 3
        assert len(result.citations) == 3

    def test_empty_evidence_fallback(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[],
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert result.draft_text == NO_EVIDENCE_FALLBACK_TEXT
        assert result.citations == []
        assert result.evidence_used == []
        assert result.confidence == 0.0
        assert result.must_human_review is True
        assert result.fallback_reason == "no_evidence"

    def test_deterministic_output(self):
        provider = FakeDraftProvider()
        evs = [_make_evidence(rank=1, score=0.8)]
        risk = _make_risk()
        cls = _make_classification()
        r1 = provider.generate(
            evidence_candidates=evs,
            risk_assessment=risk,
            classification=cls,
            normalized_text="test",
        )
        r2 = provider.generate(
            evidence_candidates=evs,
            risk_assessment=risk,
            classification=cls,
            normalized_text="test",
        )
        assert r1.draft_text == r2.draft_text
        assert r1.confidence == r2.confidence
        assert len(r1.citations) == len(r2.citations)

    def test_high_risk_sets_must_human_review(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence(score=0.9)],
            risk_assessment=_make_risk(must_human_review=True),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert result.must_human_review is True

    def test_high_severity_sets_must_human_review(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence(score=0.9)],
            risk_assessment=_make_risk(severity=RiskSeverity.HIGH),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert result.must_human_review is True

    def test_low_risk_no_human_review(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence(score=0.9)],
            risk_assessment=_make_risk(
                must_human_review=False, severity=RiskSeverity.LOW
            ),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert result.must_human_review is False

    def test_no_network_or_external_calls(self):
        """FakeDraftProvider should not need network, env vars, or API keys."""
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence()],
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="no network needed",
        )
        # If we got a result without any external setup, the test passes
        assert result is not None

    def test_draft_includes_intent_context(self):
        provider = FakeDraftProvider()
        result = provider.generate(
            evidence_candidates=[_make_evidence()],
            risk_assessment=_make_risk(),
            classification=_make_classification(IntentClass.RETURN_EXCHANGE),
            normalized_text="我想换货",
        )
        assert "return_exchange" in result.draft_text or "换货" in result.draft_text

    def test_excerpt_capped_at_200_chars(self):
        provider = FakeDraftProvider()
        long = "x" * 500
        ev = _make_evidence(rank=1, score=0.8, content=long)
        result = provider.generate(
            evidence_candidates=[ev],
            risk_assessment=_make_risk(),
            classification=_make_classification(),
            normalized_text="test",
        )
        assert len(result.citations[0].evidence_excerpt) <= 200
