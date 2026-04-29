## Phase 1: Schema + Seed Data

- [ ] 1.1 Create `src/ticketpilot/retrieval/__init__.py` with package exports
- [ ] 1.2 Create `src/ticketpilot/retrieval/schema/__init__.py`
- [ ] 1.3 Create `src/ticketpilot/retrieval/schema/knowledge.py` with Pydantic models:
  - DocType enum (FAQ, POLICY, CASE)
  - KnowledgeDocument (base)
  - FAQDocument, PolicyDocument, CaseDocument
  - KnowledgeChunk with parent_chunk_id and chunk_level
- [ ] 1.4 Create `src/ticketpilot/retrieval/schema/retrieval.py` with:
  - RetrievalQuery, RetrievalResult, RetrievalTrace Pydantic models
- [ ] 1.5 Create `src/ticketpilot/retrieval/schema/seeds.py` for seed data loading
- [ ] 1.6 Create database migration for knowledge_faq table
- [ ] 1.7 Create database migration for knowledge_policy table
- [ ] 1.8 Create database migration for knowledge_case table
- [ ] 1.9 Create database migration for knowledge_chunks table
- [ ] 1.10 Create database migration for retrieval_traces table
- [ ] 1.11 Create `data/knowledge/faq_seed.json` with 10+ FAQ documents
- [ ] 1.12 Create `data/knowledge/policy_seed.json` with 10+ Policy documents
- [ ] 1.13 Create `data/knowledge/case_seed.json` with 10+ Case documents
- [ ] 1.14 Verify schema validation with basic instantiation tests

## Phase 2: PostgreSQL Keyword Retrieval

- [ ] 2.1 Create `src/ticketpilot/retrieval/db/__init__.py`
- [ ] 2.2 Create `src/ticketpilot/retrieval/db/connection.py` with DB connection management
- [ ] 2.3 Create `src/ticketpilot/retrieval/db/keyword.py` with:
  - PostgreSQL FTS using to_tsvector/to_tsquery
  - ts_rank scoring
  - Top-k results return
- [ ] 2.4 Create parent-child chunking utility function
- [ ] 2.5 Write unit tests for keyword retrieval

## Phase 3: pgvector + HNSW Setup

- [ ] 3.1 Create `src/ticketpilot/retrieval/providers/__init__.py`
- [ ] 3.2 Create `src/ticketpilot/retrieval/providers/embedding.py` with:
  - EmbeddingProvider interface (abstract class)
  - FakeEmbeddingProvider (returns random vectors)
  - SmallEmbeddingProvider (text-embedding-3-small)
  - QualityEmbeddingProvider (text-embedding-3-large placeholder)
- [ ] 3.3 Create `src/ticketpilot/retrieval/db/vector.py` with:
  - HNSW vector retrieval using pgvector
  - Cosine similarity scoring
  - Top-k results return
- [ ] 3.4 Create HNSW index migration with m=16, ef_construction=200
- [ ] 3.5 Write unit tests for vector retrieval with fake embeddings

## Phase 4: Hybrid Retrieval + RRF

- [ ] 4.1 Create `src/ticketpilot/retrieval/db/fusion.py` with:
  - RRF fusion implementation with k=60
  - Combines keyword_rank + vector_rank
- [ ] 4.2 Create `src/ticketpilot/retrieval/pipeline.py` with HybridRetrievalPipeline:
  - Accepts query text
  - Generates query embedding
  - Calls keyword retrieval
  - Calls vector retrieval
  - Applies RRF fusion
  - Returns fused results
- [ ] 4.3 Create `src/ticketpilot/retrieval/traces.py` with RetrievalTraceLogger
- [ ] 4.4 Write unit tests for RRF fusion
- [ ] 4.5 Write integration tests for full pipeline

## Phase 5: Retrieval Traces + Smoke Test

- [ ] 5.1 Create `tests/unit/test_retrieval.py`
- [ ] 5.2 Implement golden case 1: FAQ lookup (routing intent)
- [ ] 5.3 Implement golden case 2: Policy lookup (compliance check)
- [ ] 5.4 Implement golden case 3: Case lookup (similar ticket precedent)
- [ ] 5.5 Implement golden case 4: Hybrid query (keyword + dense both contribute)
- [ ] 5.6 Implement golden case 5: Parent-child retrieval (child needs parent context)
- [ ] 5.7 Implement golden case 6: Multi-source fusion (FAQ + Case both returned)
- [ ] 5.8 Verify all 6 golden cases pass smoke test
- [ ] 5.9 Verify retrieval trace contains all required fields:
  - query, keyword_results, vector_results, fused_results
  - final_evidence, retrieved_doc_ids, scores, doc_type, source ids

## Phase 6: Documentation and Quality Gate

- [ ] 6.1 Update `docs/changelog.md` with retrieval foundation entry
- [ ] 6.2 Run quality gate: `bash scripts/run_quality_gate.sh`
- [ ] 6.3 Verify `openspec validate --all` passes

## Acceptance Criteria Verification

- [ ] AC1: FAQ / Policy / Case three knowledge sources are physically separated (3 distinct tables)
- [ ] AC2: Each knowledge chunk has: doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, risk_level
- [ ] AC3: Parent-child chunking is established: child can trace back to parent
- [ ] AC4: PostgreSQL keyword retrieval returns top-k results
- [ ] AC5: pgvector HNSW vector retrieval returns top-k results
- [ ] AC6: RRF input includes: keyword_rank + vector_rank
- [ ] AC7: Retrieval trace can record: query, keyword results, vector results, fused results, final evidence, scores, doc_type, source ids
- [ ] AC8: Seed data has: 10+ FAQ, 10+ Policy, 10+ Case
- [ ] AC9: At least 6 retrieval golden cases exist
- [ ] AC10: Retrieval smoke test can run
