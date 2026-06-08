# Retrieval Architecture

## Overview

The retrieval engine provides hybrid keyword + vector search over a Chinese knowledge base. It is the core of TicketPilot's knowledge-grounded pipeline, enabling evidence-backed customer support replies. The retrieval operates as Stage 4 of the pipeline.

**Source modules:** `src/ticketpilot/retrieval/`

## Source Separation: FAQ / Policy / Case

The knowledge base uses a **two-layer source architecture**:

### Layer 1: Source Tables (type-specific storage)

Three physically separate PostgreSQL tables, each with columns specific to the document type:

| Table | Document Type | Type-Specific Columns |
|-------|--------------|----------------------|
| `knowledge_faq` | FAQ | `intent_tags` (text[]), `business_domain` |
| `knowledge_policy` | Policy | `policy_code`, `effective_date`, `business_domain` |
| `knowledge_case` | Case | `case_outcome`, `resolution_summary`, `risk_level`, `compensation_amount`, `business_domain` |

All source tables share: `id` (UUID PK), `title`, `created_at`, `updated_at`.

### Layer 2: Chunk Table (unified retrieval)

A single `knowledge_chunks` table stores all chunked content across all document types, with foreign key columns to source tables:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Chunk identifier |
| `doc_id` | UUID | FK to source document |
| `doc_type` | text | "faq", "policy", or "case" |
| `source_table` | text | Source table name |
| `source_id` | UUID | FK to source table row |
| `content` | text | Chunk text content |
| `embedding` | vector(384) | Embedding vector (fake for MVP) |
| `parent_chunk_id` | UUID (nullable) | FK to parent chunk (for parent-child linking) |
| `chunk_level` | int | 1 (parent) or 2 (child) |

**Why two layers:** Source tables satisfy the spec requirement for physical separation (different update frequencies, access patterns, retention policies). The unified chunks table enables single-query retrieval without UNION operations.

## Knowledge Chunks

### Parent-Child Chunking

Each document is split into two chunk levels:

- **Level 1 (parent)**: 500-1000 tokens. Provides full context for reply generation.
- **Level 2 (child)**: 100-300 tokens. Provides precise passage matching for retrieval.

Child chunks link to parent chunks via `parent_chunk_id`, enabling traceability from a matched passage to its broader context.

**Source:** `src/ticketpilot/retrieval/chunker.py`

### Seed Data

The current knowledge base contains synthetic seed data (not real enterprise data):
- 12 FAQ documents
- 12 Policy documents
- 12 Case documents

These 36 documents produce approximately 50 chunks after parent-child splitting. The seed data is sufficient for demo and integration testing but is not representative of real-world scale or content.

## Hybrid Retrieval

The retrieval pipeline runs a two-stage process: keyword search + vector search, then fuses results with RRF.

### Stage 1: Keyword Search (PostgreSQL FTS)

**Source:** `src/ticketpilot/retrieval/keyword_search.py`

| Parameter | Value |
|-----------|-------|
| FTS configuration | `simple` (not `chinese`) |
| Index | GIN on `to_tsvector('simple', content)` |
| Ranking | `ts_rank` with default normalization |
| Fallback | LIKE-based match on 8 Chinese business terms when FTS returns zero results |

**Important note on FTS config:** The `simple` configuration tokenizes on whitespace. It does not perform Chinese word segmentation. For content consisting primarily of Chinese text without spaces, FTS may produce few or no results. The 8-term Chinese business keyword LIKE fallback compensates for this limitation.

### Stage 2: Vector Search (pgvector HNSW)

**Source:** `src/ticketpilot/retrieval/vector_search.py`

| Parameter | Value |
|-----------|-------|
| Index type | HNSW (Hierarchical Navigable Small World) |
| m (max connections per node) | 16 |
| ef_construction | 200 |
| ef_search | 100 |
| Distance operator | `<=>` (cosine distance) |
| Score formula | `1 - (embedding <=> query_vector)` |

### Stage 3: RRF Fusion

**Source:** `src/ticketpilot/retrieval/rrf.py`

**RRF formula:** `score(doc) = sum(1 / (k + rank(ranker, doc)))` for each ranker

| Parameter | Value |
|-----------|-------|
| k | 60 |
| Per-ranker tracking | Each FusedResult records keyword_rank, keyword_contribution, vector_rank, vector_contribution |

RRF is score-agnostic — it combines rank positions rather than raw scores, which is essential since keyword FTS scores and vector cosine similarity are not directly comparable. The `k=60` constant reduces the impact of large rank differences between rankers.

### Retrieval Pipeline Orchestration

**Source:** `src/ticketpilot/retrieval/pipeline.py`

