# RAG Retrieval Specification

## Overview

This spec defines the retrieval system for TicketPilot, a Chinese customer support ticket triage and evidence-grounded reply Copilot.

**Scope**: Hybrid retrieval combining PostgreSQL full-text search (keyword) with pgvector HNSW (dense vectors), fused via Reciprocal Rank Fusion (RRF).

**Out of Scope**: Cross-encoder reranking (future extension), external vector databases (FAISS/Milvus for IVF_PQ).

## Functional Requirements

### FR-1: Hybrid Retrieval Pipeline
The system MUST support parallel keyword and dense retrieval paths that are merged via RRF.

### FR-2: Source Separation
The system MUST route queries to appropriate knowledge sources (FAQ, Policy, Case) based on intent classification.

### FR-3: Embedding Provider Abstraction
The system MUST support swappable embedding providers without changing retrieval logic.

### FR-4: Top-k Limiting
The system MUST respect top_k parameters and return at most top_k results.

### FR-5: RRF Fusion
The system MUST fuse results from multiple retrieval paths using Reciprocal Rank Fusion with configurable k parameter.

### FR-6: Knowledge Base Schema
The system MUST store knowledge base entries with id, source_type, title, content, and embedding fields.

### FR-7: HNSW Index
The system MUST create and use pgvector HNSW index for dense retrieval.

### FR-8: Full-Text Search Index
The system MUST create and use PostgreSQL GIN index for full-text search.

## Non-Functional Requirements

### NFR-1: Query Latency (Keyword Only)
Keyword-only queries MUST complete in < 50ms for a knowledge base of 10,000 documents.

### NFR-2: Query Latency (Dense Only)
Dense-only queries MUST complete in < 100ms for a knowledge base of 10,000 vectors.

### NFR-3: Query Latency (Hybrid)
Hybrid queries (keyword + dense + fusion) MUST complete in < 200ms for a knowledge base of 10,000 documents.

### NFR-4: HNSW Recall
HNSW ANN search MUST achieve > 95% recall compared to brute-force search.

### NFR-5: Embedding Dimensions
Embedding dimensions MUST be 128 (fake), 384 (small), or 768 (quality) depending on provider.

### NFR-6: RRF Parameter
RRF k parameter MUST be configurable with default value of 60.

## Interface Definitions

### Data Structures

```python
class RetrievalResult:
    doc_id: str
    source_type: Literal["faq", "policy", "case"]
    title: str
    content: str
    score: float

class RetrievalQuery:
    text: str              # Query text
    intent: IntentClass    # From classification
    sources: list[str]     # ["faq", "policy", "case"]
    top_k: int = 10        # Max results per path
    embedding_provider: str = "small"  # fake|small|quality

class RetrievalResponse:
    results: list[RetrievalResult]
    query_time_ms: float
    keyword_results_count: int
    dense_results_count: int
```

### Embedding Provider Interface

```python
class EmbeddingProvider:
    @property
    def dimension(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### Retrieval Pipeline Interface

```python
class RetrievalPipeline:
    def retrieve(self, query: RetrievalQuery) -> RetrievalResponse: ...

    def keyword_search(self, text: str, sources: list[str], top_k: int) -> list[RetrievalResult]: ...

    def dense_search(self, text: str, sources: list[str], top_k: int) -> list[RetrievalResult]: ...

    def fuse(self, result_lists: list[list[RetrievalResult]], k: int) -> list[RetrievalResult]: ...
```

## Acceptance Criteria

| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-1 | FAQ retrieval returns FAQ content | Unit test with FAQ seed data |
| AC-2 | Policy retrieval returns Policy content | Unit test with Policy seed data |
| AC-3 | Case retrieval returns Case content | Unit test with Case seed data |
| AC-4 | Intent-based routing works correctly | Unit test routing for all 8 intent classes |
| AC-5 | RRF fusion merges keyword and dense results | Integration test with known duplicate |
| AC-6 | Top-k limiting works | Verify max results equals top_k |
| AC-7 | HNSW recall > 95% | Benchmark against brute force |
| AC-8 | Provider switching works | Test all three providers |
| AC-9 | Chinese full-text search works | Query with Chinese characters |
| AC-10 | Hybrid latency < 200ms | Timing test at 10K docs |

## Tasks

### Phase 1: Core Infrastructure

- [ ] Create retrieval module directory structure
- [ ] Implement EmbeddingProvider base protocol and ABC
- [ ] Implement FakeEmbeddingProvider for testing
- [ ] Implement SmallEmbeddingProvider (text2vec-base-multilingual)
- [ ] Create knowledge_base PostgreSQL schema
- [ ] Add HNSW and GIN indexes

### Phase 2: Retrieval Paths

- [ ] Implement keyword_search with PostgreSQL full-text search
- [ ] Implement dense_search with pgvector HNSW
- [ ] Implement SourceRouter with intent-based routing
- [ ] Implement RRF fusion algorithm

### Phase 3: Pipeline Integration

- [ ] Create RetrievalPipeline orchestration class
- [ ] Implement parallel execution of keyword and dense paths
- [ ] Add top_k limiting to final results
- [ ] Add timing instrumentation

### Phase 4: Quality Embeddings

- [ ] Implement LargeEmbeddingProvider (text2vec-large-chinese or m3e-base)
- [ ] Add environment-based provider selection
- [ ] Benchmark small vs large model quality

### Phase 5: Testing and Validation

- [ ] Write unit tests for all components
- [ ] Integration test with seed data
- [ ] Benchmark HNSW recall vs brute force
- [ ] Latency profiling at scale
- [ ] Update quality gate with retrieval tests

## Related Documents

- docs/retrieval_design.md - Detailed technical design
- docs/technical_decisions.md - Architecture decisions
- openspec/specs/rag-retrieval/spec.md - Official OpenSpec (after promotion)

## Limitations

1. **Chinese stemming**: PostgreSQL Chinese text search is less mature than English; dense retrieval compensates
2. **HNSW memory**: HNSW indices consume more memory than IVF_PQ; acceptable for MVP scale
3. **Single-vector-dimension**: All embeddings must use same dimension; no mixed-dimension retrieval
4. **No reranking**: Final ranking is limited to RRF fusion; cross-encoder reranking is future work

## Future Work

1. **Cross-encoder Reranking**: Integrate Cohere or local CrossEncoder for refined ranking
2. **Query Expansion**: Use LLM to expand queries with synonyms
3. **Self-Query Retrieval**: Parse structured filters from natural queries
4. **IVF_PQ Migration**: Move to FAISS/Milvus if corpus exceeds 10M vectors
5. **Knowledge Graph**: Link FAQ entries to Policy sections for hierarchical retrieval
