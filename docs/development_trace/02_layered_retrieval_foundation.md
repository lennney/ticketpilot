# Stage 1B: Layered Knowledge Retrieval Foundation

## Stage Goal

Build the retrieval foundation for TicketPilot: a layered knowledge architecture with FAQ/Policy/Case source separation, parent-child chunking, hybrid keyword + vector retrieval using PostgreSQL FTS and pgvector HNSW, RRF fusion, and retrieval traces.

## Business Problem Addressed

Customer support agents need quick access to relevant knowledge when responding to tickets. Without a retrieval system, agents must manually search through FAQs, policies, and past cases. TicketPilot's retrieval engine provides:

- **FAQ lookup**: Quick answers to common questions (e.g., return policy, shipping times)
- **Policy lookup**: Compliance-relevant policy clauses (e.g., refund eligibility, liability limits)
- **Case lookup**: Historical resolution precedent for similar tickets
- **Hybrid search**: Combines exact keyword matching (for policy clause numbers, product codes) with semantic vector similarity (for paraphrased queries)

## Key Design Decisions

### 1. Two-layer source table architecture (source tables + unified chunks)

**Decision**: Three physically separate source tables (`knowledge_faq`, `knowledge_policy`, `knowledge_case`) with type-specific columns, plus one unified `knowledge_chunks` table for retrieval, with `source_table` and `source_id` columns tracing each chunk back to its source.

**Rationale**: Satisfies the spec requirement for physical separation (different update frequencies, access patterns, retention policies, metadata schemas) while preserving retrieval efficiency (single table for all chunks means no union queries).

**How this evolved**: The initial implementation had a single `knowledge_chunks` table with a `doc_type` discriminator and no source tables. The two-layer design was adopted during audit remediation (Stage 04, BLOCK-2) to satisfy the spec requirement. See `04_quality_gate_hardening.md` for details.

### 2. Parent-child chunking

**Decision**: Each document is split into parent chunks (500-1000 tokens, level 1) and child chunks (100-300 tokens, level 2) with `parent_chunk_id` linkage.

**Rationale**: Child chunks provide precise passage matching; parent chunks provide full context for reply generation. The linkage enables traceability from a matched passage to its broader context.

### 3. Hybrid retrieval (keyword + vector)

**Decision**: PostgreSQL full-text search (FTS) using `to_tsvector('simple', content)` with GIN index for keyword retrieval, plus pgvector HNSW index (`m=16`, `ef_construction=200`, `ef_search=100`, cosine distance) for vector retrieval.

**Rationale**: Policy clause numbers ("7.3.2") require exact keyword matching. Paraphrased queries require vector semantic similarity. Hybrid retrieval consistently outperforms either alone.

**FTS config note**: Uses `simple` (not `chinese`) tokenizer. The `simple` config tokenizes on whitespace. An 8-term Chinese business keyword fallback (LIKE-based) compensates when FTS returns no results.

### 4. Fake embedding provider for pipeline verification

**Decision**: `FakeEmbeddingProvider` generates 384-dimensional pseudo-random vectors from SHA-256 hashes of text content. Marked as "PIPELINE VERIFICATION ONLY."

**Rationale**: Proves the full retrieval pipeline works (embedding generation, HNSW indexing, cosine similarity scoring) without any external API or real embedding model. The fake provider is deterministic — same text always produces the same vector — enabling reproducible tests.

**Important caveat**: Fake embeddings have **no semantic meaning**. Retrieval quality tests using fake embeddings verify that the pipeline mechanics work, NOT that real retrieval quality is acceptable. Real semantic retrieval requires a real embedding provider.

### 5. RRF fusion with k=60

**Decision**: Reciprocal Rank Fusion combining keyword and vector rankings with the standard k=60 constant.

**Rationale**: RRF is a well-established fusion algorithm that does not require score calibration (keyword scores and vector cosine similarity are not directly comparable). The k=60 constant reduces the impact of large rank differences.

### 6. In-memory retrieval traces (not persisted to DB)

**Decision**: `RetrievalTrace` is a Pydantic model stored in memory on `TicketOutput`, not persisted to the `retrieval_traces` database table.

**Rationale**: The spec-defined `retrieval_traces` DB table was deferred to a future trace-observability change. The in-memory trace satisfies all spec completeness requirements for the MVP and can be asserted on in tests.

## Implementation Scope