The `hybrid_retrieval()` function orchestrates:
1. Run keyword search (`keyword_search_db`)
2. Run vector search (`vector_search_db`)
3. Fuse results (`rrf_fusion`)
4. Apply optional doc_type filter
5. Return `RetrievalTrace` with full fused results

### Evidence Mapping

**Source:** `src/ticketpilot/retrieval/evidence_mapper.py`

After fusion, `map_fused_to_evidence()` converts `FusedResult` objects to `EvidenceCandidate` objects (the boundary type used by the pipeline). This mapping:
- Drops retrieval-internal fields (keyword_rank, vector_rank, per-ranker contributions)
- Adds `source_table` from the chunk's source table reference
- Preserves `rank` for downstream ordering

## Fake Embedding Limitation

**Critical constraint:** The `FakeEmbeddingProvider` generates deterministic pseudo-random vectors using SHA-256 hashes seeded random number generation. These vectors have **no semantic meaning**.

```
FakeEmbeddingProvider:
  - Dimension: 384
  - Algorithm: SHA-256(text) -> seed -> random.Random(seed) -> 384 floats in [-1, 1]
  - Deterministic: same text always produces the same vector
  - Status: PIPELINE VERIFICATION ONLY
```

What the fake embedding provider can verify:
- Embedding generation and storage works
- HNSW indexing works (cosine distance computation, index creation)
- Vector search returns results (sorted by distance)
- RRF fusion works with vector ranking
- Full retrieval pipeline integration (query -> embedding -> search -> fusion -> output)

What the fake embedding provider **cannot** provide:
- Semantic retrieval quality
- Meaningful cosine similarity scores
- Meaningful ranking of results by relevance
- Any real-world retrieval precision or recall

## Hybrid Reranking (Post-RRF)

After RRF fusion, an optional **Hybrid Reranker** applies multi-signal weighted fusion
to improve Top-K ranking quality. This replaces the previous simple embedding tiebreaker.

**Source:** `src/ticketpilot/retrieval/hybrid_reranker.py`

### Signals

| Signal | Default Weight | Description |
|--------|---------------|-------------|
| RRF score | 0.40 | Min-max normalized RRF fusion score |
| Embedding similarity | 0.25 | Cosine similarity (auto-disabled with FakeEmbedding) |
| Intent metadata boost | 0.20 | Intent → doc_type matching (e.g., refund→policy +0.15) |
| Content quality | 0.15 | Length appropriateness + keyword density |

When FakeEmbeddingProvider is detected, the embedding signal weight is redistributed
proportionally among the other 3 signals (so weights always sum to 1.0).

### Configuration

Weights and parameters are configurable via `config/reranker.yaml`:

```yaml
weights:
  rrf_score: 0.40
  embedding_similarity: 0.25
  intent_metadata_boost: 0.20
  content_quality: 0.15
```

**Source:** `src/ticketpilot/retrieval/reranker_config.py`

## Multi-Query Expansion

An optional **MultiQueryExpander** generates query variants using LLM to improve recall.
When enabled, the original query + N variants are each run through the retrieval pipeline
independently, then merged before hybrid reranking.

**Source:** `src/ticketpilot/retrieval/query_expander.py`

### Merge Strategies

Results from multiple query variants are merged using:

- **sum_score** (default): RRF scores summed per chunk_id — docs found by multiple
  variants get higher scores (multi-path validation)
- **max_score**: Keep highest RRF score per chunk_id
- **rrf_again**: Apply second-level RRF across variant rankings

**Source:** `src/ticketpilot/retrieval/result_merger.py`

### Pipeline Integration

```
Query → (optional) MultiQueryExpander → N variants
      → per-variant: keyword + vector + RRF
      → merge (sum_score)
      → HybridReranker (4-signal fusion)
      → Top-K output + RetrievalTrace
```

Both features are backward-compatible: `enable_query_expansion=False` by default,
and `intent=None` disables intent boost. All new fields in RetrievalTrace are Optional.

## Deferred Items

The following retrieval refinements are explicitly deferred:

- **Realistic enterprise data pack** — Current 36-document seed set is synthetic. A real data pack with actual FAQ, policy, and case documents is needed.
- **SourceRouter implementation** — Intent-to-source routing (e.g., refund tickets search only FAQ + Policy) was designed but not implemented.
- **Persistent retrieval traces** — `RetrievalTrace` is in-memory only. The `retrieval_traces` DB table migration is deferred.
- **BM25 or alternative keyword retrieval** — PostgreSQL FTS is sufficient for MVP. BM25 may improve keyword ranking.
- **Embedding fine-tuning** — No support ticket data available for fine-tuning.
- **Evidence scoring threshold tuning** — RRF scores have no absolute meaning; threshold tuning deferred until evaluation data exists.
- **Cross-encoder reranker** — Would require sentence-transformers dependency; deferred in favor of lightweight multi-signal fusion.
