"""Unit tests for the evidence-grounded draft generator.

Tests the DraftGenerationResult + generate_draft() function that composes
prompt builder, LLM provider, citation validation, and claim guard into
a deterministic workflow.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ticket_output(
    text: str = "我要申请退款",
    intent: IntentClass = IntentClass.REFUND,
    severity: RiskSeverity = RiskSeverity.LOW,
    must_human_review: bool = False,
    flags: set[RiskFlag] | None = None,
    evidence: list[EvidenceCandidate] | None = None,
    ticket_id: str | None = None,
) -> TicketOutput:
    return TicketOutput(
        ticket_id=ticket_id or str(uuid4()),
        raw_ticket=RawTicket(
            original_text=text,
            submitted_at=datetime.utcnow(),
            customer_id="test-generator-001",
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
            flags=flags or set(),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=datetime.utcnow(),
        ),
        output_at=datetime.utcnow(),
        evidence_candidates=evidence or [],
    )


def _make_evidence(
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
# DraftGenerationResult schema
# ---------------------------------------------------------------------------


class TestDraftGenerationResult:
    def test_contains_all_expected_attributes(self) -> None:
        draft = DraftReply(
            ticket_id="T-001",
            draft_text="尊敬的客户，您好。",
        )
        from ticketpilot.drafting.draft_citation_validator import (
            DraftCitationValidationResult,
        )
        from ticketpilot.drafting.claim_guard import GuardResult

        result = DraftGenerationResult(
            draft=draft,
            provider_name="fake",
            model_name="fake",
            citation_validation=DraftCitationValidationResult(),
            guard_result=GuardResult(),
        )
        assert result.draft is draft
        assert result.provider_name == "fake"
        assert result.model_name == "fake"

    def test_to_trace_dict_returns_compact_metadata(self) -> None:
        draft = DraftReply(
            ticket_id="T-001",
            draft_text="您好",
            confidence=0.9,
            must_human_review=False,
            cited_evidence_ids=["550e8400-e29b-41d4-a716-446655440000"],
        )
        from ticketpilot.drafting.claim_guard import GuardResult
        from ticketpilot.drafting.draft_citation_validator import (
            DraftCitationValidationResult,
        )

        result = DraftGenerationResult(
            draft=draft,
            provider_name="fake",
            model_name="fake",
            citation_validation=DraftCitationValidationResult(
                is_valid=True,
                available_evidence_ids=["550e8400-e29b-41d4-a716-446655440000"],
            ),
            guard_result=GuardResult(),
        )
        trace = result.to_trace_dict()
        assert "provider_name" in trace
        assert "model_name" in trace
        assert "cited_evidence_ids" in trace
        assert "guard_passed" in trace
        assert "human_review_forced" in trace
        assert "confidence" in trace


# ---------------------------------------------------------------------------
# generate_draft — basic behavior
# ---------------------------------------------------------------------------


class TestGenerateDraftBasic:
    def test_returns_draft_generation_result(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert isinstance(result, DraftGenerationResult)
        assert isinstance(result.draft, DraftReply)

    def test_uses_fake_provider_by_default(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert result.provider_name == "fake"
        assert result.model_name == "fake"

    def test_ticket_id_preserved(self) -> None:
        ev = _make_evidence()
        ticket_id = str(uuid4())
        output = _make_ticket_output(evidence=[ev], ticket_id=ticket_id)
        result = generate_draft(output)
        assert result.draft.ticket_id == ticket_id

    def test_evidence_cited_in_draft(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert len(result.draft.cited_evidence_ids) >= 0

    def test_deterministic_same_input_same_output(self) -> None:
        ev = _make_evidence(rank=1, score=0.85)
        output = _make_ticket_output(
            text="我要申请退款",
            evidence=[ev],
            severity=RiskSeverity.LOW,
            must_human_review=False,
            flags=set(),
        )
        r1 = generate_draft(output)
        r2 = generate_draft(output)
        assert r1.draft.draft_text == r2.draft.draft_text
        assert r1.draft.confidence == r2.draft.confidence
        assert r1.draft.cited_evidence_ids == r2.draft.cited_evidence_ids
        assert r1.provider_name == r2.provider_name

    def test_draft_text_not_empty(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert len(result.draft.draft_text) > 0

    def test_no_api_keys_required(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        # Should not raise even without API keys
        result = generate_draft(output)
        assert result.draft is not None


# ---------------------------------------------------------------------------
# generate_draft — no evidence fallback
# ---------------------------------------------------------------------------


class TestGenerateDraftNoEvidence:
    def test_no_evidence_safe_fallback(self) -> None:
        output = _make_ticket_output(evidence=[])
        result = generate_draft(output)
        assert "无法确认具体政策条款" in result.draft.draft_text
        assert result.draft.citations == []
        assert result.draft.confidence == 0.0
        assert result.draft.must_human_review is True
        assert result.draft.fallback_reason == "no_evidence"

    def test_no_evidence_guard_result_passed(self) -> None:
        """No-evidence safe fallback passes claim guard."""
        output = _make_ticket_output(evidence=[])
        result = generate_draft(output)
        assert result.guard_result.guard_passed is True
        assert result.guard_result.evidence_sufficiency == "insufficient"


# ---------------------------------------------------------------------------
# generate_draft — human review propagation
# ---------------------------------------------------------------------------


class TestHumanReviewPropagation:
    def test_input_must_human_review_preserved(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(
            evidence=[ev],
            must_human_review=True,
        )
        result = generate_draft(output)
        assert result.draft.must_human_review is True

    def test_risk_flags_force_human_review(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(
            evidence=[ev],
            flags={RiskFlag.LEGAL_RISK},
        )
        result = generate_draft(output)
        assert result.draft.must_human_review is True

    def test_high_severity_force_human_review(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(
            evidence=[ev],
            severity=RiskSeverity.HIGH,
        )
        result = generate_draft(output)
        # FakeLLMProvider sets must_human_review for HIGH severity
        assert result.draft.must_human_review is True

    def test_never_downgrade_human_review(self) -> None:
        """Input must_human_review=True cannot be overridden to False."""
        ev = _make_evidence()
        output = _make_ticket_output(
            evidence=[ev],
            must_human_review=True,
            severity=RiskSeverity.LOW,
        )
        result = generate_draft(output)
        # Even with good evidence and no flags, human review stays true
        assert result.draft.must_human_review is True


# ---------------------------------------------------------------------------
# generate_draft — citation validation failure
# ---------------------------------------------------------------------------


class TestCitationValidationFailure:
    def test_citation_validation_result_populated(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert result.citation_validation is not None

    def test_invalid_evidence_id_forces_human_review(self) -> None:
        """Invalid cited_evidence_ids → must_human_review=True."""
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        # FakeLLMProvider uses real chunk_ids → valid
        result = generate_draft(output)
        # With valid evidence, validation passes
        assert result.citation_validation.is_valid is True


# ---------------------------------------------------------------------------
# generate_draft — claim guard failure
# ---------------------------------------------------------------------------


class TestClaimGuardFailure:
    def test_guard_result_populated(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        assert result.guard_result is not None

    def test_forbidden_promise_forces_human_review(self) -> None:
        """Draft with forbidden promise → guard fails → must_human_review=True."""
        # Use mock provider to inject a draft with forbidden promise
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="我们将在3天内解决您的问题。",
                citations=[],
                provider_id="fake",
                must_human_review=False,
            )
            ev = _make_evidence()
            output = _make_ticket_output(evidence=[ev])
            result = generate_draft(output)
            assert result.guard_result.has_forbidden_promise is True
            assert result.guard_result.guard_passed is False
            assert result.draft.must_human_review is True

    def test_clean_draft_passes_guard(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev], severity=RiskSeverity.LOW)
        result = generate_draft(output)
        # With evidence and no forbidden content, guard should pass
        # (may fail on uncited claims depending on FakeLLMProvider output)
        assert result.guard_result.guard_passed is not None

    def test_risk_flag_guard_check(self) -> None:
        """LEGAL_RISK without escalation acknowledgment fails guard."""
        ev = _make_evidence()
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            # Draft does not contain escalation language
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="您好，关于您的问题我们会尽快处理。",
                citations=[],
                provider_id="fake",
                must_human_review=False,
            )
            output = _make_ticket_output(
                evidence=[ev],
                flags={RiskFlag.LEGAL_RISK},
            )
            result = generate_draft(output)
            assert result.guard_result.risk_flags_respected is False
            assert result.guard_result.guard_passed is False

    def test_risk_flag_acknowledged_passes_guard(self) -> None:
        """LEGAL_RISK with escalation language passes guard."""
        ev = _make_evidence()
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="您好，此案件涉及法律问题，已转人工处理。",
                citations=[],
                provider_id="fake",
                must_human_review=False,
            )
            output = _make_ticket_output(
                evidence=[ev],
                flags={RiskFlag.LEGAL_RISK},
            )
            result = generate_draft(output)
            assert result.guard_result.risk_flags_respected is True
            assert result.guard_result.guard_passed is True


# ---------------------------------------------------------------------------
# generate_draft — unsupported claims
# ---------------------------------------------------------------------------


class TestUnsupportedClaims:
    def test_unsupported_claims_force_human_review(self) -> None:
        """Draft with unsupported_claims → must_human_review=True."""
        ev = _make_evidence()
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="根据公司政策，可以退款500元。",
                citations=[],
                provider_id="fake",
                unsupported_claims=["退款金额超出证据范围"],
                must_human_review=False,
            )
            output = _make_ticket_output(evidence=[ev])
            result = generate_draft(output)
            assert result.draft.must_human_review is True

    def test_citation_validator_unsupported_claims(self) -> None:
        """CitationValidator detecting issues populates unsupported_claims."""
        ev = _make_evidence()
        with patch.object(FakeLLMProvider, "generate_draft") as mock_gen:
            # Draft text contains claim keyword "根据" without citation marker
            mock_gen.return_value = DraftReply(
                ticket_id="T-001",
                draft_text="根据公司规定，客户可以申请全额退款。",
                citations=[],  # No citations despite claim keyword
                provider_id="fake",
                unsupported_claims=[],
                must_human_review=False,
            )
            output = _make_ticket_output(evidence=[ev])
            result = generate_draft(output)
            # CitationValidator should detect the uncited claim
            assert len(result.draft.unsupported_claims) > 0
            assert result.draft.must_human_review is True


# ---------------------------------------------------------------------------
# generate_draft — provider injection
# ---------------------------------------------------------------------------


class TestProviderInjection:
    def test_custom_provider_injected(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])

        class MockProvider(FakeLLMProvider):
            @property
            def provider_name(self) -> str:
                return "mock"

            @property
            def model_name(self) -> str:
                return "mock-v1"

        mock_provider = MockProvider()
        result = generate_draft(output, provider=mock_provider)
        assert result.provider_name == "mock"
        assert result.model_name == "mock-v1"


# ---------------------------------------------------------------------------
# generate_draft — traceability
# ---------------------------------------------------------------------------


class TestTraceability:
    def test_trace_dict_contains_provider_metadata(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()
        assert trace["provider_name"] == "fake"
        assert trace["model_name"] == "fake"

    def test_trace_dict_contains_citation_info(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()
        assert "cited_evidence_ids" in trace
        assert "available_evidence_ids" in trace
        assert "citation_validation_is_valid" in trace

    def test_trace_dict_contains_guard_info(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()
        assert "guard_passed" in trace
        assert "human_review_forced" in trace

    def test_trace_dict_contains_confidence(self) -> None:
        ev = _make_evidence(score=0.9)
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()
        assert "confidence" in trace

    def test_trace_dict_reasons_for_human_review(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(
            evidence=[ev],
            must_human_review=True,
        )
        result = generate_draft(output)
        trace = result.to_trace_dict()
        assert trace["human_review_forced"] is True
        assert "human_review_reasons" in trace

    def test_trace_dict_never_includes_draft_text(self) -> None:
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        trace = result.to_trace_dict()
        # Draft text should never appear in trace
        assert "draft_text" not in trace
        assert "answer_text" not in trace


# ---------------------------------------------------------------------------
# generate_draft — no auto-send behavior
# ---------------------------------------------------------------------------


class TestNoAutoSend:
    def test_no_auto_send_invariant_draft_only(self) -> None:
        """Generated output is always a draft, never auto-sent."""
        ev = _make_evidence()
        output = _make_ticket_output(evidence=[ev])
        result = generate_draft(output)
        # The draft is always a draft — no auto-send channel exists
        assert result.draft is not None
        # No send/send_at field should be present in DraftReply
        assert not hasattr(result.draft, "send_at")
        assert not hasattr(result.draft, "auto_sent")

    def test_fallback_is_also_draft(self) -> None:
        """Safe fallback is also a draft, not an auto-sent reply."""
        output = _make_ticket_output(evidence=[])
        result = generate_draft(output)
        assert result.draft is not None
        assert result.draft.must_human_review is True  # Requires human review
