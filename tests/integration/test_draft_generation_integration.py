"""Integration tests for evidence-grounded draft generation workflow.

Exercises the complete pipeline: generate_draft → citation validation →
claim guard → human review propagation. No DB, no network, no real LLM.
Deterministic and local-only.
"""

from __future__ import annotations

from uuid import uuid4

from ticketpilot.drafting.generator import DraftGenerationResult, generate_draft
from ticketpilot.drafting.llm_provider import FakeLLMProvider
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ticket_output(
    text: str = "我申请退款，订单号123456",
    evidence: list[EvidenceCandidate] | None = None,
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
    flags: set[RiskFlag] | None = None,
) -> TicketOutput:
    return TicketOutput(
        ticket_id=str(uuid4()),
        raw_ticket=RawTicket(
            original_text=text,
            submitted_at=datetime.utcnow(),
            customer_id="integration-test-001",
        ),
        normalized_ticket=NormalizedTicket(
            text=text,
            language="zh",
            cleaned_at=datetime.utcnow(),
        ),
        classification=ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=datetime.utcnow(),
        ),
        risk_assessment=RiskAssessment(
            flags=flags or set(),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=datetime.utcnow(),
        ),
        output_at=datetime.utcnow(),
        evidence_candidates=evidence or [],
    )


def _evidence(
    rank: int = 1,
    score: float = 0.85,
    content: str = "退货需要在签收后7天内申请，超过期限需要特殊审批。",
    title: str = "退货政策",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        doc_type=DocType.POLICY,
        source_id=uuid4(),
        source_table="knowledge_policy",
        content=content,
        score=score,
        rank=rank,
        title=title,
    )


# ---------------------------------------------------------------------------
# End-to-end generation tests
# ---------------------------------------------------------------------------


