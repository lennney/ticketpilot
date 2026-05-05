# knowledge-schema Specification

## Purpose
TBD - created by archiving change add-layered-knowledge-retrieval-foundation. Update Purpose after archive.
## Requirements
### Requirement: DocType enum
The system SHALL define DocType as enum with 3 values: FAQ, POLICY, CASE.

#### Scenario: DocType enum values
- **WHEN** DocType enum is accessed
- **THEN** all 3 values (FAQ, POLICY, CASE) are available

### Requirement: ChunkLevel enum
The system SHALL define ChunkLevel as enum with 2 values: PARENT (1), CHILD (2).

#### Scenario: ChunkLevel enum values
- **WHEN** ChunkLevel enum is accessed
- **THEN** both values (PARENT=1, CHILD=2) are available

### Requirement: BusinessDomain enum
The system SHALL define BusinessDomain as enum with values: REFUND, RETURN_EXCHANGE, ACCOUNT, TECHNICAL, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER.

#### Scenario: BusinessDomain enum values
- **WHEN** BusinessDomain enum is accessed
- **THEN** all 8 domain values are available

### Requirement: FAQDocument schema
The system SHALL define FAQDocument with fields: id (UUID), doc_type (DocType='FAQ'), business_domain (BusinessDomain), title (str), content (str), intent_tags (list[str]), created_at (datetime), updated_at (datetime).

#### Scenario: FAQDocument validation
- **WHEN** FAQDocument is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: FAQDocument doc_type fixed
- **WHEN** FAQDocument is created without doc_type
- **THEN** doc_type defaults to DocType.FAQ

### Requirement: PolicyDocument schema
The system SHALL define PolicyDocument with fields: id (UUID), doc_type (DocType='POLICY'), business_domain (BusinessDomain), policy_code (str), title (str), content (str), effective_date (date), created_at (datetime), updated_at (datetime).

#### Scenario: PolicyDocument validation
- **WHEN** PolicyDocument is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: PolicyDocument policy_code format
- **WHEN** PolicyDocument is created with policy_code "7.3.2"
- **THEN** it passes Pydantic validation

### Requirement: CaseDocument schema
The system SHALL define CaseDocument with fields: id (UUID), doc_type (DocType='CASE'), business_domain (BusinessDomain), case_id (str), issue_summary (str), resolution (str), risk_level (str: "low"|"medium"|"high"), compensation_amount (Optional[Decimal]), created_at (datetime), updated_at (datetime).

#### Scenario: CaseDocument validation
- **WHEN** CaseDocument is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: CaseDocument risk_level enum
- **WHEN** CaseDocument is created with risk_level outside "low"|"medium"|"high"
- **THEN** Pydantic validation raises an error

### Requirement: KnowledgeChunk schema
The system SHALL define KnowledgeChunk with fields: id (UUID), doc_id (UUID), doc_type (DocType), parent_chunk_id (Optional[UUID]), chunk_level (ChunkLevel), business_domain (BusinessDomain), risk_level (Optional[str]), content (str), content_hash (str), embedding (list[float]), created_at (datetime).

#### Scenario: KnowledgeChunk validation
- **WHEN** KnowledgeChunk is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: KnowledgeChunk parent-child relationship
- **WHEN** KnowledgeChunk is created with chunk_level=CHILD
- **THEN** parent_chunk_id must reference a valid parent chunk

#### Scenario: KnowledgeChunk embedding dimensions
- **WHEN** KnowledgeChunk is created with embedding
- **THEN** embedding must have 1536 dimensions (text-embedding-3-small)

### Requirement: FAQ / Policy / Case physical separation
The system SHALL store FAQ, Policy, and Case documents in physically separate database tables.

#### Scenario: FAQ table exists
- **WHEN** database is queried for knowledge_faq table
- **THEN** the table exists with correct schema

#### Scenario: Policy table exists
- **WHEN** database is queried for knowledge_policy table
- **THEN** the table exists with correct schema

#### Scenario: Case table exists
- **WHEN** database is queried for knowledge_case table
- **THEN** the table exists with correct schema

#### Scenario: Knowledge chunks table references source types
- **WHEN** knowledge_chunks table is queried
- **THEN** doc_type column distinguishes FAQ/POLICY/CASE source

### Requirement: Parent-child chunk linkage
The system SHALL support parent-child chunking where each child chunk references its parent via parent_chunk_id.

#### Scenario: Parent chunk creation
- **WHEN** parent KnowledgeChunk is created with chunk_level=PARENT
- **THEN** parent_chunk_id is NULL

#### Scenario: Child chunk creation
- **WHEN** child KnowledgeChunk is created with chunk_level=CHILD
- **THEN** parent_chunk_id references a valid parent chunk

