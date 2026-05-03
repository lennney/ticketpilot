# Retrieval Architecture Design

> **DEPRECATED (2026-05-02):** This document contains values and designs that do not
> match the current implementation. The following specific claims are incorrect:
> - Fake embedding dimension: doc says 128, code uses **384**
> - FTS config: doc says `chinese`, code uses **`simple`**
> - HNSW ef_construction: doc says 64, code uses **200**
> - SourceRouter: documented as implemented, actually **deferred**
>
> For the authoritative implementation reference, see `docs/technical_decisions.md`
> (Retrieval Architecture section). For the actual code, see `src/ticketpilot/retrieval/`.

## Decision Summary

TicketPilot MVP uses hybrid retrieval combining PostgreSQL full-text search (keyword) with pgvector HNSW (dense vectors), fused via Reciprocal Rank Fusion (RRF). This approach balances query latency, recall quality, and operational simplicity within the PostgreSQL + pgvector stack.

**Key Decisions:**
- HNSW as primary vector index (no training, fast queries, pgvector-native)
- IVFFlat available as alternative for sorted/filtered queries
- IVF_PQ explicitly excluded from MVP (PostgreSQL limitation, added complexity)
- Three-tier embedding strategy: fake (tests), fast/small (dev), quality/large (demo)
- Source separation preserved: FAQ, Policy, Case
- RRF fusion as the merging strategy; rerank interface reserved for future

---

## Architecture Overview

                                    Ticket Input
                                         |
                                    Normalized
                                         |
                          +--------------+--------------+
                          |              |              |
                    [Keyword Path]  [Dense Path]   [Future: Rerank]
                          |              |              |
                    PostgreSQL       pgvector          (Cohere/Other
                    Full-Text         HNSW               API)
                          |              |
                          |   +-----+----+
                          |   |           |
                          |  FAQ      Policy
                          |  Policy    Case
                          |   |           |
                          |   +-----+-----+
                          |         |
                          |      [RRF Fusion]
                          |         |
                          |   [Ranked Results]
                          |         |
                          +----+----+
                               |
                          [Evidence-grounded
                           reply draft]

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Normalizer | Clean ticket text, extract entities | Python regex |
| Keyword Retriever | BM25-style full-text search | PostgreSQL ts_query |
| Dense Retriever | ANN search on embeddings | pgvector HNSW |
| Source Router | Direct query to FAQ/Policy/Case | Routing logic |
| Fusion Engine | Merge ranked lists via RRF | Python |
| Reranker (future) | Cross-encoder refinement | External API |

---

## Index Options Analysis

### Comparison Matrix

| Index Type | Build Time | Query Speed | Memory | Recall | PostgreSQL Support |
|------------|-----------|-------------|--------|--------|-------------------|
| Brute Force | N/A | O(n) | O(n) | 100% | Always |
| IVFFlat | O(n log n) | O(log n) | O(n) | High | Native |
| HNSW | O(n log n) | O(log n) | O(n log n) | Very High | Native |
| IVF_PQ | O(n log n) | O(log n) | O(n/k) | Medium-High | Not Native |

### Why HNSW for MVP

1. **No training required**: Unlike IVF_PQ, HNSW builds indices immediately without sample training data
2. **pgvector-native**: Full support in PostgreSQL extension, no external services
3. **Fast queries**: O(log n) search with excellent recall (typically 95-99% on standard benchmarks)
4. **Mature implementation**: pgvector HNSW is well-tested in production environments
5. **Simple operational model**: Single PostgreSQL instance, no additional services

**Trade-off**: HNSW consumes more memory than IVFFlat or IVF_PQ for equivalent corpus sizes. For MVP with <1M vectors, this is acceptable.

### Why Not IVF_PQ for MVP

1. **PostgreSQL limitation**: pgvector does not support IVF_PQ; would require external vector DB (FAISS/Milvus)
2. **Added complexity**: External service introduces deployment, monitoring, and consistency challenges
3. **Training overhead**: IVF_PQ requires training data to build codebook
4. **Diminishing returns at MVP scale**: Memory savings only matter at 10M+ vectors

**When IVF_PQ may be reconsidered**:
- Corpus grows beyond 10M vectors
- Custom infrastructure (not managed PostgreSQL)
- Memory costs become prohibitive
- Team has operational expertise with FAISS/Milvus

### When IVFFlat May Be Considered

IVFFlat partitions vectors into lists, making it efficient for:
- Queries with pre-filtering (exact match on metadata first)
- Sorted result sets where approximate recall is acceptable
- Batch queries on sorted/indexed attributes

**Trade-off**: IVFFlat requires SET maintenance_work_mem tuning and has slightly lower recall than HNSW for unfiltered queries.

---

## Embedding Model Tiers

### Tier 1: Fake Embedding (Tests)

Model: fake
Dimension: 128
Use case: Unit tests, CI/CD
Characteristics:
  - Deterministic output
  - No API calls
  - Reproducible results
  - Fast execution

Implementation: Return fixed random vectors seeded by input hash.

### Tier 2: Fast/Small Embedding (Local Dev)

