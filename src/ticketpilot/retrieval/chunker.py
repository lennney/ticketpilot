"""Parent-child chunking for knowledge documents."""

import hashlib
import re
import uuid
from typing import Optional

from ticketpilot.retrieval.schema.knowledge import (
    BusinessDomain,
    ChunkLevel,
    DocType,
    KnowledgeChunk,
    RiskLevel,
)

# Sentence-ending punctuation patterns
# Chinese: 。！？  English: . ! ?
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"[。！？.!?]")

# Chunk size thresholds (in characters)
_PARENT_SIZE_THRESHOLD = 1000
_CHILD_SIZE_THRESHOLD = 300
_PARENT_TARGET_SIZE = 800
_CHILD_TARGET_SIZE = 150


def compute_content_hash(content: str) -> str:
    """
    Compute SHA-256 hash of normalized content.

    Args:
        content: Raw content string

    Returns:
        64-character hexadecimal SHA-256 hash
    """
    # Normalize: strip whitespace and collapse internal whitespace
    normalized = " ".join(content.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _split_at_sentence_boundary(text: str, target_size: int) -> list[str]:
    """
    Split text at sentence boundaries, targeting a specific chunk size.

    Args:
        text: Text to split
        target_size: Target size for each chunk in characters

    Returns:
        List of text chunks
    """
    if len(text) <= target_size:
        return [text]

    chunks = []
    current_chunk = []
    current_length = 0

    # Find all sentence-ending positions
    matches = list(_SENTENCE_BOUNDARY_PATTERN.finditer(text))

    if not matches:
        # No sentence boundaries found, split by character count
        for i in range(0, len(text), target_size):
            chunks.append(text[i : i + target_size])
        return chunks

    # Process text by sentences
    start = 0
    for match in matches:
        end = match.end()
        sentence = text[start:end]
        sentence_length = len(sentence)

        if current_length + sentence_length <= target_size:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            # Save current chunk if not empty
            if current_chunk:
                chunks.append("".join(current_chunk))
            # Start new chunk
            current_chunk = [sentence]
            current_length = sentence_length
        start = end

    # Handle remaining text
    if start < len(text):
        remaining = text[start:]
        if current_length + len(remaining) <= target_size:
            current_chunk.append(remaining)
        else:
            if current_chunk:
                chunks.append("".join(current_chunk))
            chunks.append(remaining)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


def _split_into_parent_chunks(
    text: str, chunk_size: int = _PARENT_TARGET_SIZE
) -> list[str]:
    """
    Split text into parent chunks at sentence boundaries.

    Args:
        text: Text to split
        chunk_size: Target size for parent chunks (default: 800)

    Returns:
        List of parent chunk strings
    """
    if len(text) <= _PARENT_SIZE_THRESHOLD:
        return [text]

    return _split_at_sentence_boundary(text, chunk_size)


def _create_child_chunks(
    parent_id: uuid.UUID,
    parent_content: str,
    doc_id: uuid.UUID,
    doc_type: DocType,
    source_table: str,
    source_id: uuid.UUID,
    business_domain: BusinessDomain,
    risk_level: Optional[RiskLevel],
) -> list[KnowledgeChunk]:
    """
    Create child chunks from a parent chunk.

    Args:
        parent_id: UUID of the parent chunk
        parent_content: Content of the parent chunk
        doc_id: UUID of the source document
        doc_type: Document type (FAQ, POLICY, CASE)
        source_table: Source table name (knowledge_faq, knowledge_policy, knowledge_case)
        source_id: UUID of the source document row
        business_domain: Business domain classification
        risk_level: Risk level (for CASE documents)

    Returns:
        List of KnowledgeChunk objects (child chunks only)
    """
    # If parent is small enough, no children needed
    if len(parent_content) <= _CHILD_SIZE_THRESHOLD:
        return []

    child_chunks = []
    child_texts = _split_at_sentence_boundary(parent_content, _CHILD_TARGET_SIZE)

    for child_text in child_texts:
        # Create child chunk for each split part
        child_chunk = KnowledgeChunk(
            id=uuid.uuid4(),
            doc_id=doc_id,
            doc_type=doc_type,
            source_table=source_table,
            source_id=source_id,
            parent_chunk_id=parent_id,
            chunk_level=ChunkLevel.CHILD,
            business_domain=business_domain,
            risk_level=risk_level,
            content=child_text,
            content_hash=compute_content_hash(child_text),
        )
        child_chunks.append(child_chunk)

    return child_chunks


def chunk_text(
    text: str,
    doc_id: uuid.UUID,
    doc_type: DocType,
    source_table: str,
    source_id: uuid.UUID,
    business_domain: BusinessDomain,
    risk_level: Optional[RiskLevel] = None,
) -> list[KnowledgeChunk]:
    """
    Chunk text into parent and child KnowledgeChunk objects.

    Algorithm:
    1. PARENT chunk creation:
       - If text length <= 1000 characters: Create single PARENT chunk
       - If text length > 1000 characters: Split into multiple PARENT chunks (~800 chars)
         Split at sentence boundaries (Chinese: 。！？; English: . ! ?)
       - Each PARENT chunk has unique id, parent_chunk_id = NULL

    2. CHILD chunk creation (from each PARENT):
       - If PARENT content length <= 300 characters: No CHILD chunks
       - If PARENT content length > 300 characters: Split into CHILD chunks (~150 chars)
         Each CHILD references parent via parent_chunk_id

    Args:
        text: Full document text to chunk
        doc_id: UUID of the source document
        doc_type: Document type (FAQ, POLICY, CASE)
        source_table: Source table name (knowledge_faq, knowledge_policy, knowledge_case)
        source_id: UUID of the source document row in the source table
        business_domain: Business domain classification
        risk_level: Risk level (optional, for CASE documents)

    Returns:
        List of KnowledgeChunk objects (parent chunks first, then child chunks)
    """
    chunks = []

    # Step 1: Create parent chunks
    parent_texts = _split_into_parent_chunks(text)
    parent_id_map = {}  # Maps index to parent UUID for child creation

    for i, parent_text in enumerate(parent_texts):
        parent_id = uuid.uuid4()
        parent_id_map[i] = parent_id

        parent_chunk = KnowledgeChunk(
            id=parent_id,
            doc_id=doc_id,
            doc_type=doc_type,
            source_table=source_table,
            source_id=source_id,
            parent_chunk_id=None,
            chunk_level=ChunkLevel.PARENT,
            business_domain=business_domain,
            risk_level=risk_level,
            content=parent_text,
            content_hash=compute_content_hash(parent_text),
        )
        chunks.append(parent_chunk)

    # Step 2: Create child chunks from each parent
    for i, parent_text in enumerate(parent_texts):
        parent_id = parent_id_map[i]
        child_chunks = _create_child_chunks(
            parent_id=parent_id,
            parent_content=parent_text,
            doc_id=doc_id,
            doc_type=doc_type,
            source_table=source_table,
            source_id=source_id,
            business_domain=business_domain,
            risk_level=risk_level,
        )
        chunks.extend(child_chunks)

    return chunks