#### Scenario: Parent retrieval via child
- **WHEN** child chunk ID is known
- **THEN** parent chunk can be retrieved via parent_chunk_id

### Requirement: Chunk metadata fields
Each knowledge chunk MUST have: doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, risk_level.

#### Scenario: Chunk has all required metadata
- **WHEN** KnowledgeChunk is validated
- **THEN** all 6 required fields are present

#### Scenario: Missing required field
- **WHEN** KnowledgeChunk is created without doc_id
- **THEN** Pydantic validation raises an error

### Requirement: Knowledge expansion traceability
Each knowledge record added during Phase 9 SHALL have a documented relationship to the wrong-case gap(s) it addresses.
This traceability SHALL be maintained in the gap mapping report, not in the database schema.

#### Scenario: New FAQ record traces to wrong case
- **GIVEN** a new FAQ record added to `faq_seed.json`
- **WHEN** the gap mapping document is inspected
- **THEN** the document identifies which wrong case(s) the record addresses

#### Scenario: New Policy record traces to wrong case
- **GIVEN** a new Policy record added to `policy_seed.json`
- **WHEN** the gap mapping document is inspected
- **THEN** the document identifies which wrong case(s) the record addresses

#### Scenario: New Case record traces to wrong case
- **GIVEN** a new Case record added to `case_seed.json`
- **WHEN** the gap mapping document is inspected
- **THEN** the document identifies which wrong case(s) the record addresses

### Requirement: Seed data source rules preserved
All Phase 9 knowledge records SHALL comply with Phase 7 data strategy:
- Synthetic: written by developer based on Chinese e-commerce domain knowledge
- Adapted: derived from public e-commerce policy documentation, reworded
- Public-source-inspired: based on common CS scenarios, not proprietary data
- No real customer data ever

#### Scenario: Seed file validated as synthetic/adapted
- **GIVEN** a new seed record added in Phase 9
- **WHEN** source review is performed
- **THEN** the record is confirmed as synthetic, adapted, or public-source-inspired only

#### Scenario: No real data in seed file
- **GIVEN** Phase 9 seed files
- **WHEN** secret scan and data review run
- **THEN** no real enterprise customer data, PII, or credentials are found

### Requirement: FAQ/Policy/Case physical separation preserved
Phase 9 knowledge expansion SHALL maintain separate seed files for FAQ, Policy, and Case.
New records SHALL NOT be combined into a single merged seed file.

#### Scenario: FAQ records only in faq_seed.json
- **GIVEN** Phase 9 adds new FAQ records
- **WHEN** the seed data is inspected
- **THEN** FAQ records exist only in `data/knowledge/faq_seed.json`

#### Scenario: Policy records only in policy_seed.json
- **GIVEN** Phase 9 adds new Policy records
- **WHEN** the seed data is inspected
- **THEN** Policy records exist only in `data/knowledge/policy_seed.json`

#### Scenario: Case records only in case_seed.json
- **GIVEN** Phase 9 adds new Case records
- **WHEN** the seed data is inspected
- **THEN** Case records exist only in `data/knowledge/case_seed.json`

### Requirement: Schema compatibility with existing knowledge records
New Phase 9 knowledge records SHALL validate against the same Pydantic schemas (FAQDocument, PolicyDocument, CaseDocument, KnowledgeChunk) as Phase 7 records.
No schema changes are required.

#### Scenario: New FAQ record passes Pydantic validation
- **GIVEN** a new FAQ record created in Phase 9
- **WHEN** FAQDocument.model_validate() is called
- **THEN** validation passes without errors

#### Scenario: New Policy record passes Pydantic validation
- **GIVEN** a new Policy record created in Phase 9
- **WHEN** PolicyDocument.model_validate() is called
- **THEN** validation passes without errors

#### Scenario: New Case record passes Pydantic validation
- **GIVEN** a new Case record created in Phase 9
- **WHEN** CaseDocument.model_validate() is called
- **THEN** validation passes without errors

### Requirement: Chunking architecture unchanged
Phase 9 SHALL NOT modify the chunking strategy. Current short knowledge records (1 source record ≈ 1 chunk) SHALL remain unchanged.
Parent-child chunking SHALL remain available but is not required for Phase 9 expansion.

#### Scenario: Chunker.py unchanged
- **GIVEN** Phase 9 implementation
- **WHEN** `src/ticketpilot/retrieval/chunker.py` is inspected
- **THEN** it is identical to its Phase 8 state

#### Scenario: One-record-one-chunk assumption preserved
- **GIVEN** new Phase 9 knowledge records
- **WHEN** they are seeded into the knowledge base
- **THEN** each source record maps to exactly one knowledge chunk (no chunk splitting)

