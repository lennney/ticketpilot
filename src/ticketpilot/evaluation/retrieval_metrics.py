"""Pure metric functions for retrieval comparison evaluation.

All functions are pure and deterministic:
- Operate on in-memory objects only
- Do NOT call pipeline, DB, embedding provider, LLM, network, or filesystem
- Produce identical results for identical inputs
- Gracefully handle missing doc_id golden expectations (skip doc_id metrics)
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default k values for top-k metrics
DEFAULT_KS: list[int] = [1, 3, 5, 10]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RetrievedDoc:
    """A single retrieved document in a comparison case."""

    doc_id: str
    doc_type: str
    rank: int
    score: float


@dataclass
class RetrievalComparisonCase:
    """A single case's retrieval results vs golden expectations.

    Fields:
        case_id: Unique case identifier matching golden expectations.
        query: The search query used for retrieval.
        retrieved_docs: List of retrieved documents, sorted by rank.
        expected_doc_types: Set of doc types that should appear in results.
        expected_doc_ids: Set of doc IDs that should appear, or None if not available.
    """

    case_id: str
    query: str
    retrieved_docs: list[RetrievedDoc]
    expected_doc_types: frozenset[str]
    expected_doc_ids: frozenset[str] | None = None


@dataclass
class CaseRetrievalMetrics:
    """Per-case retrieval metrics.

    Fields:
        case_id: Unique case identifier.
        top_k_doc_type_hit: Whether an expected doc_type appears in top-k, per k.
        top_k_doc_id_hit: Whether an expected doc_id appears in top-k, per k.
            None if no doc_id golden expectations available.
        reciprocal_rank_doc_type: 1/(rank of first expected doc_type), 0.0 if none.
        reciprocal_rank_doc_id: 1/(rank of first expected doc_id), None if no doc_id golden.
    """

    case_id: str
    top_k_doc_type_hit: dict[int, bool]
    top_k_doc_id_hit: dict[int, bool] | None = None
    reciprocal_rank_doc_type: float = 0.0
    reciprocal_rank_doc_id: float | None = None


@dataclass
class WrongCaseEntry:
    """A retrieval case that failed to retrieve expected evidence."""

    case_id: str
    failure_mode: str
    details: str
    top_k_doc_type_hit: dict[int, bool] = field(default_factory=dict)
    reciprocal_rank_doc_type: float = 0.0


@dataclass
class RetrievalComparisonSummary:
    """Aggregate retrieval comparison metrics across all cases.

    Fields:
        total_cases: Number of cases evaluated.
        hit_rate_doc_type: Doc-type hit rate at each k.
        hit_rate_doc_id: Doc-id hit rate at each k, or None if no doc_id golden.
        mrr_doc_type: Mean Reciprocal Rank for doc-type relevance.
        mrr_doc_id: Mean Reciprocal Rank for doc-id relevance, or None.
        per_case: Dict of case_id -> CaseRetrievalMetrics.
        wrong_cases: List of WrongCaseEntry for retrieval failures.
    """

    total_cases: int
    hit_rate_doc_type: dict[int, float]
    hit_rate_doc_id: dict[int, float] | None = None
    mrr_doc_type: float = 0.0
    mrr_doc_id: float | None = None
    per_case: dict[str, CaseRetrievalMetrics] = field(default_factory=dict)
    wrong_cases: list[WrongCaseEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def compute_hit_rate_at_k(hits: list[bool]) -> float:
    """Compute hit rate from a list of per-case hit booleans at a given k.

    Args:
        hits: List of booleans, one per case, indicating whether a hit occurred.

    Returns:
        Hit rate in [0.0, 1.0]. Returns 0.0 for empty list.
    """
    if not hits:
        return 0.0
    return sum(hits) / len(hits)


def compute_mrr(reciprocal_ranks: list[float]) -> float:
    """Compute Mean Reciprocal Rank.

    Args:
        reciprocal_ranks: List of reciprocal rank values, one per case.
            Each value is in [0.0, 1.0] where 0.0 means no relevant result found.

    Returns:
        MRR in [0.0, 1.0]. Returns 0.0 for empty list.
    """
    if not reciprocal_ranks:
        return 0.0
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def _find_first_relevant_rank_by_doc_type(
    retrieved: list[RetrievedDoc],
    expected_doc_types: set[str],
) -> int | None:
    """Find the 1-based rank of the first retrieved doc with an expected doc_type.

    Args:
        retrieved: List of retrieved docs sorted by rank (ascending).
        expected_doc_types: Set of expected doc_type values.

    Returns:
        1-based rank, or None if no relevant doc found.
    """
    for doc in retrieved:
        if doc.doc_type in expected_doc_types:
            return doc.rank
    return None


def _find_first_relevant_rank_by_doc_id(
    retrieved: list[RetrievedDoc],
    expected_doc_ids: set[str],
) -> int | None:
    """Find the 1-based rank of the first retrieved doc with an expected doc_id.

    Args:
        retrieved: List of retrieved docs sorted by rank (ascending).
        expected_doc_ids: Set of expected doc_id values.

    Returns:
        1-based rank, or None if no relevant doc found.
    """
    for doc in retrieved:
        if doc.doc_id in expected_doc_ids:
            return doc.rank
    return None


def _is_any_doc_type_in_top_k(
    retrieved: list[RetrievedDoc],
    expected_doc_types: set[str],
    k: int,
) -> bool:
    """Check whether any expected doc_type appears within the top-k results."""
    for doc in retrieved[:k]:
        if doc.doc_type in expected_doc_types:
            return True
    return False


def _is_any_doc_id_in_top_k(
    retrieved: list[RetrievedDoc],
    expected_doc_ids: set[str],
    k: int,
) -> bool:
    """Check whether any expected doc_id appears within the top-k results."""
    for doc in retrieved[:k]:
        if doc.doc_id in expected_doc_ids:
            return True
    return False


# ---------------------------------------------------------------------------
# Per-case computation
# ---------------------------------------------------------------------------


def compute_case_retrieval_metrics(
    case: RetrievalComparisonCase,
    ks: list[int] | None = None,
) -> CaseRetrievalMetrics:
    """Compute all retrieval metrics for a single case.

    Args:
        case: The comparison case with retrieved results and golden expectations.
        ks: List of k values for top-k metrics. Defaults to [1, 3, 5, 10].

    Returns:
        CaseRetrievalMetrics with per-case metric values.
    """
    if ks is None:
        ks = DEFAULT_KS

    retrieved = sorted(case.retrieved_docs, key=lambda d: d.rank)
    expected_types = set(case.expected_doc_types)

    # Doc-type level
    type_hits = {
        k: _is_any_doc_type_in_top_k(retrieved, expected_types, k) for k in ks
    }
    first_type_rank = _find_first_relevant_rank_by_doc_type(retrieved, expected_types)
    rr_type = 1.0 / first_type_rank if first_type_rank is not None else 0.0

    # Doc-id level (optional — only if golden expectations include doc_ids)
    id_hits: dict[int, bool] | None = None
    rr_id_val: float | None = None
    if case.expected_doc_ids is not None and len(case.expected_doc_ids) > 0:
        expected_ids = set(case.expected_doc_ids)
        id_hits = {k: _is_any_doc_id_in_top_k(retrieved, expected_ids, k) for k in ks}
        first_id_rank = _find_first_relevant_rank_by_doc_id(retrieved, expected_ids)
        rr_id_val = 1.0 / first_id_rank if first_id_rank is not None else 0.0

    return CaseRetrievalMetrics(
        case_id=case.case_id,
        top_k_doc_type_hit=type_hits,
        top_k_doc_id_hit=id_hits,
        reciprocal_rank_doc_type=rr_type,
        reciprocal_rank_doc_id=rr_id_val,
    )


# ---------------------------------------------------------------------------
# Wrong-case classification
# ---------------------------------------------------------------------------


def _classify_failure_mode(
    case: RetrievalComparisonCase,
    metrics: CaseRetrievalMetrics,
) -> str | None:
    """Classify why a case failed retrieval.

    Args:
        case: The original comparison case.
        metrics: The computed metrics for this case.

    Returns:
        Failure mode string, or None if the case is successful at k=10.
    """
    if metrics.top_k_doc_type_hit.get(10, False):
        return None

    expected_types = set(case.expected_doc_types)
    retrieved_types = {d.doc_type for d in case.retrieved_docs[:10]}

    if not retrieved_types & expected_types:
        return "missing_doc_type"

    return "below_top_10"


def summarize_wrong_cases(
    cases: list[RetrievalComparisonCase],
    ks: list[int] | None = None,
) -> list[WrongCaseEntry]:
    """Identify and classify retrieval failures.

    Args:
        cases: All comparison cases.
        ks: List of k values for top-k metrics.

    Returns:
        List of WrongCaseEntry for cases that failed retrieval at k=10.
    """
    if ks is None:
        ks = DEFAULT_KS

    wrong: list[WrongCaseEntry] = []

    for case in cases:
        metrics = compute_case_retrieval_metrics(case, ks)
        mode = _classify_failure_mode(case, metrics)
        if mode is None:
            continue

        expected_types = ", ".join(sorted(case.expected_doc_types))
        retrieved_summary = ", ".join(
            f"{d.doc_type}({d.doc_id})@{d.rank}"
            for d in sorted(case.retrieved_docs, key=lambda x: x.rank)[:10]
        )

        wrong.append(
            WrongCaseEntry(
                case_id=case.case_id,
                failure_mode=mode,
                details=(
                    f"Expected doc_types: [{expected_types}] | "
                    f"Retrieved: {retrieved_summary}"
                ),
                top_k_doc_type_hit=metrics.top_k_doc_type_hit,
                reciprocal_rank_doc_type=metrics.reciprocal_rank_doc_type,
            )
        )

    return wrong


# ---------------------------------------------------------------------------
# Aggregate computation
# ---------------------------------------------------------------------------


def compute_retrieval_comparison_summary(
    cases: list[RetrievalComparisonCase],
    ks: list[int] | None = None,
) -> RetrievalComparisonSummary:
    """Compute aggregate retrieval comparison metrics across all cases.

    Args:
        cases: All comparison cases.
        ks: List of k values for top-k metrics.

    Returns:
        RetrievalComparisonSummary with aggregate metrics.
    """
    if ks is None:
        ks = DEFAULT_KS

    if not cases:
        return RetrievalComparisonSummary(
            total_cases=0,
            hit_rate_doc_type={k: 0.0 for k in ks},
            per_case={},
        )

    per_case: dict[str, CaseRetrievalMetrics] = {}
    for case in cases:
        per_case[case.case_id] = compute_case_retrieval_metrics(case, ks)

    # Doc-type hit rates
    hit_rate_type: dict[int, float] = {}
    for k in ks:
        hits = [m.top_k_doc_type_hit[k] for m in per_case.values()]
        hit_rate_type[k] = compute_hit_rate_at_k(hits)

    # Doc-type MRR
    rr_types = [m.reciprocal_rank_doc_type for m in per_case.values()]
    mrr_type = compute_mrr(rr_types)

    # Doc-id hit rates (only if all cases have doc_id data)
    has_any_doc_ids = any(
        m.top_k_doc_id_hit is not None for m in per_case.values()
    )
    hit_rate_id: dict[int, float] | None = None
    mrr_id: float | None = None
    if has_any_doc_ids and per_case:
        hit_rate_id = {}
        for k in ks:
            hits = [
                m.top_k_doc_id_hit[k]
                for m in per_case.values()
                if m.top_k_doc_id_hit is not None
            ]
            hit_rate_id[k] = compute_hit_rate_at_k(hits) if hits else 0.0

        rr_ids = [
            m.reciprocal_rank_doc_id
            for m in per_case.values()
            if m.reciprocal_rank_doc_id is not None
        ]
        mrr_id = compute_mrr(rr_ids) if rr_ids else None

    wrong = summarize_wrong_cases(cases, ks)

    return RetrievalComparisonSummary(
        total_cases=len(cases),
        hit_rate_doc_type=hit_rate_type,
        hit_rate_doc_id=hit_rate_id,
        mrr_doc_type=mrr_type,
        mrr_doc_id=mrr_id,
        per_case=per_case,
        wrong_cases=wrong,
    )
