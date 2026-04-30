"""Tests for evidence_mapper mapping FusedResult to EvidenceCandidate."""

import uuid

from ticketpilot.retrieval.evidence_mapper import (
    _doc_type_to_source_table,
    map_fused_to_evidence,
)
from ticketpilot.retrieval.traces import FusedResult
from ticketpilot.retrieval.schema.knowledge import DocType


def _make_fused(
    chunk_id: uuid.UUID,
    doc_id: uuid.UUID,
    doc_type: DocType,
    content: str,
    rrf_score: float,
    keyword_rank: int | None = None,
    vector_rank: int | None = None,
) -> FusedResult:
    return FusedResult(
        chunk_id=chunk_id,
        doc_id=doc_id,
        doc_type=doc_type,
        content=content,
        rrf_score=rrf_score,
        keyword_rank=keyword_rank,
        keyword_contribution=1.0 / (60 + keyword_rank) if keyword_rank else None,
        vector_rank=vector_rank,
        vector_contribution=1.0 / (60 + vector_rank) if vector_rank else None,
        sources=(
            ["keyword"] if keyword_rank and not vector_rank
            else ["vector"] if vector_rank and not keyword_rank
            else ["keyword", "vector"]
        ),
    )


class TestDocTypeToSourceTable:
    def test_faq_maps_to_knowledge_faq(self):
        assert _doc_type_to_source_table(DocType.FAQ) == "knowledge_faq"

    def test_policy_maps_to_knowledge_policy(self):
        assert _doc_type_to_source_table(DocType.POLICY) == "knowledge_policy"

    def test_case_maps_to_knowledge_case(self):
        assert _doc_type_to_source_table(DocType.CASE) == "knowledge_case"


class TestMapFusedToEvidence:
    def test_non_empty_results_map_correctly(self):
        chunk_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        fused = [
            _make_fused(chunk_id, doc_id, DocType.FAQ, "退款政策说明", 0.95, keyword_rank=1),
        ]
        candidates = map_fused_to_evidence(fused)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.chunk_id == chunk_id
        assert c.doc_id == doc_id
        assert c.doc_type == DocType.FAQ
        assert c.source_id == doc_id  # SEED-ONLY assumption
        assert c.source_table == "knowledge_faq"
        assert c.content == "退款政策说明"
        assert c.score == 0.95
        assert c.rank == 1

    def test_rank_ordering_preserved(self):
        first_id = uuid.uuid4()
        second_id = uuid.uuid4()
        fused = [
            _make_fused(first_id, uuid.uuid4(), DocType.FAQ, "first", 0.99, keyword_rank=1),
            _make_fused(second_id, uuid.uuid4(), DocType.FAQ, "second", 0.85, keyword_rank=2),
        ]
        candidates = map_fused_to_evidence(fused)
        assert len(candidates) == 2
        assert candidates[0].rank == 1
        assert candidates[0].score == 0.99
        assert candidates[1].rank == 2
        assert candidates[1].score == 0.85
        assert candidates[0].score >= candidates[1].score

    def test_empty_input_returns_empty_list(self):
        assert map_fused_to_evidence([]) == []

    def test_source_table_derivation_all_doc_types(self):
        faq_id = uuid.uuid4()
        policy_id = uuid.uuid4()
        case_id = uuid.uuid4()
        fused = [
            _make_fused(faq_id, uuid.uuid4(), DocType.FAQ, "faq content", 0.9, keyword_rank=1),
            _make_fused(policy_id, uuid.uuid4(), DocType.POLICY, "policy content", 0.8, keyword_rank=2),
            _make_fused(case_id, uuid.uuid4(), DocType.CASE, "case content", 0.7, keyword_rank=3),
        ]
        candidates = map_fused_to_evidence(fused)
        assert candidates[0].source_table == "knowledge_faq"
        assert candidates[1].source_table == "knowledge_policy"
        assert candidates[2].source_table == "knowledge_case"

    def test_rrf_score_mapped_to_score(self):
        fused = [
            _make_fused(uuid.uuid4(), uuid.uuid4(), DocType.FAQ, "test", 0.72, keyword_rank=3),
        ]
        candidates = map_fused_to_evidence(fused)
        assert candidates[0].score == 0.72

    def test_title_defaults_to_none(self):
        fused = [
            _make_fused(uuid.uuid4(), uuid.uuid4(), DocType.FAQ, "test", 0.5, keyword_rank=1),
        ]
        candidates = map_fused_to_evidence(fused)
        assert candidates[0].title is None
