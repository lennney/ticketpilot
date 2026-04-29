## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. This change builds the retrieval foundation: layered knowledge architecture with hybrid keyword + vector retrieval.

**Current state**: Ticket intake and risk triage vertical slice complete. No retrieval system yet.

**Constraints**:
- No reply generation yet
- No reranker integration yet (placeholder interfaces only)
- No Langfuse/Ragas yet (traces go to structured logs only)
- No Streamlit UI yet
- FAQ/Policy/Case MUST be physically separated (different tables)
- MUST support parent-child chunk retrieval
- MUST use HNSW for vector index
- MUST support hybrid retrieval (keyword + dense), NOT vector-only

## Goals / Non-Goals

**Goals:**
- Layered knowledge schema with FAQ / Policy / Case separation
- Parent-child chunking with `parent_chunk_id` linkage
- PostgreSQL full-text keyword retrieval returning top-k
- pgvector HNSW vector retrieval returning top-k
- RRF fusion combining keyword and vector rankings
- Retrieval traces capturing full pipeline state
- Seed data: 10+ FAQ, 10+ Policy, 10+ Case
- 6 retrieval golden cases for smoke testing

**Non-Goals:**
- Reply generation (handled in later vertical slice)
- Real reranker integration (placeholder interface only)
- Langfuse/Ragas integration (structured logging only)
- Streamlit UI (handled in later vertical slice)
- BM25 scoring (PostgreSQL full-text sufficient for MVP)

## Architecture Diagram

```
                                    +------------------+
                                    |   Ticket Input   |
                                    +--------+---------+
                                             |
                                             v
                              +-------------------------+
                              |   Intent Classification |
                              +--------+----------------+
                                         |
                                         v
                    +--------------------------------------+
                    |         Retrieval Pipeline           |
                    +--------------------------------------+
                    |                                      |
                    v                                      v
        +-------------------+                  +--------------------+
        | Keyword Retrieval|                  |  Vector Retrieval  |
        | (PostgreSQL FTS) |                  |   (pgvector HNSW)  |
        +--------+----------+                  +--------+-----------+
                 |                                        |
                 v                                        v
        +-------------------+                  +--------------------+
        |  Keyword Scores  |                  |   Vector Scores    |
        |  (ts_rank)       |                  |   (cosine_sim)     |
        +--------+----------+                  +--------+-----------+
                 |                                        |
                 +----------------+  +-------------------+
                                    v
                         +------------------+
                         |   RRF Fusion      |
                         |   (k=60)          |
                         +--------+-----------+
                                  |
                                  v
                         +------------------+
                         |  Fused Rankings  |
                         +--------+-----------+
                                  |
                                  v
                         +------------------+
                         | Retrieval Trace  |
                         +------------------+
```

## Data Model

### Table: `knowledge_faq`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| doc_type | VARCHAR(10) | Always 'FAQ' |
| business_domain | VARCHAR(50) | e.g., 'refund', 'return_exchange', 'account' |
| title | TEXT | FAQ title |
| content | TEXT | Full FAQ content |
| intent_tags | TEXT[] | Intent routing tags |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### Table: `knowledge_policy`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| doc_type | VARCHAR(10) | Always 'POLICY' |
| business_domain | VARCHAR(50) | e.g., 'refund', 'return_exchange', 'account' |
| policy_code | VARCHAR(20) | Policy clause number (e.g., '7.3.2') |
| title | TEXT | Policy section title |
| content | TEXT | Full policy content |
| effective_date | DATE | Policy effective date |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### Table: `knowledge_case`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| doc_type | VARCHAR(10) | Always 'CASE' |
| business_domain | VARCHAR(50) | e.g., 'refund', 'return_exchange' |
| case_id | VARCHAR(50) | Original ticket ID |
| issue_summary | TEXT | Brief issue description |
| resolution | TEXT | How the case was resolved |
| risk_level | VARCHAR(20) | 'low', 'medium', 'high' |
| compensation_amount | DECIMAL(10,2) | Compensation given (if any) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### Table: `knowledge_chunks` (all doc types)

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| doc_id | UUID | Foreign key to source document |
| doc_type | VARCHAR(10) | 'FAQ', 'POLICY', or 'CASE' |
| parent_chunk_id | UUID | FK to parent chunk (NULL for level=1) |
| chunk_level | INTEGER | 1=parent, 2=child |
| business_domain | VARCHAR(50) | Domain classification |
| risk_level | VARCHAR(20) | Risk tier (from case) or NULL |
| content | TEXT | Chunk text content |
| content_hash | VARCHAR(64) | SHA-256 for deduplication |
| embedding | VECTOR(1536) | Embedding vector (text-embedding-3-small) |
| created_at | TIMESTAMP | Creation timestamp |