- Created `src/ticketpilot/retrieval/schema/knowledge.py` with DocType enum (FAQ, POLICY, CASE), KnowledgeDocument base, type-specific document models, KnowledgeChunk with parent_chunk_id and chunk_level
- Created `src/ticketpilot/retrieval/schema/retrieval.py` with RetrievalQuery, RetrievalResult, FusedResult, RetrievalTrace models
- Created `src/ticketpilot/retrieval/schema/seeds.py` for seed data loading
- Created database migration `001` for initial `knowledge_chunks` table (later revised by migration `003` during audit remediation)
- Created `src/ticketpilot/retrieval/db/connection.py` with DB connection pool management
- Created `src/ticketpilot/retrieval/db/keyword.py` with PostgreSQL FTS keyword retrieval
- Created `src/ticketpilot/retrieval/providers/embedding.py` with EmbeddingProvider abstract class and FakeEmbeddingProvider
- Created `src/ticketpilot/retrieval/db/vector.py` with pgvector HNSW vector retrieval
- Created `src/ticketpilot/retrieval/db/fusion.py` with RRF fusion (k=60)
- Created `src/ticketpilot/retrieval/pipeline.py` with HybridRetrievalPipeline orchestrating keyword + vector + fusion
- Created `src/ticketpilot/retrieval/traces.py` with RetrievalTrace logging
- Created seed data: 12 FAQ, 12 Policy, 12 Case documents (36 documents total) in `data/knowledge/`
- Created parent-child chunking utility with configurable chunk sizes
- Unit tests for keyword retrieval, vector retrieval, RRF fusion, chunking, and retrieval pipeline
- Integration tests against live PostgreSQL + pgvector (55 integration tests total across all retrieval components)

## Forbidden Scope

- No reply generation (handled in Stage 1C)
- No real reranker (placeholder interface only)
- No Langfuse/Ragas observability (structured logging only at this stage)
- No Streamlit UI (handled in Stage 1D)
- No BM25 scoring (PostgreSQL FTS sufficient for MVP)
- No real embedding provider — only FakeEmbeddingProvider implemented
- No persistent retrieval traces DB table

## Tests and Quality Gate Result

- Unit tests: Component-level coverage for keyword, vector, RRF, chunking, and pipeline
- Integration tests: 55 pass against live PostgreSQL + pgvector with seed data
- Quality gate passes with DB available
- **Note**: Initial implementation had a DB gap (integration tests skipped when DB unavailable). This was resolved during audit remediation (Stage 04) with the `scripts/run_integration_tests.sh` runner and skip-count guard.

## Major Risks

| Risk | Handling |
|------|----------|
| **Fake embeddings prove pipeline mechanics, not real retrieval quality** | All documentation clearly states this. A real embedding provider is a deferred item. |
| **Seed data is synthetic, not real enterprise data** | 12 documents per type is sufficient for integration testing but not representative. Real data pack deferred. |
| **PostgreSQL FTS with `simple` config does not tokenize Chinese** | Compensated with 8-term Chinese business keyword fallback using LIKE queries. A `chinese` config was considered but `simple` was chosen for the MVP. |
| **HNSW memory usage for large collections** | Not addressed for MVP (small seed data). Parameter tuning (`m`, `ef_construction`) documented for future scaling. |
| **Parent-child chunking increases storage 2-3x** | Accepted for MVP scale. Not optimized. |

## Deferred Items

- Real embedding provider (small 384-d and quality 768-d tiers planned)
- Realistic enterprise data pack (replaces synthetic seed data)
- Persistent retrieval traces DB table (`retrieval_traces` migration deferred)
- SourceRouter implementation (intent-to-source routing deferred from design)
- BM25 or alternative keyword retrieval (PostgreSQL FTS sufficient for MVP)
- Embedding fine-tuning on support ticket data
- Retrieval evaluation harness (golden question-answer pairs)

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `ee513a2` | 2026-04-29 | spec: add layered knowledge retrieval foundation |
| (implementation commits on feature branch) | | |
| `ce58ba0` | 2026-05-01 | chore: archive add-layered-knowledge-retrieval-foundation OpenSpec change |

## Reusable Patterns

1. **Hybrid retrieval pipeline** — The keyword + vector + RRF fusion pattern is a standard RAG architecture. The provider abstraction (keyword/vector/fusion as pluggable components) is reusable for any retrieval system.
2. **Parent-child chunking** — The two-level chunking strategy with `parent_chunk_id` linkage and configurable chunk sizes is reusable for document chunking in any RAG system.
3. **Fake embedding provider pattern** — SHA-256 seeded deterministic embeddings for CI/testing without external API calls. The interface allows swapping in a real provider without changing the pipeline.
4. **Two-layer source architecture** — Source tables (type-specific schemas) + unified chunks table (retrieval-oriented) is a standard pattern (used by LangChain, LlamaIndex) for managing heterogeneous document types with a common retrieval interface.
5. **RRF fusion as score-agnostic ranking** — The RRF algorithm does not require score normalization between rankers, making it trivial to add or remove retrieval methods.
