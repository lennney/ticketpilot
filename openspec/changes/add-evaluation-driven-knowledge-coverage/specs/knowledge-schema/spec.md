## ADDED Requirements

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
