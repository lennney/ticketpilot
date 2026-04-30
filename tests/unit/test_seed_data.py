"""Tests for seed data."""

import re
from pathlib import Path

import pytest

from ticketpilot.retrieval.schema.knowledge import (
    CaseDocument,
    FAQDocument,
    PolicyDocument,
)
from ticketpilot.retrieval.schema.seeds import (
    load_case_seed_data,
    load_faq_seed_data,
    load_policy_seed_data,
)


class TestSeedDataFiles:
    """Tests for seed data JSON files."""

    @pytest.fixture
    def seed_data_dir(self):
        """Get seed data directory path."""
        return Path(__file__).parent.parent.parent / "data" / "knowledge"

    def test_faq_seed_file_exists(self, seed_data_dir):
        """Test FAQ seed file exists."""
        faq_path = seed_data_dir / "faq_seed.json"
        assert faq_path.exists()

    def test_policy_seed_file_exists(self, seed_data_dir):
        """Test Policy seed file exists."""
        policy_path = seed_data_dir / "policy_seed.json"
        assert policy_path.exists()

    def test_case_seed_file_exists(self, seed_data_dir):
        """Test Case seed file exists."""
        case_path = seed_data_dir / "case_seed.json"
        assert case_path.exists()


class TestFAQQuality:
    """Tests for FAQ seed data quality."""

    def test_faq_seed_count(self):
        """Test FAQ seed count >= 10."""
        faq_docs = load_faq_seed_data()
        assert len(faq_docs) >= 10

    def test_policy_seed_count(self):
        """Test Policy seed count >= 10."""
        policy_docs = load_policy_seed_data()
        assert len(policy_docs) >= 10

    def test_case_seed_count(self):
        """Test Case seed count >= 10."""
        case_docs = load_case_seed_data()
        assert len(case_docs) >= 10

    def test_faq_spans_multiple_business_domains(self):
        """Test FAQ spans >= 4 business_domains."""
        faq_docs = load_faq_seed_data()
        domains = set(doc.business_domain.value for doc in faq_docs)
        assert len(domains) >= 4

    def test_policy_spans_multiple_business_domains(self):
        """Test Policy spans >= 4 business_domains."""
        policy_docs = load_policy_seed_data()
        domains = set(doc.business_domain.value for doc in policy_docs)
        assert len(domains) >= 4

    def test_case_spans_multiple_business_domains(self):
        """Test Case spans >= 4 business_domains."""
        case_docs = load_case_seed_data()
        domains = set(doc.business_domain.value for doc in case_docs)
        assert len(domains) >= 4


class TestFAQDocumentValidation:
    """Tests for FAQ document validation."""

    def test_all_faq_documents_are_valid(self):
        """Test all FAQ documents are valid FAQDocument."""
        faq_docs = load_faq_seed_data()
        for doc in faq_docs:
            assert isinstance(doc, FAQDocument)
            assert doc.doc_type.value == "FAQ"

    def test_faq_has_required_fields(self):
        """Test each FAQ has required fields."""
        faq_docs = load_faq_seed_data()
        for doc in faq_docs:
            assert doc.id is not None
            assert doc.title is not None
            assert doc.content is not None
            assert doc.business_domain is not None
            assert len(doc.content) > 0


class TestPolicyDocumentValidation:
    """Tests for Policy document validation."""

    def test_all_policy_documents_are_valid(self):
        """Test all Policy documents are valid PolicyDocument."""
        policy_docs = load_policy_seed_data()
        for doc in policy_docs:
            assert isinstance(doc, PolicyDocument)
            assert doc.doc_type.value == "POLICY"

    def test_policy_code_format_x_y_z(self):
        """Test all Policy documents have valid policy_code format X.Y.Z."""
        policy_docs = load_policy_seed_data()
        pattern = re.compile(r"^\d+\.\d+\.\d+$")
        for doc in policy_docs:
            assert pattern.match(doc.policy_code), f"Invalid policy_code: {doc.policy_code}"

    def test_policy_has_required_fields(self):
        """Test each Policy has required fields."""
        policy_docs = load_policy_seed_data()
        for doc in policy_docs:
            assert doc.id is not None
            assert doc.policy_code is not None
            assert doc.title is not None
            assert doc.content is not None
            assert doc.effective_date is not None


class TestCaseDocumentValidation:
    """Tests for Case document validation."""

    def test_all_case_documents_are_valid(self):
        """Test all Case documents are valid CaseDocument."""
        case_docs = load_case_seed_data()
        for doc in case_docs:
            assert isinstance(doc, CaseDocument)
            assert doc.doc_type.value == "CASE"

    def test_case_has_valid_risk_level(self):
        """Test all Case documents have valid risk_level."""
        case_docs = load_case_seed_data()
        valid_levels = {"low", "medium", "high"}
        for doc in case_docs:
            assert doc.risk_level.value in valid_levels

    def test_case_has_required_fields(self):
        """Test each Case has required fields."""
        case_docs = load_case_seed_data()
        for doc in case_docs:
            assert doc.id is not None
            assert doc.case_id is not None
            assert doc.issue_summary is not None
            assert doc.resolution is not None
            assert doc.risk_level is not None


class TestSeedDataIntegrity:
    """Tests for seed data integrity."""

    def test_faq_doc_type_fixed_to_faq(self):
        """Test all FAQ documents have doc_type=FAQ."""
        faq_docs = load_faq_seed_data()
        for doc in faq_docs:
            assert doc.doc_type.value == "FAQ"

    def test_policy_doc_type_fixed_to_policy(self):
        """Test all Policy documents have doc_type=POLICY."""
        policy_docs = load_policy_seed_data()
        for doc in policy_docs:
            assert doc.doc_type.value == "POLICY"

    def test_case_doc_type_fixed_to_case(self):
        """Test all Case documents have doc_type=CASE."""
        case_docs = load_case_seed_data()
        for doc in case_docs:
            assert doc.doc_type.value == "CASE"
