"""Maps FusedResult objects from retrieval into EvidenceCandidate objects."""

from ticketpilot.retrieval.traces import FusedResult
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate


def _doc_type_to_source_table(doc_type: DocType) -> str:
    """Map DocType to the corresponding source table name."""
    mapping = {
        DocType.FAQ: "knowledge_faq",
        DocType.POLICY: "knowledge_policy",
        DocType.CASE: "knowledge_case",
    }
    return mapping[doc_type]


def map_fused_to_evidence(results: list[FusedResult]) -> list[EvidenceCandidate]:
    """Convert fused retrieval results to evidence candidates.

    Each FusedResult is mapped to an EvidenceCandidate with rank assigned
    as the 1-based position in the input list. Returns an empty list when
    the input is empty.
    """
    if not results:
        return []

    candidates: list[EvidenceCandidate] = []
    for i, fused in enumerate(results):
        # SEED-ONLY: doc_id == source_id for single-chunk docs.
        # Replace with DB lookup when multi-chunk documents are added.
        candidate = EvidenceCandidate(
            chunk_id=fused.chunk_id,
            doc_id=fused.doc_id,
            doc_type=fused.doc_type,
            source_id=fused.doc_id,
            source_table=_doc_type_to_source_table(fused.doc_type),
            content=fused.content,
            score=fused.rrf_score,
            rank=i + 1,
        )
        candidates.append(candidate)

    return candidates
