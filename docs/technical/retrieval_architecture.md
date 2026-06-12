# Retrieval Architecture

> **Last updated:** 2026-06-11
> **Changes:** DashScope real embeddings + jieba FTS segmentation + seed data expansion

## Overview

The retrieval engine provides hybrid keyword + vector search over a Chinese knowledge base. It is the core of TicketPilot's knowledge-grounded pipeline, enabling evidence-backed customer support replies.

**Source modules:** `src/ticketpilot/retrieval/`

### Pipeline Flow

```
Ticket Text
    ↓
build_retrieval_query()      ← Query builder (text + intent/risk terms)
    ↓
hybrid_retrieval()
    ├── keyword_search()      ← PostgreSQL FTS (simple config) + LIKE fallback
    │   └── jieba分词         ← Chinese word segmentation (since 2026-06-11)
    ├── vector_search()       ← pgvector HNSW (DashScope text-embedding-v3)
    │   └── 1024-dim cosine   ← Real semantic embeddings (since 2026-06-11)
    ├── RRF fusion            ← Reciprocal Rank Fusion (k=60)
    └── HybridReranker        ← 4-signal weighted reranking
    ↓
map_fused_to_evidence()      ← FusedResult → EvidenceCandidate
    ↓
Evidence Candidates          ← Input to drafting stage
```

## Source Separation: FAQ / Policy / Case

The knowledge base uses a **two-layer source architecture**:

### Layer 1: Source Tables (type-specific storage)

Three physically separate PostgreSQL tables:

| Table | Document Type | Type-Specific Columns |
|-------|--------------|----------------------|
| `knowledge_faq` | FAQ | `intent_tags` (text[]), `business_domain` |
| `knowledge_policy` | Policy | `policy_code`, `effective_date`, `business_domain` |
| `knowledge_case` | Case | `case_outcome`, `resolution_summary`, `risk_level`, `compensation_amount`, `business_domain` |

All source tables share: `id` (UUID PK), `title`, `created_at`, `updated_at`.

### Layer 2: Chunk Table (unified retrieval)

A single `knowledge_chunks` table stores all chunked content across all document types:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Chunk identifier |
| `doc_id` | UUID | FK to source document |
| `doc_type` | text | "faq", "policy", or "case" |
| `source_table` | text | Source table name |
| `source_id` | UUID | FK to source table row |
| `content` | text | Chunk text content |
| `embedding` | vector(1024) | DashScope text-embedding-v3 |
| `parent_chunk_id` | UUID (nullable) | FK to parent chunk |
| `chunk_level` | int | 1 (parent) or 2 (child) |

**Why two layers:** Source tables satisfy spec requirements for physical separation (different update frequencies, access patterns, retention policies). The unified chunks table enables single-query retrieval without UNION operations.

### Current Seed Data (2026-06-11)

```
Knowledge chunks: 1,505 total
  ├── FAQ:    619
  ├── POLICY: 463
  └── CASE:   423
```

All chunks have DashScope text-embedding-v3 (1024-dim) embeddings.

## Hybrid Retrieval

### Stage 1: Keyword Search (PostgreSQL FTS + LIKE)

**Source:** `src/ticketpilot/retrieval/keyword_search.py`

| Parameter | Value |
|-----------|-------|
| FTS configuration | `simple` (not `chinese`) |
| Index | GIN on `to_tsvector('simple', content)` |
| Ranking | `ts_rank_cd` (cover density, normalization 32) |
| **Chinese segmentation** | **jieba** (since 2026-06-11) |
| LIKE fallback | 30 Chinese business terms |
| **% escaping** | Escaped for psycopg3 (since 2026-06-11) |

**Chinese FTS fix (2026-06-11):** PostgreSQL's `simple` config treats each CJK character as an individual token. Without segmentation, a query like "我买的手机充电器坏了" becomes a 10-character AND (`我 & 买 & 的 & 手 & 机 & 充 & 电 & 器 & 坏 & 了`) that matches almost nothing. 

Solution: `_segment_chinese_terms()` uses **jieba** word segmentation to break Chinese text into meaningful words, then filters single-character stopwords (42 common chars like "的", "了", "吗"). The same query now produces:
```
手机 | 充电器 | 坏了        ← OR of 2-3 char groups
```

