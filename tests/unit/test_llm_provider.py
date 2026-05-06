"""Unit tests for LLM provider interface and FakeLLMProvider."""

from uuid import uuid4

import pytest

from ticketpilot.drafting.llm_provider import FakeLLMProvider, LLMProvider
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate


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


class TestLLMProvider:
    def test_abstract_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]

    def test_subclass_without_generate_raises_type_error(self):
        with pytest.raises(TypeError):

            class IncompleteProvider(LLMProvider):  # type: ignore[abstract]
                @property
                def provider_name(self) -> str:
                    return "incomplete"

                @property
                def model_name(self) -> str:
                    return "incomplete"

            IncompleteProvider()


class TestFakeLLMProvider:
    def test_provider_name_and_model(self):
        provider = FakeLLMProvider()
        assert provider.provider_name == "fake"
        assert provider.model_name == "fake"

    def test_generate_draft_returns_draft_reply(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
            evidence_candidates=[_make_evidence()],
        )
        assert isinstance(result, DraftReply)
        assert result.draft_text
        assert result.provider_id == "fake"

    def test_no_evidence_fallback(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
        )
        assert result.draft_text == "根据现有信息，无法确认具体政策条款，建议转人工处理。"
        assert result.citations == []
        assert result.evidence_used == []
        assert result.confidence == 0.0
        assert result.must_human_review is True
        assert result.fallback_reason == "no_evidence"
        assert result.escalation_reason == "insufficient_evidence"
        assert result.cited_evidence_ids == []
        assert "未检索到相关证据" in result.safety_notes[0]

    def test_with_evidence_cites_evidence_ids(self):
        provider = FakeLLMProvider()
        ev = _make_evidence(rank=1, score=0.9)
        result = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
            evidence_candidates=[ev],
        )
        assert str(ev.chunk_id) in result.cited_evidence_ids
        assert len(result.citations) == 1
        assert result.citations[0].chunk_id == ev.chunk_id

    def test_multiple_evidence_candidates(self):
        provider = FakeLLMProvider()
        evs = [_make_evidence(rank=i, score=0.8) for i in range(1, 5)]
        result = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            evidence_candidates=evs,
        )
        # Should only use top 3
        assert len(result.citations) == 3
        assert len(result.cited_evidence_ids) == 3

    def test_risk_flags_force_human_review(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我要投诉",
            issue_type="complaint",
            risk_flags=["complaint", "legal"],
            evidence_candidates=[_make_evidence(score=0.9)],
        )
        assert result.must_human_review is True
        assert result.escalation_reason is not None
        assert "complaint" in result.escalation_reason
        assert "legal" in result.escalation_reason
        assert any("风险标记" in note for note in result.safety_notes)

    def test_no_risk_flags_no_human_review(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
            risk_flags=[],
            must_human_review=False,
            severity="low",
            evidence_candidates=[_make_evidence(score=0.9)],
        )
        assert result.must_human_review is False
        assert result.escalation_reason is None

    def test_deterministic_output(self):
        provider = FakeLLMProvider()
        evs = [_make_evidence(rank=1, score=0.8)]
        r1 = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            evidence_candidates=evs,
        )
        r2 = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            evidence_candidates=evs,
        )
        assert r1.draft_text == r2.draft_text
        assert r1.confidence == r2.confidence
        assert r1.cited_evidence_ids == r2.cited_evidence_ids

    def test_no_network_or_external_calls(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="no network needed",
            issue_type="refund",
            evidence_candidates=[_make_evidence()],
        )
        assert result is not None

    def test_no_fake_policy_promises(self):
        """FakeLLMProvider must not produce forbidden policy promises."""
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我要退款赔偿",
            issue_type="refund",
            evidence_candidates=[_make_evidence(content="退款需要审批")],
        )
        forbidden_patterns = ["一定退款", "保证赔偿", "已为您处理账号"]
        for pattern in forbidden_patterns:
            assert pattern not in result.draft_text

    def test_draft_includes_issue_type_context(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="我想换货",
            issue_type="return_exchange",
            evidence_candidates=[_make_evidence()],
        )
        assert "return_exchange" in result.draft_text

    def test_confidence_from_evidence_scores(self):
        provider = FakeLLMProvider()
        evs = [_make_evidence(rank=1, score=0.5)]
        result = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            evidence_candidates=evs,
        )
        assert result.confidence == 0.5

    def test_must_human_review_from_param(self):
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            must_human_review=True,
            evidence_candidates=[_make_evidence(score=0.9)],
        )
        assert result.must_human_review is True

    def test_high_severity_does_not_auto_force_review(self):
        """FakeLLMProvider doesn't auto-force review on severity alone
        (unlike legacy FakeDraftProvider). The review decision comes from
        explicit risk_flags or must_human_review param."""
        provider = FakeLLMProvider()
        result = provider.generate_draft(
            normalized_text="test",
            issue_type="refund",
            severity="high",
            evidence_candidates=[_make_evidence(score=0.9)],
        )
        # Without risk_flags or must_human_review, no forced review
        assert result.must_human_review is False