Model: text2vec-base-multilingual (paraphrase-multilingual-MiniLM-L12-v2)
Dimension: 384
Use case: Local development, rapid iteration
Characteristics:
  - CPU-friendly inference
  - Good multilingual support (Chinese, English)
  - Fast (< 50ms per query)
  - 137MB model size

**Rationale**: This model balances speed and quality for development. It handles Chinese text adequately while remaining fast enough for interactive development.

### Tier 3: Quality/Large Embedding (Demo/Quality Mode)

Model: text2vec-large-chinese (shibing624/text2vec-base-chinese)
Alternative: moka-ai/m3e-base (for multilingual)
Dimension: 768
Use case: Demo, evaluation, production-like testing
Characteristics:
  - Superior Chinese semantic understanding
  - Stronger multilingual handling
  - Slower inference (100-200ms per query)
  - Larger model size

**Rationale**: Chinese-specific or multilingual models provide better semantic matching for e-commerce support tickets. M3E-base offers excellent multilingual performance if international expansion is planned.

### Provider Abstraction

```python
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass

    @property
    def dimension(self) -> int:
        pass

    @property
    def model_name(self) -> str:
        pass
```

---

## Source Separation

### Why Preserve Separation

1. **Auditability**: Track which source type contributed to each answer
2. **Quality signals**: FAQ answers are authoritative; Case answers are anecdotal
3. **Conflict resolution**: Policy overrides FAQ; Case must cite Policy
4. **Scoped recall**: Different intent classes may query different sources

### Source Definitions

| Source | Content Type | Update Frequency | Trust Level |
|--------|-------------|-------------------|--------------|
| FAQ | Frequently asked questions with standard answers | Low | High |
| Policy | Company rules, refund policies, service agreements | Very Low | Highest |
| Case | Historical resolved tickets with solutions | Medium | Medium |

### Routing Logic

```python
class SourceRouter:
    ROUTE_MAP = {
        IntentClass.REFUND: ["faq", "policy"],
        IntentClass.RETURN_EXCHANGE: ["faq", "policy"],
        IntentClass.COMPLAINT: ["case", "policy"],
        IntentClass.LOGISTICS: ["faq", "case"],
        IntentClass.ACCOUNT_ISSUE: ["policy"],
        IntentClass.TECHNICAL_ISSUE: ["faq", "case"],
        IntentClass.PRODUCT_CONSULTING: ["faq"],
        IntentClass.OTHER: ["faq", "case", "policy"],
    }
```

---

## Hybrid Retrieval Design

### Retrieval Pipeline

```
1. User Query (ticket text)
       |
2. Normalize Query
       |
3. Parallel Execution:
   [Keyword Path]          [Dense Path]
   PostgreSQL ts_query     pgvector HNSW
   rank by ts_rank         rank by cosine_distance
       |                         |
       +----------+--------------+
                  |
            [RRF Fusion]
            k = 60 (standard)
                  |
            [Merged Ranked List]
                  |
         [Future: Rerank]
                  |
         [Final Evidence List]
```

### Keyword Path (PostgreSQL Full-Text)

```sql
SELECT id, source_type, content,
    ts_rank(to_tsvector(chinese, content), query) AS rank
FROM knowledge_base
WHERE to_tsvector(chinese, content) @@ query
ORDER BY rank DESC LIMIT @top_k;
```

**Configuration**:
- Text search config: chinese (or simple as fallback)
- Ranking: ts_rank normalized to [0, 1]
- Stemming: Enabled for Chinese via zhparse or character-based analysis

### Dense Path (pgvector HNSW)

```sql
SELECT id, source_type, content,
    1 - (embedding <=> @query_embedding) AS similarity
FROM knowledge_base
WHERE source_type = ANY(@sources)
ORDER BY embedding <=> @query_embedding
LIMIT @top_k;
```

**Index Creation**:
```sql
CREATE INDEX ON knowledge_base USING hnsw (embedding vector_cosine_ops);
```

**HNSW Parameters**:
- m: 16 (bi-directional links per node)
- ef_construction: 64 (search width during build)

### RRF Fusion Algorithm

```python
def reciprocal_rank_fusion(result_lists, k=60):
    scores = {}
    for result_list in result_lists:
        for rank, result in enumerate(result_list, start=1):
            doc_id = result.doc_id
            rrf_score = 1 / (k + rank)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]
```

**RRF Properties**:
- k=60 is standard; k=0 equals Borda count
- k=inf equals minimum rank
- Documents not in a list get 0 contribution

### Rerank Interface (Future Extension)

```python
class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[RetrievalResult], top_k: int = 10) -> list[RetrievalResult]:
        pass
```

---

## File Layout for Retrieval Module

```
src/ticketpilot/retrieval/
    __init__.py
    embeddings/
        __init__.py
        base.py          # EmbeddingProvider protocol
        fake.py          # FakeEmbeddingProvider for tests
        small.py         # SmallEmbeddingProvider (dev)
        large.py         # LargeEmbeddingProvider (quality)
    router.py            # SourceRouter (FAQ/Policy/Case)
    keyword.py           # PostgreSQL full-text retrieval
    dense.py             # pgvector HNSW retrieval
    fusion.py            # RRF fusion implementation
    reranker.py          # Reranker interface (future)
    pipeline.py          # Hybrid retrieval pipeline

tests/
    unit/
        test_retrieval/
            test_embeddings.py
            test_router.py
            test_fusion.py
            test_pipeline.py
        test_intake_risk_triage.py

docs/
    retrieval_design.md       # This document
    retrieval_spec.md         # OpenSpec draft
    technical_decisions.md   # Updated with retrieval decisions
```

