"""Unit tests for CitationValidator."""

from uuid import uuid4

import pytest

from ticketpilot.drafting.citation_validator import CitationValidator
from ticketpilot.drafting.schemas import Citation
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate


@pytest.fixture
def validator() -> CitationValidator:
    return CitationValidator()


@pytest.fixture
def sample_citations() -> list[Citation]:
    return [
        Citation(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table="knowledge_faq",
            source_id=uuid4(),
            evidence_excerpt="退货需要在7天内申请",
            claim_supported=True,
        ),
    ]


@pytest.fixture
def sample_evidence(sample_citations) -> list[EvidenceCandidate]:
    c = sample_citations[0]
    return [
        EvidenceCandidate(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            doc_type=c.doc_type,
            source_id=c.source_id,
            source_table=c.source_table,
            content=c.evidence_excerpt,
            score=0.9,
            rank=1,
        ),
    ]


class TestCitationValidator:
    def test_valid_citations_pass(self, validator, sample_citations, sample_evidence):
        text = "根据政策[1]，退货需要在7天内申请。"
        passed, issues = validator.validate(text, sample_citations, sample_evidence)
        assert passed is True
        assert issues == []

    def test_unknown_chunk_id_detected(self, validator):
        citations = [
            Citation(
                chunk_id=uuid4(),  # not in evidence list
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table="knowledge_faq",
                source_id=uuid4(),
                evidence_excerpt="test",
            ),
        ]
        evidence = [
            EvidenceCandidate(
                chunk_id=uuid4(),  # different UUID
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_id=uuid4(),
                source_table="knowledge_faq",
                content="test",
                score=0.9,
                rank=1,
            ),
        ]
        text = "根据政策[1]。"
        passed, issues = validator.validate(text, citations, evidence)
        assert passed is False
        assert any("unknown chunk_id" in i for i in issues)

    def test_missing_citation_marker_exceeds_count(
        self, validator, sample_citations, sample_evidence
    ):
        text = "根据政策[1]和条款[5]。"
        passed, issues = validator.validate(text, sample_citations, sample_evidence)
        assert passed is False
        assert any("[5]" in i for i in issues)

    def test_unsupported_claim_pattern_detected(self, validator):
        text = "根据相关政策，您可以申请全额退款。"
        passed, issues = validator.validate(text, citations=[], evidence_candidates=[])
        assert passed is False
        assert any("unsupported claim" in i.lower() for i in issues)

    def test_cited_claim_not_flagged(
        self, validator, sample_citations, sample_evidence
    ):
        text = "根据相关政策[1]，您可以申请全额退款。"
        passed, issues = validator.validate(text, sample_citations, sample_evidence)
        assert passed is True

    def test_empty_text_passes(self, validator):
        passed, issues = validator.validate("", citations=[], evidence_candidates=[])
        assert passed is True
        assert issues == []

    def test_multiple_issues_accumulated(self, validator):
        text = "根据政策[5]和[6]，可以退款。"
        passed, issues = validator.validate(text, citations=[], evidence_candidates=[])
        assert passed is False
        # Should have at least 2 citation marker issues
        marker_issues = [i for i in issues if "[" in i]
        assert len(marker_issues) >= 1

    def test_has_unsupported_claims_true_when_issues(self, validator):
        text = "可以退款。"
        result = validator.has_unsupported_claims(text, citations=[])
        assert result is True

    def test_has_unsupported_claims_false_when_clean(self, validator):
        text = "感谢您的耐心等待。"
        result = validator.has_unsupported_claims(text, citations=[])
        assert result is False

    def test_different_doc_type_preserved(self, validator):
        chunk_id = uuid4()
        citations = [
            Citation(
                chunk_id=chunk_id,
                doc_id=uuid4(),
                doc_type=DocType.POLICY,
                source_table="knowledge_policy",
                source_id=uuid4(),
                evidence_excerpt="policy clause",
                claim_supported=True,
            ),
        ]
        evidence = [
            EvidenceCandidate(
                chunk_id=chunk_id,
                doc_id=uuid4(),
                doc_type=DocType.POLICY,
                source_id=uuid4(),
                source_table="knowledge_policy",
                content="policy clause",
                score=0.9,
                rank=1,
            ),
        ]
        text = "根据政策[1]。"
        passed, issues = validator.validate(text, citations, evidence)
        assert passed is True
