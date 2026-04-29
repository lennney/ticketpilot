## MODIFIED Requirements

### Requirement: FAQ / Policy / Case physical separation

The system SHALL store FAQ, Policy, and Case **source documents** in physically separate database tables (`knowledge_faq`, `knowledge_policy`, `knowledge_case`), each with type-specific columns. All document types SHALL share a unified `knowledge_chunks` table for retrieval, with `source_table` and `source_id` columns tracing each chunk back to its source document.

#### Scenario: FAQ source table exists
- **WHEN** database is queried for `knowledge_faq` table
- **THEN** the table exists with columns: id, business_domain, title, content, intent_tags, created_at, updated_at

#### Scenario: Policy source table exists
- **WHEN** database is queried for `knowledge_policy` table
- **THEN** the table exists with columns: id, business_domain, policy_code, title, content, effective_date, created_at, updated_at

#### Scenario: Case source table exists
- **WHEN** database is queried for `knowledge_case` table
- **THEN** the table exists with columns: id, business_domain, case_id, issue_summary, resolution, risk_level, compensation_amount, created_at, updated_at

#### Scenario: Knowledge chunks table references source
- **WHEN** `knowledge_chunks` table is queried
- **THEN** each row has `source_table` (one of knowledge_faq, knowledge_policy, knowledge_case) and `source_id` (UUID referencing the source table)

#### Scenario: Doc type discriminator retained
- **WHEN** `knowledge_chunks` table is queried
- **THEN** `doc_type` column is retained as a denormalized copy of the source type for query convenience

#### Scenario: Chunk-source referential integrity
- **WHEN** a chunk is inserted into `knowledge_chunks`
- **THEN** its `source_id` must reference an existing row in the table named by `source_table`

## Rationale

The original spec required "FAQ, Policy, and Case documents in physically separate database tables." The implementation used a single `knowledge_chunks` table with a `doc_type` discriminator column, which violated the spec.

This amendment clarifies the design intent:

1. **Source layer** (3 tables): Each document type has its own table with type-specific columns. FAQ has `intent_tags`. Policy has `policy_code` and `effective_date`. Case has `risk_level` and `compensation_amount`. Physical separation at this layer enables different update frequencies, access patterns, and retention policies.

2. **Chunk layer** (1 table): All chunks share a unified table (`knowledge_chunks`) for retrieval. This is necessary because retrieval operations (FTS, HNSW vector search, RRF fusion) operate uniformly across all document types. `source_table` and `source_id` columns maintain traceability back to source documents.

This two-layer design is the standard pattern used by LangChain, LlamaIndex, and production RAG systems. It satisfies the spec intent of physical separation while enabling efficient retrieval.
