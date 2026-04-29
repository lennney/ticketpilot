# add-layered-knowledge-retrieval-foundation

Build the retrieval foundation for TicketPilot: FAQ / Policy / Case layered knowledge base with hybrid PostgreSQL full-text + pgvector vector retrieval using RRF fusion.

## Why

TicketPilot requires evidence-grounded reply generation. Before generating replies, the system must reliably retrieve relevant knowledge from FAQ documents, policy documents, and historical case summaries. This vertical slice establishes the layered knowledge architecture and hybrid retrieval pipeline.

## What Changes

- Add layered knowledge schema: FAQ / Policy / Case source separation with parent-child chunking
- Add PostgreSQL full-text keyword retrieval
- Add pgvector HNSW vector retrieval
- Add RRF fusion for hybrid results
- Add retrieval trace structure for debugging and evaluation
- Add seed data: 10+ FAQ, 10+ Policy, 10+ Case documents
- Add 6 retrieval golden cases for smoke testing

## Capabilities

### New Capabilities

- `knowledge-schema`: Pydantic schemas and DB schema for layered knowledge
- `retrieval-pipeline`: Hybrid retrieval pipeline interface
- `retrieval-evaluation`: Golden cases and metrics

### Modified Capabilities

- (none - foundation only)

## Impact

- New module: `src/ticketpilot/retrieval/` with knowledge schemas, retrieval pipeline
- New seed data: `data/knowledge/` with FAQ, Policy, Case JSON files
- New test files: `tests/unit/test_retrieval.py` with golden case smoke tests
- No reply generation yet (handled in later vertical slice)
- No reranker integration yet
- No Langfuse/Ragas yet
- No Streamlit UI yet

## Risk Warnings

1. **FORBIDDEN**: Mixing FAQ/Policy/Case into one table
2. **FORBIDDEN**: Only using small chunks without parent
3. **FORBIDDEN**: Vector-only retrieval without keyword
4. **NOT YET**: Premature embedding fine-tuning

## Acceptance Criteria

1. FAQ / Policy / Case three knowledge sources are physically separated (3 distinct tables)
2. Each knowledge chunk has: doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, risk_level
3. Parent-child chunking is established: child can trace back to parent
4. PostgreSQL keyword retrieval returns top-k results
5. pgvector HNSW vector retrieval returns top-k results
6. RRF input includes: keyword_rank + vector_rank
7. Retrieval trace can record: query, keyword results, vector results, fused results, final evidence, scores, doc_type, source ids
8. Seed data has: 10+ FAQ, 10+ Policy, 10+ Case
9. At least 6 retrieval golden cases exist
10. Retrieval smoke test can run
