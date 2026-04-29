"""Tests for knowledge schema models."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ticketpilot.retrieval.schema.knowledge import (
    BusinessDomain,
    CaseDocument,
    ChunkLevel,
    DocType,
    FAQDocument,
    KnowledgeChunk,
    PolicyDocument,
    RiskLevel,
)


class TestDocType:
    """Tests for DocType enum."""

    def test_doc_type_has_faq_policy_case(self):
        """Test DocType enum has FAQ, POLICY, CASE values."""
        assert DocType.FAQ.value == "FAQ"
        assert DocType.POLICY.value == "POLICY"
        assert DocType.CASE.value == "CASE"

    def test_doc_type_is_string_enum(self):
        """Test DocType is a string enum."""
        assert isinstance(DocType.FAQ, str)
        assert DocType.FAQ == "FAQ"


class TestChunkLevel:
    """Tests for ChunkLevel enum."""

    def test_chunk_level_has_parent_child(self):
        """Test ChunkLevel enum has PARENT and CHILD values."""
        assert ChunkLevel.PARENT.value == 1
        assert ChunkLevel.CHILD.value == 2

    def test_chunk_level_is_int_enum(self):
        """Test ChunkLevel is an int enum."""
        assert isinstance(ChunkLevel.PARENT, int)
        assert ChunkLevel.PARENT == 1


class TestBusinessDomain:
    """Tests for BusinessDomain enum."""

    def test_business_domain_has_all_8_values(self):
        """Test BusinessDomain enum has all 8 required values."""
        expected = [
            "refund",
            "return_exchange",
            "account",
            "technical",
            "product_consulting",
            "logistics",
            "complaint",
            "other",
        ]
        for domain in expected:
            assert hasattr(BusinessDomain, domain.upper())
            assert getattr(BusinessDomain, domain.upper()).value == domain


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_has_low_medium_high(self):
        """Test RiskLevel enum has LOW, MEDIUM, HIGH values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


class TestFAQDocument:
    """Tests for FAQDocument model."""

    def test_faq_document_validation(self):
        """Test FAQDocument validation with valid data."""
        doc = FAQDocument(
            business_domain=BusinessDomain.REFUND,
            title="Test FAQ",
            content="This is test content",
            intent_tags=["tag1", "tag2"],
        )
        assert doc.doc_type == DocType.FAQ
        assert doc.business_domain == BusinessDomain.REFUND
        assert doc.title == "Test FAQ"
        assert doc.content == "This is test content"
        assert doc.intent_tags == ["tag1", "tag2"]

    def test_faq_document_doc_type_fixed(self):
        """Test that FAQDocument forces doc_type to FAQ."""
        with pytest.raises(ValidationError):
            FAQDocument(
                doc_type=DocType.POLICY,  # Should be rejected
                business_domain=BusinessDomain.REFUND,
                title="Test",
                content="Test",
            )


class TestPolicyDocument:
    """Tests for PolicyDocument model."""

    def test_policy_document_validation(self):
        """Test PolicyDocument validation with valid data."""
        doc = PolicyDocument(
            business_domain=BusinessDomain.REFUND,
            policy_code="7.3.2",
            title="Test Policy",
            content="This is policy content",
            effective_date=date(2024, 1, 1),
        )
        assert doc.doc_type == DocType.POLICY
        assert doc.policy_code == "7.3.2"

    def test_policy_document_policy_code_format(self):
        """Test PolicyDocument requires X.Y.Z format for policy_code."""
        with pytest.raises(ValidationError):
            PolicyDocument(
                business_domain=BusinessDomain.REFUND,
                policy_code="invalid",  # Should fail
                title="Test",
                content="Test",
                effective_date=date(2024, 1, 1),
            )

    def test_policy_document_policy_code_valid_formats(self):
        """Test PolicyDocument accepts valid policy_code formats."""
        for code in ["1.0.0", "7.3.2", "10.15.99"]:
            doc = PolicyDocument(
                business_domain=BusinessDomain.REFUND,
                policy_code=code,
                title="Test",
                content="Test content",
                effective_date=date(2024, 1, 1),
            )
            assert doc.policy_code == code


