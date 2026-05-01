## ADDED Requirements

### Requirement: Retrieval Golden Case 1 - FAQ Lookup (routing intent)
The system SHALL retrieve FAQ documents for intent routing queries.

#### Scenario: FAQ lookup for return intent
- **WHEN** query is "我想退货怎么处理"
- **THEN** top results include FAQ documents about return_exchange

#### Scenario: FAQ lookup returns intent_tags
- **WHEN** FAQ retrieval returns results
- **THEN** results include intent_tags for routing

### Requirement: Retrieval Golden Case 2 - Policy Lookup (compliance check)
The system SHALL retrieve Policy documents for compliance queries.

#### Scenario: Policy lookup by clause number
- **WHEN** query includes policy clause reference like "7.3.2"
- **THEN** top results include Policy document with matching policy_code

#### Scenario: Policy lookup for refund eligibility
- **WHEN** query is "超过30天还能退款吗"
- **THEN** top results include Policy documents about refund time limits

### Requirement: Retrieval Golden Case 3 - Case Lookup (similar ticket precedent)
The system SHALL retrieve Case documents for precedent matching.

#### Scenario: Case lookup for similar issue
- **WHEN** query is "商品破损投诉"
- **THEN** top results include Case documents with similar issue_summary

#### Scenario: Case lookup includes resolution
- **WHEN** Case retrieval returns results
- **THEN** results include resolution field

### Requirement: Retrieval Golden Case 4 - Hybrid Query (keyword + dense both contribute)
The system SHALL return relevant results when both keyword and vector retrieval contribute.

#### Scenario: Hybrid query with paraphrased intent
- **WHEN** query is "东西坏了怎么赔" (paraphrased from "商品破损赔偿")
- **THEN** keyword retrieval returns partial matches
- **AND** vector retrieval returns semantic matches
- **AND** RRF fusion combines both signals

### Requirement: Retrieval Golden Case 5 - Parent-Child Retrieval (child needs parent context)
The system SHALL retrieve parent chunks when child chunks match.

#### Scenario: Child chunk matches query
- **WHEN** child chunk content matches query
- **THEN** result includes parent_chunk_id for context retrieval

#### Scenario: Parent context available via child
- **WHEN** child chunk ID is in results
- **THEN** parent chunk content can be retrieved via parent_chunk_id

### Requirement: Retrieval Golden Case 6 - Multi-Source Fusion (FAQ + Case both returned)
The system SHALL return results from multiple source types in single query.

#### Scenario: Multi-source query
- **WHEN** query is "商品破损怎么处理"
- **THEN** results include both FAQ (how-to) and Case (similar precedent) documents

#### Scenario: Source diversity in results
- **WHEN** hybrid retrieval returns top-10
- **THEN** results span multiple doc_types (FAQ, POLICY, or CASE)

### Requirement: Seed data volume
The system SHALL have minimum seed data: 10+ FAQ, 10+ Policy, 10+ Case.

#### Scenario: FAQ seed count
- **WHEN** knowledge_faq table is queried
- **THEN** at least 10 documents exist

#### Scenario: Policy seed count
- **WHEN** knowledge_policy table is queried
- **THEN** at least 10 documents exist

#### Scenario: Case seed count
- **WHEN** knowledge_case table is queried
- **THEN** at least 10 documents exist

### Requirement: Retrieval smoke test executable
The system SHALL provide executable smoke tests for retrieval.

#### Scenario: Smoke test imports
- **WHEN** tests/unit/test_retrieval.py is imported
- **THEN** no import errors occur

#### Scenario: Smoke test runs
- **WHEN** pytest tests/unit/test_retrieval.py is executed
- **THEN** all 6 golden cases pass

### Requirement: Retrieval trace completeness
The system SHALL produce complete retrieval traces.

#### Scenario: Trace has query
- **WHEN** retrieval trace is created
- **THEN** query field contains original query text

#### Scenario: Trace has keyword results
- **WHEN** retrieval trace is created
- **THEN** keyword_results contains doc_ids and scores

#### Scenario: Trace has vector results
- **WHEN** retrieval trace is created
- **THEN** vector_results contains doc_ids and scores

#### Scenario: Trace has fused results
- **WHEN** retrieval trace is created
- **THEN** fused_results contains combined rankings with RRF scores

#### Scenario: Trace has final evidence
- **WHEN** retrieval trace is created
- **THEN** final_evidence contains selected evidence for reply generation

#### Scenario: Trace has scores
- **WHEN** retrieval trace is created
- **THEN** each result includes the scores used for ranking

#### Scenario: Trace has doc_type
- **WHEN** retrieval trace is created
- **THEN** each result includes doc_type (FAQ/POLICY/CASE)

#### Scenario: Trace has source ids
- **WHEN** retrieval trace is created
- **THEN** retrieved_doc_ids contains all source document UUIDs

### Requirement: Risk warnings documented
The system SHALL document and prevent forbidden patterns.

#### Scenario: Source mixing forbidden
- **WHEN** design is reviewed
- **THEN** mixing FAQ/Policy/Case into one table is documented as FORBIDDEN

#### Scenario: Orphan chunks forbidden
- **WHEN** design is reviewed
- **THEN** using only small chunks without parent is documented as FORBIDDEN

#### Scenario: Vector-only forbidden
- **WHEN** design is reviewed
- **THEN** vector-only retrieval without keyword is documented as FORBIDDEN

#### Scenario: Premature fine-tuning warned
- **WHEN** design is reviewed
- **THEN** premature embedding fine-tuning is documented as NOT YET
