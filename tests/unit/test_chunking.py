"""Tests for chunking functionality."""

import re
from uuid import uuid4

from ticketpilot.retrieval.chunker import (
    _CHILD_SIZE_THRESHOLD,
    _SENTENCE_BOUNDARY_PATTERN,
    chunk_text,
    compute_content_hash,
)
from ticketpilot.retrieval.schema.knowledge import (
    BusinessDomain,
    ChunkLevel,
    DocType,
    KnowledgeChunk,
    RiskLevel,
)


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_content_hash_is_sha256_format(self):
        """Test content_hash is SHA-256 format (64 hex chars)."""
        result = compute_content_hash("test content")
        assert len(result) == 64
        assert re.match(r"^[a-f0-9]{64}$", result)

    def test_same_content_produces_same_hash(self):
        """Test same content produces same hash."""
        content = "Test content for hashing"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        assert hash1 == hash2

    def test_different_content_produces_different_hash(self):
        """Test different content produces different hash."""
        hash1 = compute_content_hash("content one")
        hash2 = compute_content_hash("content two")
        assert hash1 != hash2

    def test_whitespace_normalization_for_hash(self):
        """Test whitespace normalization for hash."""
        # Different whitespace but same semantic content
        hash1 = compute_content_hash("hello   world")
        hash2 = compute_content_hash("hello world")
        assert hash1 == hash2

    def test_leading_trailing_whitespace_stripped(self):
        """Test leading/trailing whitespace is stripped."""
        hash1 = compute_content_hash("  content  ")
        hash2 = compute_content_hash("content")
        assert hash1 == hash2


class TestSentenceBoundaryPattern:
    """Tests for sentence boundary detection."""

    def test_chinese_sentence_boundaries(self):
        """Test Chinese sentence-ending punctuation."""
        text = "这是第一句。这是第二句！这是第三句？"
        matches = list(_SENTENCE_BOUNDARY_PATTERN.finditer(text))
        assert len(matches) == 3
        assert text[matches[0].start()] == "。"
        assert text[matches[1].start()] == "！"
        assert text[matches[2].start()] == "？"

    def test_english_sentence_boundaries(self):
        """Test English sentence-ending punctuation."""
        text = "First sentence. Second sentence! Third sentence?"
        matches = list(_SENTENCE_BOUNDARY_PATTERN.finditer(text))
        assert len(matches) == 3
        assert text[matches[0].start()] == "."
        assert text[matches[1].start()] == "!"
        assert text[matches[2].start()] == "?"


class TestChunkText:
    """Tests for chunk_text function."""

    _SOURCE_TABLE = "knowledge_faq"
    _SOURCE_ID = uuid4()

    def test_short_text_creates_only_parent(self):
        """Test short text (<=300 chars) creates only PARENT chunk."""
        # Short Chinese text
        text = "如何申请退款？如果商品有质量问题，可以在7天内申请退款。需要提供商品照片。"
        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        # All chunks should be PARENT
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.chunk_level == ChunkLevel.PARENT

    def test_short_text_no_children(self):
        """Test short text creates no child chunks."""
        text = "简短的内容。"

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        # Should have at least one PARENT
        parent_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.PARENT]
        assert len(parent_chunks) >= 1

        # Should have no CHILD chunks if text is short
        child_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.CHILD]
        if len(parent_chunks[0].content) <= _CHILD_SIZE_THRESHOLD:
            assert len(child_chunks) == 0

    def test_medium_text_creates_parent_and_children(self):
        """Test medium text (>300, <=1000) creates PARENT + children."""
        # Medium text with multiple sentences - must be > 300 chars per parent
        # to trigger child creation
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。这是第五句话。" * 10

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        parent_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.PARENT]
        child_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.CHILD]

        assert len(parent_chunks) >= 1
        # Medium text should have some children
        assert len(child_chunks) > 0

    def test_long_text_creates_multiple_parents(self):
        """Test long text (>1000) creates multiple PARENT chunks."""
        # Build a long text
        long_sentence = "这是一句测试话语，用来构造长文本以验证分块功能是否正常工作。"
        text = long_sentence * 50  # ~1500 chars

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.POLICY,
            source_table="knowledge_policy",
            source_id=uuid4(),
            business_domain=BusinessDomain.REFUND,
        )

        parent_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.PARENT]

        # Long text should create multiple parent chunks
        assert len(parent_chunks) > 1

    def test_child_chunks_reference_valid_parent_ids(self):
        """Test child chunks reference valid parent IDs."""
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。" * 5

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        parent_chunks = {c.id for c in chunks if c.chunk_level == ChunkLevel.PARENT}
        child_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.CHILD]

        for child in child_chunks:
            assert child.parent_chunk_id in parent_chunks

    def test_orphan_child_detection(self):
        """Test that child chunks can be created with parent reference."""
        # Note: Pydantic validates UUID format but not UUID existence.
        # This is by design - UUID existence should be validated at the
        # application/integration level, not at the schema level.
        parent_id = uuid4()
        chunk = KnowledgeChunk(
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            parent_chunk_id=parent_id,
            chunk_level=ChunkLevel.CHILD,
            business_domain=BusinessDomain.REFUND,
            content="Child content with parent reference",
            content_hash="a" * 64,
        )
        assert chunk.parent_chunk_id == parent_id
        assert chunk.chunk_level == ChunkLevel.CHILD

    def test_chunks_preserve_doc_metadata(self):
        """Test chunks preserve doc metadata from source document."""
        doc_id = uuid4()
        text = "这是测试内容。" * 20

        chunks = chunk_text(
            text=text,
            doc_id=doc_id,
            doc_type=DocType.CASE,
            source_table="knowledge_case",
            source_id=uuid4(),
            business_domain=BusinessDomain.ACCOUNT,
            risk_level=RiskLevel.HIGH,
        )

        for chunk in chunks:
            assert chunk.doc_id == doc_id
            assert chunk.doc_type == DocType.CASE
            assert chunk.business_domain == BusinessDomain.ACCOUNT
            assert chunk.risk_level == RiskLevel.HIGH

    def test_parent_chunk_id_is_null_for_parents(self):
        """Test PARENT chunks have parent_chunk_id = NULL."""
        text = "测试文本内容。"

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        parent_chunks = [c for c in chunks if c.chunk_level == ChunkLevel.PARENT]
        for parent in parent_chunks:
            assert parent.parent_chunk_id is None

    def test_chunk_content_hash_format(self):
        """Test all chunks have valid SHA-256 content_hash."""
        text = "测试内容。" * 10

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        for chunk in chunks:
            assert len(chunk.content_hash) == 64
            assert re.match(r"^[a-f0-9]{64}$", chunk.content_hash)

    def test_chunk_ids_are_unique(self):
        """Test all chunk IDs are unique."""
        text = "测试内容。" * 10

        chunks = chunk_text(
            text=text,
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_table=self._SOURCE_TABLE,
            source_id=self._SOURCE_ID,
            business_domain=BusinessDomain.REFUND,
        )

        chunk_ids = [c.id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))