**LIKE fallback:** When FTS scores are below `FTS_MIN_SCORE_THRESHOLD` (0.1), the system checks for strong business terms (30 terms like "退款", "投诉", "清关") and runs LIKE-based search. Results from both sources are merged.

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
| Embedding provider | **DashScope text-embedding-v3** (1024-dim) |

**Embedding provider history:**
- **MVP (pre-2026-06-11):** `FakeEmbeddingProvider` — SHA-256 hash seeded random vectors. **Semantically meaningless.**
- **Current (2026-06-11+):** `OpenAICompatibleEmbeddingProvider` → DashScope text-embedding-v3. **Real Chinese semantic embeddings.**

**Configuration** (`.env.local`):
```bash
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=<dashscope_api_key>
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIM=1024
```

The reranker auto-detects real embeddings via `_is_real_embedding_provider()`:
- Fake → `embedding_similarity` signal weight redistributed to other signals
- Real → embedding similarity contributes to ranking

### Stage 3: RRF Fusion

**Source:** `src/ticketpilot/retrieval/rrf.py`

**RRF formula:** `score(doc) = sum(1 / (k + rank(ranker, doc)))` for each ranker

| Parameter | Value |
|-----------|-------|
| k | 60 |
| Per-ranker tracking | Each FusedResult records keyword_rank, vector_rank, per-ranker contributions |

RRF is score-agnostic — it combines rank positions rather than raw scores. With real embeddings, the vector ranking now contributes **meaningful** semantic relevance alongside keyword matching.

### Stage 4: Hybrid Reranker (Post-RRF)

**Source:** `src/ticketpilot/retrieval/hybrid_reranker.py`

Four signals with configurable weights (`config/reranker.yaml`):

| Signal | Default Weight | Active with Fake Embed? | Active with Real Embed? |
|--------|---------------|----------------------|----------------------|
| RRF score | 0.40 | ✅ | ✅ |
| Embedding similarity | 0.25 | ❌ (redistributed) | ✅ |
| Intent metadata boost | 0.20 | ✅ | ✅ |
| Content quality | 0.15 | ✅ | ✅ |

## Query Building

**Source:** `src/ticketpilot/retrieval/query_builder.py`

Builds a retrieval query from ticket state:

```python
# Input: ticket text + intent + risk flags
build_retrieval_query("我买的手机充电器坏了", IntentClass.PRODUCT_CONSULTING, {COMPENSATION_RISK})

# Output: concatenated query with intent/risk terms
→ "我买的手机充电器坏了 产品 咨询 规格 功能 赔偿 赔付 金额"
```

The appended terms (from `_INTENT_TERMS` and `_RISK_TERMS`) compensate for the keyword search limitations by injecting known domain vocabulary. These are then segmented by jieba in the FTS stage.

## Evidence Mapping

**Source:** `src/ticketpilot/retrieval/evidence_mapper.py`

After fusion, `map_fused_to_evidence()` converts `FusedResult` → `EvidenceCandidate`:
- Drops retrieval-internal fields (keyword_rank, vector_rank, RRF details)
- Adds `source_table` from chunk's source table reference
- Preserves `rank` for downstream ordering

## Multi-Query Expansion (Optional)

An optional `MultiQueryExpander` generates LLM-based query variants to improve recall. When enabled, N variants run independently, then merged via sum_score strategy.

**Source:** `src/ticketpilot/retrieval/query_expander.py`

Enabled via `enable_query_expansion=True` in `retrieve_evidence()` call.

## Key Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-11 | DashScope text-embedding-v3 | Best Chinese embedding quality, 1024-dim matches existing schema, free tier available |
| 2026-06-11 | jieba FTS segmentation | Without word segmentation, Chinese FTS recall was near zero |
| 2026-06-11 | % escaping in FTS | psycopg3 treats bare `%` as placeholder → SQL error |
| 2026-06-10 | HybridReranker replaces simple embedding tiebreaker | Multi-signal fusion gives better ranking than single-signal |

## Re-seeding Process

To regenerate knowledge chunk embeddings with a different provider:

```python
from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks
from ticketpilot.retrieval.embedding_config import load_embedding_config_from_env
from ticketpilot.retrieval.providers import create_embedding_provider

config = load_embedding_config_from_env()
provider = create_embedding_provider(config)
result = seed_knowledge_chunks(
    embedding_provider=provider,
    clear_existing=True,  # DANGER: deletes all existing chunks
)
print(result)
```

After re-seeding, the HNSW index is automatically rebuilt by PostgreSQL (the existing index definition survives because dimension matches).