class TestCaseDocument:
    """Tests for CaseDocument model."""

    def test_case_document_validation(self):
        """Test CaseDocument validation with valid data."""
        doc = CaseDocument(
            business_domain=BusinessDomain.REFUND,
            case_id="CASE-2024-001",
            issue_summary="Issue description",
            resolution="Resolution description",
            risk_level=RiskLevel.HIGH,
            compensation_amount=100.50,
        )
        assert doc.doc_type == DocType.CASE
        assert doc.case_id == "CASE-2024-001"
        assert doc.risk_level == RiskLevel.HIGH
        assert doc.compensation_amount == 100.50

    def test_case_document_compensation_optional(self):
        """Test CaseDocument compensation_amount is optional."""
        doc = CaseDocument(
            business_domain=BusinessDomain.REFUND,
            case_id="CASE-2024-002",
            issue_summary="Issue",
            resolution="Resolution",
            risk_level=RiskLevel.LOW,
        )
        assert doc.compensation_amount is None


class TestKnowledgeChunk:
    """Tests for KnowledgeChunk model."""

    # Two-layer source references used across all chunk constructors
    _SOURCE_TABLE = "knowledge_faq"
    _SOURCE_ID = uuid4()

    def test_knowledge_chunk_parent_level(self):
        """Test KnowledgeChunk with parent_chunk_id=None (PARENT level)."""
        chunk = KnowledgeChunk(
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            parent_chunk_id=None,
            chunk_level=ChunkLevel.PARENT,
            business_domain=BusinessDomain.REFUND,
            content="Parent chunk content",
            content_hash="a" * 64,
        )
        assert chunk.parent_chunk_id is None
        assert chunk.chunk_level == ChunkLevel.PARENT

    def test_knowledge_chunk_child_level(self):
        """Test KnowledgeChunk with parent_chunk_id set (CHILD level)."""
        parent_id = uuid4()
        chunk = KnowledgeChunk(
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            parent_chunk_id=parent_id,
            chunk_level=ChunkLevel.CHILD,
            business_domain=BusinessDomain.REFUND,
            content="Child chunk content",
            content_hash="b" * 64,
        )
        assert chunk.parent_chunk_id == parent_id
        assert chunk.chunk_level == ChunkLevel.CHILD

    def test_knowledge_chunk_has_all_required_fields(self):
        """Test KnowledgeChunk has all required fields."""
        chunk = KnowledgeChunk(
            doc_id=uuid4(),
            doc_type=DocType.POLICY,
            source_table="knowledge_policy",
            source_id=uuid4(),
            chunk_level=ChunkLevel.PARENT,
            business_domain=BusinessDomain.ACCOUNT,
            content="Test content",
            content_hash="c" * 64,
        )
        assert hasattr(chunk, "id")
        assert hasattr(chunk, "doc_id")
        assert hasattr(chunk, "doc_type")
        assert hasattr(chunk, "source_table")
        assert hasattr(chunk, "source_id")
        assert hasattr(chunk, "parent_chunk_id")
        assert hasattr(chunk, "chunk_level")
        assert hasattr(chunk, "business_domain")
        assert hasattr(chunk, "risk_level")
        assert hasattr(chunk, "content")
        assert hasattr(chunk, "content_hash")
        assert hasattr(chunk, "created_at")

    def test_knowledge_chunk_invalid_content_hash(self):
        """Test KnowledgeChunk rejects invalid content_hash."""
        with pytest.raises(ValidationError):
            KnowledgeChunk(
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table=self._SOURCE_TABLE,
                source_id=self._SOURCE_ID,
                business_domain=BusinessDomain.REFUND,
                content="Test",
                content_hash="invalid",  # Too short
            )

    def test_knowledge_chunk_content_hash_must_be_hex(self):
        """Test KnowledgeChunk content_hash must be valid hexadecimal."""
        with pytest.raises(ValidationError):
            KnowledgeChunk(
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table=self._SOURCE_TABLE,
                source_id=self._SOURCE_ID,
                business_domain=BusinessDomain.REFUND,
                content="Test",
                content_hash="g" * 64,  # 'g' is not valid hex
            )

    def test_knowledge_chunk_with_risk_level(self):
        """Test KnowledgeChunk can have risk_level for CASE documents."""
        chunk = KnowledgeChunk(
            doc_id=uuid4(),
            doc_type=DocType.CASE,
            source_table="knowledge_case",
            source_id=uuid4(),
            chunk_level=ChunkLevel.PARENT,
            business_domain=BusinessDomain.REFUND,
            risk_level=RiskLevel.HIGH,
            content="High risk case chunk",
            content_hash="d" * 64,
        )
        assert chunk.risk_level == RiskLevel.HIGH
