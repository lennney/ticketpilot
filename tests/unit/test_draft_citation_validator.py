"""Unit tests for DraftCitationValidator."""

from uuid import uuid4

from ticketpilot.drafting.draft_citation_validator import (
    DraftCitationValidationResult,
    validate_draft_citations,
)
from ticketpilot.drafting.llm_provider import SAFE_FALLBACK_TEXT
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


class TestDraftCitationValidationResult:
    def test_default_values(self):
        result = DraftCitationValidationResult()
        assert result.is_valid is True
        assert result.valid_cited_evidence_ids == []
        assert result.invalid_cited_evidence_ids == []
        assert result.duplicate_cited_evidence_ids == []
        assert result.missing_citation_required is False
        assert result.available_evidence_ids == []
        assert result.errors == []
        assert result.warnings == []
        assert result.must_human_review is False


class TestValidateDraftCitations:
    def test_valid_cited_id_passes(self):
        ev = _make_evidence(rank=1)
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="根据政策内容，退货需要7天内申请。",
            cited_evidence_ids=[str(ev.chunk_id)],
        )
        result = validate_draft_citations(draft, [ev])
        assert result.is_valid is True
        assert str(ev.chunk_id) in result.valid_cited_evidence_ids
        assert result.invalid_cited_evidence_ids == []

    def test_multiple_valid_ids_pass(self):
        evs = [_make_evidence(rank=i) for i in range(1, 4)]
        cited = [str(ev.chunk_id) for ev in evs]
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=cited,
        )
        result = validate_draft_citations(draft, evs)
        assert result.is_valid is True
        assert len(result.valid_cited_evidence_ids) == 3
        assert all(eid in result.valid_cited_evidence_ids for eid in cited)

    def test_invalid_cited_id_fails(self):
        ev = _make_evidence(rank=1)
        fake_id = str(uuid4())
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[str(ev.chunk_id), fake_id],
        )
        result = validate_draft_citations(draft, [ev])
        assert result.is_valid is False
        assert fake_id in result.invalid_cited_evidence_ids
        assert result.must_human_review is True
        assert any("Invalid cited" in e for e in result.errors)

    def test_duplicate_id_reported(self):
        ev = _make_evidence(rank=1)
        eid = str(ev.chunk_id)
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[eid, eid],
        )
        result = validate_draft_citations(draft, [ev])
        # Duplicates are warnings, not fatal
        assert eid in result.duplicate_cited_evidence_ids
        assert result.is_valid is True
        assert any("Duplicate" in w for w in result.warnings)

    def test_no_evidence_plus_cited_id_fails(self):
        fake_id = str(uuid4())
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[fake_id],
        )
        result = validate_draft_citations(draft, [])
        assert result.is_valid is False
        assert fake_id in result.invalid_cited_evidence_ids
        assert result.must_human_review is True
        assert any("No evidence candidates" in e for e in result.errors)

    def test_no_evidence_safe_fallback_passes_structurally(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text=SAFE_FALLBACK_TEXT,
            cited_evidence_ids=[],
        )
        result = validate_draft_citations(draft, [])
        assert result.is_valid is True
        assert result.missing_citation_required is False
        assert any("No evidence candidates" in w for w in result.warnings)

    def test_substantive_text_no_citations_marks_missing(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="根据我们的退款政策，您可以申请全额退款。",
            cited_evidence_ids=[],
        )
        result = validate_draft_citations(draft, [_make_evidence()])
        assert result.missing_citation_required is True
        assert any("missing" in w.lower() for w in result.warnings)

    def test_safe_fallback_no_citations_does_not_require_citation(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text=SAFE_FALLBACK_TEXT,
            cited_evidence_ids=[],
        )
        result = validate_draft_citations(draft, [])
        assert result.missing_citation_required is False

    def test_unsupported_claims_force_must_human_review(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[],
            unsupported_claims=["缺少退款政策引用"],
        )
        result = validate_draft_citations(draft, [_make_evidence()])
        assert result.must_human_review is True
        assert result.is_valid is False
        assert any("unsupported" in e.lower() for e in result.errors)

    def test_must_human_review_propagates(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            must_human_review=True,
            cited_evidence_ids=[str(_make_evidence().chunk_id)],
            evidence_used=[],
        )
        result = validate_draft_citations(draft, [_make_evidence()])
        assert result.must_human_review is True

    def test_validation_failure_forces_must_human_review(self):
        ev = _make_evidence(rank=1)
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            must_human_review=False,
            cited_evidence_ids=[str(uuid4())],
        )
        result = validate_draft_citations(draft, [ev])
        assert result.must_human_review is True

    def test_never_downgrades_human_review(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            must_human_review=True,
            cited_evidence_ids=[str(_make_evidence().chunk_id)],
        )
        result = validate_draft_citations(draft, [_make_evidence()])
        assert result.must_human_review is True

    def test_available_evidence_ids_reported(self):
        evs = [_make_evidence(rank=i) for i in range(1, 4)]
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[str(evs[0].chunk_id)],
        )
        result = validate_draft_citations(draft, evs)
        assert len(result.available_evidence_ids) == 3
        assert all(str(ev.chunk_id) in result.available_evidence_ids for ev in evs)

    def test_deterministic_output_same_input(self):
        ev = _make_evidence(rank=1)
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[str(ev.chunk_id)],
        )
        r1 = validate_draft_citations(draft, [ev])
        r2 = validate_draft_citations(draft, [ev])
        assert r1.is_valid == r2.is_valid
        assert r1.valid_cited_evidence_ids == r2.valid_cited_evidence_ids
        assert r1.errors == r2.errors
        assert r1.warnings == r2.warnings

    def test_empty_evidence_content_does_not_break_validator(self):
        ev = _make_evidence(rank=1, content="")
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[str(ev.chunk_id)],
        )
        result = validate_draft_citations(draft, [ev])
        # Empty content doesn't affect ID validation
        assert result.is_valid is True
        assert str(ev.chunk_id) in result.valid_cited_evidence_ids

    def test_fake_llm_provider_output_validates(self):
        from ticketpilot.drafting.llm_provider import FakeLLMProvider

        provider = FakeLLMProvider()
        ev = _make_evidence(rank=1, score=0.9)
        draft = provider.generate_draft(
            normalized_text="我要退款",
            issue_type="refund",
            evidence_candidates=[ev],
        )
        result = validate_draft_citations(draft, [ev])
        assert result.is_valid is True
        assert str(ev.chunk_id) in result.valid_cited_evidence_ids

    def test_no_evidence_no_citations_is_valid(self):
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="您好，感谢您的咨询。",
            cited_evidence_ids=[],
        )
        result = validate_draft_citations(draft, [])
        assert result.is_valid is True
        # Greeting-only text without substance isn't flagged as missing citation
        # (it's not a safe fallback either, but it's a non-substantive greeting)

    def test_partial_invalid_ids_reported(self):
        ev = _make_evidence(rank=1)
        valid_id = str(ev.chunk_id)
        invalid_id = str(uuid4())
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[valid_id, invalid_id],
        )
        result = validate_draft_citations(draft, [ev])
        assert valid_id in result.valid_cited_evidence_ids
        assert invalid_id in result.invalid_cited_evidence_ids
        assert result.is_valid is False

    def test_mixed_duplicates_and_invalid(self):
        ev = _make_evidence(rank=1)
        valid_id = str(ev.chunk_id)
        invalid_id = str(uuid4())
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="test",
            cited_evidence_ids=[valid_id, valid_id, invalid_id],
        )
        result = validate_draft_citations(draft, [ev])
        assert valid_id in result.valid_cited_evidence_ids
        assert invalid_id in result.invalid_cited_evidence_ids
        assert valid_id in result.duplicate_cited_evidence_ids
        assert result.is_valid is False
        assert result.must_human_review is True

    def test_draft_with_citations_does_not_flag_missing(self):
        ev = _make_evidence(rank=1)
        draft = DraftReply(
            ticket_id="tkt-001",
            draft_text="根据政策，可以退款。",
            cited_evidence_ids=[str(ev.chunk_id)],
        )
        result = validate_draft_citations(draft, [ev])
        assert result.missing_citation_required is False
