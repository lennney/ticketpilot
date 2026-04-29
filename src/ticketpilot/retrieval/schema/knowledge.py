"""Knowledge schema models for FAQ, Policy, and Case documents."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DocType(str, Enum):
    """Document type enum for knowledge sources."""

    FAQ = "FAQ"
    POLICY = "POLICY"
    CASE = "CASE"


class ChunkLevel(int, Enum):
    """Chunk level enum for parent-child chunking."""

    PARENT = 1
    CHILD = 2


class BusinessDomain(str, Enum):
    """Business domain enum for ticket categorization."""

    REFUND = "refund"
    RETURN_EXCHANGE = "return_exchange"
    ACCOUNT = "account"
    TECHNICAL = "technical"
    PRODUCT_CONSULTING = "product_consulting"
    LOGISTICS = "logistics"
    COMPLAINT = "complaint"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk level enum for case prioritization."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FAQDocument(BaseModel):
    """FAQ document model."""

    id: UUID = Field(default_factory=uuid4)
    doc_type: DocType = Field(default=DocType.FAQ, frozen=True)
    business_domain: BusinessDomain
    title: str
    content: str
    intent_tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("doc_type", mode="before")
    @classmethod
    def validate_doc_type(cls, v: str | DocType) -> DocType:
        """Ensure doc_type is always FAQ for FAQDocument."""
        if isinstance(v, str) and v.upper() != "FAQ":
            raise ValueError("FAQDocument must have doc_type=FAQ")
        if isinstance(v, DocType) and v != DocType.FAQ:
            raise ValueError("FAQDocument must have doc_type=FAQ")
        return DocType.FAQ


class PolicyDocument(BaseModel):
    """Policy document model."""

    id: UUID = Field(default_factory=uuid4)
    doc_type: DocType = Field(default=DocType.POLICY, frozen=True)
    business_domain: BusinessDomain
    policy_code: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    title: str
    content: str
    effective_date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("doc_type", mode="before")
    @classmethod
    def validate_doc_type(cls, v: str | DocType) -> DocType:
        """Ensure doc_type is always POLICY for PolicyDocument."""
        if isinstance(v, str) and v.upper() != "POLICY":
            raise ValueError("PolicyDocument must have doc_type=POLICY")
        if isinstance(v, DocType) and v != DocType.POLICY:
            raise ValueError("PolicyDocument must have doc_type=POLICY")
        return DocType.POLICY

    @field_validator("policy_code")
    @classmethod
    def validate_policy_code(cls, v: str) -> str:
        """Validate policy_code format X.Y.Z."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("policy_code must be in format X.Y.Z")
        for part in parts:
            if not part.isdigit():
                raise ValueError("policy_code must be in format X.Y.Z")
        return v


class CaseDocument(BaseModel):
    """Case document model."""

    id: UUID = Field(default_factory=uuid4)
    doc_type: DocType = Field(default=DocType.CASE, frozen=True)
    business_domain: BusinessDomain
    case_id: str
    issue_summary: str
    resolution: str
    risk_level: RiskLevel
    compensation_amount: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("doc_type", mode="before")
    @classmethod
    def validate_doc_type(cls, v: str | DocType) -> DocType:
        """Ensure doc_type is always CASE for CaseDocument."""
        if isinstance(v, str) and v.upper() != "CASE":
            raise ValueError("CaseDocument must have doc_type=CASE")
        if isinstance(v, DocType) and v != DocType.CASE:
            raise ValueError("CaseDocument must have doc_type=CASE")
        return DocType.CASE


class KnowledgeChunk(BaseModel):
    """Knowledge chunk model for parent-child chunking.

    Part of the two-layer architecture:
      Source layer: knowledge_faq, knowledge_policy, knowledge_case (separate tables)
      Chunk layer:  knowledge_chunks (unified, with source_table/source_id references)
    """

    id: UUID = Field(default_factory=uuid4)
    doc_id: UUID
    doc_type: DocType
    source_table: str
    source_id: UUID
    parent_chunk_id: Optional[UUID] = None
    chunk_level: ChunkLevel
    business_domain: BusinessDomain
    risk_level: Optional[RiskLevel] = None
    content: str
    content_hash: str = Field(..., min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("chunk_level", mode="before")
    @classmethod
    def validate_chunk_level(cls, v: int | ChunkLevel) -> ChunkLevel:
        """Ensure chunk_level is valid."""
        if isinstance(v, int):
            if v == 1:
                return ChunkLevel.PARENT
            elif v == 2:
                return ChunkLevel.CHILD
            raise ValueError("chunk_level must be 1 (PARENT) or 2 (CHILD)")
        return v

    @field_validator("content_hash", mode="before")
    @classmethod
    def validate_content_hash(cls, v: str) -> str:
        """Validate content_hash is a valid SHA-256 hex string."""
        if len(v) != 64:
            raise ValueError("content_hash must be 64 characters (SHA-256)")
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("content_hash must be a valid hexadecimal string")
        return v.lower()