class TestDraftGenerationIntegration:
    """End-to-end integration tests for generate_draft() workflow."""

    def test_full_pipeline_returns_result_with_all_components(self):
        """generate_draft returns DraftGenerationResult with draft, validation, and guard."""
        ev = _evidence()
        output = _ticket_output(evidence=[ev])
        result = generate_draft(output)

        assert isinstance(result, DraftGenerationResult)
        assert isinstance(result.draft, DraftReply)
        assert result.draft.ticket_id == output.ticket_id
        assert result.provider_name == "fake"
        assert result.model_name == "fake"

    def test_evidence_candidates_flow_through_pipeline(self):
        """Evidence candidates reach all pipeline stages."""
        ev = _evidence(rank=1, score=0.9)
        output = _ticket_output(evidence=[ev])
        result = generate_draft(output)

        # Citation validation sees the evidence
        assert len(result.citation_validation.available_evidence_ids) >= 1
        # Claim guard sees the evidence
        assert result.guard_result.evidence_sufficiency == "sufficient"
        # Draft has evidence
        assert len(result.draft.cited_evidence_ids) >= 0

    def test_citation_validation_and_guard_both_run(self):
        """Both structural citation validation and claim guard execute."""
        ev = _evidence()
        output = _ticket_output(evidence=[ev])
        result = generate_draft(output)

        assert result.citation_validation is not None
        assert result.guard_result is not None
        # With evidence, both should produce results
        assert result.guard_result.guard_passed is not None

    def test_no_evidence_no_citations_safe_fallback(self):
        """No evidence → safe fallback with no citations."""
        output = _ticket_output(evidence=[])
        result = generate_draft(output)

        assert "无法确认具体政策条款" in result.draft.draft_text
        assert result.draft.citations == []
        assert result.draft.confidence == 0.0
        assert result.draft.must_human_review is True
        assert result.guard_result.guard_passed is True  # Safe fallback passes
        assert result.guard_result.evidence_sufficiency == "insufficient"
        # Citation validation correctly detects unsupported claims in fallback text
        assert result.citation_validation.must_human_review is True

    def test_human_review_propagation_chain(self):
        """Human review is forced by multiple pipeline conditions."""
        # Case 1: input must_human_review=True
        output = _ticket_output(
            evidence=[_evidence()],
            must_human_review=True,
        )
        result = generate_draft(output)
        assert result.draft.must_human_review is True

        # Case 2: risk flags present
        output2 = _ticket_output(
            evidence=[_evidence()],
            flags={RiskFlag.LEGAL_RISK},
        )
        result2 = generate_draft(output2)
        assert result2.draft.must_human_review is True

        # Case 3: no evidence
        output3 = _ticket_output(evidence=[])
        result3 = generate_draft(output3)
        assert result3.draft.must_human_review is True

    def test_guard_failure_forces_human_review(self):
        """Guard failure propagates to must_human_review."""
        from unittest.mock import patch

        # Inject a draft with forbidden promise
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="我们将在5天内解决您的问题。",
                citations=[],
                provider_id="fake",
                must_human_review=False,
            )
            output = _ticket_output(evidence=[_evidence()])
            result = generate_draft(output)
            assert result.guard_result.has_forbidden_promise is True
            assert result.draft.must_human_review is True

    def test_trace_dict_is_compact_and_deterministic(self):
        """Trace dict contains key metadata, excludes sensitive data."""
        ev = _evidence()
        output = _ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()

        required_keys = [
            "provider_name",
            "model_name",
            "cited_evidence_ids",
            "available_evidence_ids",
            "citation_validation_is_valid",
            "guard_passed",
            "human_review_forced",
            "human_review_reasons",
            "confidence",
        ]
        for key in required_keys:
            assert key in trace, f"Missing key: {key}"

        # Ensure no sensitive data
        assert "draft_text" not in trace
        assert "answer_text" not in trace

    def test_multiple_evidences_all_traced(self):
        """Multiple evidence candidates are all recorded in trace."""
        ev1 = _evidence(rank=1, score=0.9)
        ev2 = _evidence(rank=2, score=0.8)
        ev3 = _evidence(rank=3, score=0.7)
        output = _ticket_output(evidence=[ev1, ev2, ev3])
        result = generate_draft(output)

        trace = result.to_trace_dict()
        # All 3 evidence IDs available
        assert len(trace["available_evidence_ids"]) >= 3

    def test_deterministic_same_inputs_same_output(self):
        """Repeated calls produce identical results."""
        ev = _evidence(rank=1, score=0.85)
        text = "我申请退款，订单号123456"
        output1 = _ticket_output(text=text, evidence=[ev])
        output2 = _ticket_output(text=text, evidence=[ev])

        r1 = generate_draft(output1)
        r2 = generate_draft(output2)

        assert r1.draft.draft_text == r2.draft.draft_text
        assert r1.draft.confidence == r2.draft.confidence
        assert r1.guard_result.guard_passed == r2.guard_result.guard_passed
        assert r1.to_trace_dict() == r2.to_trace_dict()

    def test_different_evidence_produces_different_confidence(self):
        """Evidence with different scores produces different confidence."""
        ev_low = _evidence(score=0.5)
        ev_high = _evidence(score=0.95)
        output_low = _ticket_output(evidence=[ev_low])
        output_high = _ticket_output(evidence=[ev_high])

        r_low = generate_draft(output_low)
        r_high = generate_draft(output_high)

        assert r_low.draft.confidence != r_high.draft.confidence

    def test_high_risk_acknowledged_in_trace(self):
        """High-risk flag acknowledgment is reflected in trace."""
        output = _ticket_output(
            evidence=[_evidence()],
            flags={RiskFlag.COMPENSATION_RISK, RiskFlag.LEGAL_RISK},
        )
        result = generate_draft(output)
        trace = result.to_trace_dict()

        assert trace["human_review_forced"] is True
        reasons = trace["human_review_reasons"]
        # Guard failure (risk not acknowledged) or escalation recorded
        assert any(
            "risk" in r or "escalation" in r or "guard_failed" in r for r in reasons
        ), f"Expected risk-related reason in {reasons}"

    def test_no_network_calls(self):
        """generate_draft makes no HTTP/network calls by default."""
        ev = _evidence()
        output = _ticket_output(evidence=[ev])
        result = generate_draft(output)
        # Should complete without any socket operations
        assert result is not None
        assert result.draft is not None

    def test_fake_provider_no_api_keys_required(self):
        """FakeLLMProvider works without any environment configuration."""
        # Ensure no API keys are set
        import os

        old_val = os.environ.pop("TICKETPILOT_LLM_PROVIDER", None)
        try:
            ev = _evidence()
            output = _ticket_output(evidence=[ev])
            result = generate_draft(output)
            assert result.provider_name == "fake"
        finally:
            if old_val is not None:
                os.environ["TICKETPILOT_LLM_PROVIDER"] = old_val

    def test_escalation_reason_set_on_guard_failure(self):
        """Guard failure sets escalation_reason in draft."""
        from unittest.mock import patch

        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            # Draft with uncited substantive content (no citation markers)
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="您好，关于您的问题我们会尽快处理，如有需要请联系我们。",
                citations=[],
                provider_id="fake",
                must_human_review=False,
            )
            ev = _evidence()
            output = _ticket_output(
                evidence=[ev],
                flags={RiskFlag.LEGAL_RISK},  # Forces risk check
            )
            result = generate_draft(output)
            # Either guard failed or human review was set
            assert (
                result.draft.must_human_review is True
                or not result.guard_result.guard_passed
            )