### Table: `retrieval_traces`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| query | TEXT | Original query text |
| query_embedding | VECTOR(1536) | Query embedding vector |
| keyword_results | JSONB | Top-k keyword results with scores |
| vector_results | JSONB | Top-k vector results with scores |
| fused_results | JSONB | RRF fused results with final scores |
| final_evidence | JSONB | Selected evidence for reply generation |
| retrieved_doc_ids | UUID[] | All retrieved document IDs |
| retrieval_latency_ms | INTEGER | Total retrieval time |
| created_at | TIMESTAMP | Trace timestamp |

## Why Source Separation Is Critical

**FORBIDDEN: Mixing FAQ/Policy/Case into one table**

Source separation is required because:

1. **Different update frequencies**: FAQ changes often (weekly), Policy changes rarely (quarterly), Case grows continuously
2. **Different access patterns**: FAQ for routing, Policy for compliance, Case for precedent
3. **Different retention policies**: FAQ may be deprecated, Policy must be preserved, Case has privacy considerations
4. **Different metadata**: FAQ has intent_tags, Policy has policy_code, Case has risk_level and compensation

Mixing sources dilutes relevance signals and complicates trace attribution.

## Why Parent-Child Chunking Is Required

**FORBIDDEN: Only using small chunks without parent**

Parent-child chunking is required because:

1. **Context preservation**: Child chunks (100-300 tokens) are specific but lack context
2. **Relevance scoring**: Parent chunks (500-1000 tokens) provide full context for scoring
3. **Traceability**: Can trace which passage triggered the match while showing parent context
4. **Use case support**: 
   - Child: specific passage matching query
   - Parent: full document context for reply generation

Without parent linkage, small chunks lack sufficient context for evidence-grounded replies.

## Why Hybrid Retrieval (Keyword + Dense) Is Required

**FORBIDDEN: Vector-only retrieval without keyword**

Hybrid retrieval is required because:

1. **Exact matches**: Policy clause numbers ("7.3.2") require exact keyword matching
2. **Semantic matches**: paraphrased queries require vector similarity
3. **Complementary signals**: Keyword and vector rankings are not highly correlated
4. **Recall improvement**: Hybrid retrieval consistently outperforms either alone

Vector-only retrieval misses exact policy references. Keyword-only retrieval misses paraphrased queries.

## HNSW Index Configuration

```sql
-- HNSW index for vector retrieval
CREATE INDEX idx_chunks_embedding_hnsw 
ON knowledge_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- PostgreSQL full-text search index
CREATE INDEX idx_chunks_content_fts 
ON knowledge_chunks 
USING gin (to_tsvector('chinese', content));
```

Parameters:
- `m = 16`: Number of bi-directional links per node (higher = better recall, more memory)
- `ef_construction = 200`: Size of dynamic candidate list during construction (higher = better quality, slower)
- `ef = 100`: Size of dynamic candidate list during search (default, adjustable for latency/quality tradeoff)

## RRF Algorithm with k=60

Reciprocal Rank Fusion formula:

