# Design: Hybrid Retrieval Ranking Diagnosis (Phase 10)

## Architecture Principles

### Trace-First, Not Tuning-First

Phase 10 is a diagnostic phase. No retrieval algorithm parameters (RRF k, keyword
weight, vector weight, HNSW ef_search) may be changed. The goal is to understand
where the ranking pipeline fails for each P0-related wrong case, using data
already captured by `RetrievalTrace`.

### Provider Identity Gate (Mandatory, From Phase 9)

Every trace report generated in Phase 10 MUST declare the embedding provider used:

| Provider | Usage in Phase 10 |
|---|---|
| FakeEmbeddingProvider (384-d) | Pipeline mechanics check only; semantic conclusions invalid |
| OpenAICompatibleProvider (1024-d) | Required for semantic ranking diagnosis |

Fake provider diagnosis MUST include a disclaimer: "Fake embeddings are deterministic
per text but carry no semantic meaning. Ranking conclusions from fake provider traces
are pipeline-mechanical only and cannot inform retrieval quality decisions."

### Immutable Baselines (From Phase 9)

Phase 7, Phase 8, and Phase 9 reports are read-only for Phase 10:
- `reports/retrieval/wrong_cases.md` (Phase 8)
- `reports/retrieval/fake_vs_real_comparison.{json,md}` (Phase 8)
- `reports/retrieval/phase9_*` (Phase 9)
- `reports/evaluation/*` (Phase 7)

Phase 10 outputs go to `reports/retrieval/phase10_*` namespaced paths.

## Existing Trace Infrastructure

### RetrievalTrace Fields (Already Available)

```python
class RetrievalTrace:
    query: str
    query_embedding: list[float]
    keyword_results: list[KeywordResult]   # chunk_id, doc_id, doc_type, score, rank
    vector_results: list[VectorResult]     # chunk_id, doc_id, doc_type, score, rank
    fused_results: list[FusedResult]       # chunk_id, doc_id, doc_type, rrf_score,
                                           # keyword_rank, keyword_contribution,
                                           # vector_rank, vector_contribution, sources
    final_evidence_ids: list[UUID]
    embedding_provider: str
    top_k: int
    rrf_k: int
    total_latency_ms: int
```

### What's Already Captured
- Per-ranker results with chunk_id, doc_id, doc_type, score, rank
- Per-ranker contribution to RRF score in FusedResult
- Which sources contributed each fused result ("keyword", "vector", or both)
- Embedding provider identity

### What's Missing for Full Diagnosis
- No per-case export that collates keyword/vector/fused for a specific chunk_id
- No P0 record → best rank mapping across cases
- No automated bottleneck classification
- No provider-aware report generation

## Data Flow

```
Phase 9 P0 Cases (16)
        │
        ▼
Export per-case RetrievalTrace
  (keyword, vector, fused, final evidence)
        │
        ▼
Cross-reference P0 record chunk_ids
  against each layer of the trace
        │
        ▼
Bottleneck Classification:
  - keyword_not_recalled: P0 record absent from keyword results entirely
  - vector_not_recalled: P0 record absent from vector results entirely
  - recalled_but_fused_low: P0 record in keyword/vector but fused rank > top_k
  - fused_top10_but_metric_still_wrong: P0 record in fused Top-10 but case still wrong
  - doc_level_label_missing: golden label only has doc_type, not doc_id
  - query_expansion_gap: query underspecified; record exists but not matched
  - empty_retrieval: both retrievers return zero results
  - provider_identity_issue: wrong provider or dimension mismatch
        │
        ▼
Phase 10 Recommendation:
  doc-level labels | query expansion | RRF tuning | reranker | limitation
```

## Bottleneck Taxonomy Design

Each P0-related wrong case is classified into exactly one primary bottleneck:

| Category | Definition | Detection Method |
|---|---|---|
| `keyword_not_recalled` | P0 record absent from keyword results entirely | chunk_id not in trace.keyword_results |
| `vector_not_recalled` | P0 record absent from vector results entirely | chunk_id not in trace.vector_results |
| `recalled_but_fused_low` | P0 record in keyword or vector, but fused rank > top_k | chunk_id in keyword/vector, fused rank > top_k |
| `fused_top10_but_metric_still_wrong` | P0 record in fused Top-10, but case still classified wrong | chunk_id in fused top_k, case still in wrong_cases |
| `doc_level_label_missing` | Cannot distinguish if right doc was retrieved because golden only has doc_type | golden.expected_relevant_doc_ids is empty |
| `query_expansion_gap` | Query underspecified; record exists and semantically matches but query terms don't trigger recall | manual inspection |
| `empty_retrieval` | Both retrievers return zero results for this query | len(keyword) == 0 and len(vector) == 0 |
| `provider_identity_issue` | Trace provider differs from expected, or dimension mismatch | trace.embedding_provider != expected |

Categories are determined programmatically where possible; `query_expansion_gap`
requires manual inspection of query text vs record content.

## Compatibility with External Retrieval Design

Azure AI Search and other enterprise hybrid search systems execute keyword and
vector retrieval in parallel, then merge via RRF. TicketPilot's architecture
mirrors this:
- `keyword_search()` → PostgreSQL FTS (ts_vector)
- `vector_search()` → pgvector HNSW (cosine similarity)
- `rrf_fuse()` → RRF with k=60

Phase 10's diagnosis is compatible with any system that exposes per-ranker
rankings before fusion. The bottleneck taxonomy is retrieval-stack-agnostic.

## Safety Constraints

- Human-in-the-loop required for risk flags (unchanged)
- No auto-send, no auto-reply (unchanged)
- No production or real customer data (unchanged)
- Secret scan must remain clean (unchanged)
- Provider identity must be declared in every report (Phase 10 addition)
- Fake provider diagnosis must carry disclaimer (Phase 10 addition)
- No baseline reports may be modified

## File Manifest (Planning Stage)

| File | Purpose | This Batch? |
|------|---------|-------------|
| `proposal.md` | Problem, goal, non-goals, scope, success criteria, risks | Created now |
| `design.md` | Architecture constraints, trace review, bottleneck taxonomy | Created now |
| `tasks.md` | Task breakdown for all 7 sub-phases | Created now |
| `specs/retrieval-evaluation/spec.md` | Bottleneck taxonomy, per-case layered trace export, recommendation report | Created now |
| `specs/retrieval-trace/spec.md` | Trace field gap analysis, provider-aware export, disclaimer requirements | Created now |