---

## Acceptance Criteria

### Functional Requirements

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-1 | System returns results from FAQ source | Query routed to FAQ returns FAQ content |
| AC-2 | System returns results from Policy source | Query routed to Policy returns Policy content |
| AC-3 | System returns results from Case source | Query routed to Case returns Case content |
| AC-4 | Keyword path returns relevant documents | Query Chinese refund terms returns refund-related FAQ |
| AC-5 | Dense path returns semantically similar documents | Query embedding matches relevant content |
| AC-6 | RRF fusion merges results correctly | Same doc in both paths appears in merged list |
| AC-7 | Results are ranked by combined score | Final ordering reflects RRF scores |
| AC-8 | Embedding provider abstraction works | Switching providers does not break retrieval |
| AC-9 | Source routing respects intent classification | Complaint intent routes to Case + Policy |
| AC-10 | Top-k limit is respected | Requesting top=5 returns at most 5 results |

### Non-Functional Requirements

| ID | Criterion | Target |
|----|-----------|--------|
| NF-1 | Query latency (keyword only) | < 50ms at 10K documents |
| NF-2 | Query latency (dense only) | < 100ms at 10K vectors |
| NF-3 | Query latency (hybrid) | < 200ms at 10K documents |
| NF-4 | Recall (HNSW) | > 95% vs brute force |
| NF-5 | Embedding dimension (fake) | 128 |
| NF-6 | Embedding dimension (small) | 384 |
| NF-7 | Embedding dimension (quality) | 768 |
| NF-8 | RRF k parameter | 60 (configurable) |

---

## Risks and Trade-offs

### Risk 1: HNSW Memory Usage

**Description**: HNSW indices consume more memory than IVF alternatives. At scale, this could become problematic.

**Probability**: Low for MVP (corpus < 1M vectors)
**Impact**: High if it occurs

**Mitigation**:
- Monitor memory usage during evaluation
- Plan for IVFFlat switch if memory pressure detected
- Consider IVF_PQ with external FAISS if corpus exceeds 10M

### Risk 2: Chinese Full-Text Search Quality

**Description**: PostgreSQL Chinese stemming is less mature than English. Results may be suboptimal.

**Probability**: Medium
**Impact**: Medium

**Mitigation**:
- Use zhparse for Chinese tokenization if available
- Fallback to simple config with character n-grams
- Supplement with dense retrieval to compensate

### Risk 3: Embedding Model Selection

**Description**: Current model choices may not optimally serve all intent classes.

**Probability**: Medium
**Impact**: Medium

**Mitigation**:
- Run evaluation on representative corpus
- A/B test small vs large models for each intent class
- Preserve abstraction to swap models without changing retrieval logic

### Risk 4: RRF Parameter Sensitivity

**Description**: k=60 may not be optimal for all query types.

**Probability**: Low
**Impact**: Low

**Mitigation**:
- Make k configurable via environment variable
- Log k values used for future tuning
- Consider query-type-specific k values in future

### Risk 5: Source Conflict Resolution

**Description**: FAQ, Policy, and Case may provide conflicting guidance.

**Probability**: High (real-world knowledge bases always have conflicts)
**Impact**: Medium

**Mitigation**:
- Establish priority rules: Policy > FAQ > Case
- Surface all sources to human reviewer
- Log conflicts for knowledge base maintenance

---

## Implementation Notes

### Database Schema (PostgreSQL)

```sql
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN (faq, policy, case)),
    intent_class TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON knowledge_base USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX ON knowledge_base USING gin (to_tsvector(chinese, title ||   || content));
CREATE INDEX ON knowledge_base (source_type);
```

### Environment Variables

```bash
EMBEDDING_PROVIDER=fake|small|quality
EMBEDDING_DIMENSION=128|384|768
RRF_K=60
DATABASE_URL=postgresql://user:pass@localhost:5432/ticketpilot
RERANKER_API_KEY=
```

### Dependencies

```toml
dependencies = [
    "psycopg2-binary>=2.9.9",
    "pgvector>=0.2.3",
    "sentence-transformers>=2.2.0",
    "scikit-learn>=1.3.0",
]
```

---

## Future Extensions

1. **Cross-encoder Reranking**: Integrate Cohere or local CrossEncoder for refined ranking
2. **Query Expansion**: Use LLM to expand queries with synonyms before retrieval
3. **Self-Query Retrieval**: Parse user query for metadata filters (date, category)
4. **Knowledge Graph Augmentation**: Link FAQ entries to Policy sections
5. **Feedback Loop**: Use human review signals to improve retrieval weights
6. **IVF_PQ Migration**: Move to FAISS/Milvus if corpus exceeds 10M vectors