```
RRF_score(doc) = sum over rankers r: 1 / (k + rank_r(doc))
```

Where:
- `k = 60` (standard constant, reduces impact of large rank differences)
- `rank_r(doc)` is the rank position (1-indexed) from ranker `r`
- A doc ranked #1 by both retrievers: score = 1/(60+1) + 1/(60+1) = 0.03226
- A doc ranked #1 by one, #10 by other: score = 1/61 + 1/69 = 0.03077

```python
def rrf_fusion(keyword_results: list, vector_results: list, k: int = 60) -> list:
    scores = defaultdict(float)
    for rank, (doc_id, _) in enumerate(keyword_results, start=1):
        scores[doc_id] += 1 / (k + rank)
    for rank, (doc_id, _) in enumerate(vector_results, start=1):
        scores[doc_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## Embedding Model Tiers

For MVP, support three embedding tiers via provider interface:

| Tier | Model | Dimensions | Use Case |
|------|-------|------------|----------|
| fake | FakeEmbedding | 1536 | Unit tests, CI |
| small | text-embedding-3-small | 1536 | Development, quick iteration |
| quality | text-embedding-3-large | 3072 | Production evaluation |

**NOT YET: Fine-tuning embeddings on support ticket data**

Fine-tuning requires:
- Labeled retrieval data (query -> relevant document pairs)
- Evaluation harness to measure improvement
- A/B testing infrastructure

Placeholder interface now, real integration later.

## File Layout for Retrieval Module

```
src/ticketpilot/
  retrieval/
    __init__.py
    schema/
      __init__.py
      knowledge.py      # KnowledgeDocument, KnowledgeChunk Pydantic models
      retrieval.py     # RetrievalQuery, RetrievalResult, RetrievalTrace
      seeds.py         # Seed data loader
    providers/
      __init__.py
      embedding.py     # EmbeddingProvider interface + Fake/Small/Quality implementations
    db/
      __init__.py
      connection.py    # Database connection management
      keyword.py       # PostgreSQL full-text retrieval
      vector.py        # pgvector HNSW retrieval
      fusion.py        # RRF fusion logic
    pipeline.py          # HybridRetrievalPipeline
    traces.py             # RetrievalTraceLogger
data/
  knowledge/
    faq_seed.json
    policy_seed.json
    case_seed.json
tests/
  unit/
    test_retrieval.py     # Golden case smoke tests
```

## Risks / Trade-offs

[Risk] PostgreSQL full-text vs. BM25
-> PostgreSQL FTS is sufficient for MVP; BM25 requires additional library

[Risk] HNSW memory usage for large document collections
-> Monitor memory; can reduce `m` parameter or switch to IVFFlat for billions of vectors

[Risk] Embedding drift over time
-> Placeholder for re-embedding pipeline; not implemented yet

[Risk] Parent-child chunking increases storage 2-3x
-> Acceptable for MVP scale (thousands of documents)

## Migration Plan

1. Create `src/ticketpilot/retrieval/` structure with schema definitions
2. Implement embedding provider interface with fake/small/quality tiers
3. Create database schema migrations for knowledge tables and chunks
4. Implement PostgreSQL keyword retrieval
5. Implement pgvector HNSW retrieval
6. Implement RRF fusion
7. Create retrieval pipeline combining all retrievers
8. Implement retrieval trace logging
9. Add seed data: 10+ FAQ, 10+ Policy, 10+ Case
10. Write golden case smoke tests
11. Run quality gate and update docs/changelog.md

**Rollback**: Delete `src/ticketpilot/retrieval/`, drop knowledge tables, revert changelog.

## Open Questions

- Exact chunk size boundaries (100-300 for child, 500-1000 for parent) need validation
- Whether to store embeddings at chunk time or generate on-demand
- How to handle multilingual queries (Chinese + English policy terms)
- Whether to index chunks separately or only parent chunks for vector search

