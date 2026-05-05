# retrieval-evaluation Specification

## Purpose
TBD - created by archiving change add-layered-knowledge-retrieval-foundation. Update Purpose after archive.
## Requirements
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

### Requirement: Refined wrong-case taxonomy
The system SHALL classify retrieval failures using a refined taxonomy beyond the Phase 8 `missing_doc_type` single category.
Each failed query SHALL be assigned to exactly one primary category from the refined set.

#### Scenario: Missing FAQ identified
- **GIVEN** a retrieval failure where expected evidence includes FAQ but no FAQ document appears in top-10
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `missing_faq`

#### Scenario: Missing Policy identified
- **GIVEN** a retrieval failure where expected evidence includes Policy but no Policy document appears in top-10
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `missing_policy`

#### Scenario: Missing Case identified
- **GIVEN** a retrieval failure where expected evidence includes Case but no Case document appears in top-10
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `missing_case`

#### Scenario: Doc type mismatch identified
- **GIVEN** a retrieval where docs of the expected type exist in the knowledge base but were returned as a different type
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `doc_type_mismatch`

#### Scenario: Business domain gap identified
- **GIVEN** a retrieval failure where the entire business domain has sparse or no coverage across all doc types
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `business_domain_gap`

#### Scenario: Risk level gap identified
- **GIVEN** a retrieval failure where knowledge lacks records annotated at the required risk level
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `risk_level_gap`

#### Scenario: Query expansion gap identified
- **GIVEN** a retrieval failure where the query is underspecified for knowledge that exists
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `query_expansion_gap`

#### Scenario: Golden label gap identified
- **GIVEN** a retrieval failure where golden expectations are incomplete or empty (e.g., empty expected_evidence_doc_types)
- **WHEN** refined wrong-case analysis runs
- **THEN** the case SHALL be classified as `golden_label_gap`

### Requirement: Refined taxonomy categories defined
The refined wrong-case analysis SHALL use the following category definitions.

#### Scenario: All refined categories available
- **GIVEN** the refined wrong-case taxonomy module
- **WHEN** the taxonomy constants are accessed
- **THEN** all 8 categories SHALL be defined

| Category | Definition | Actionable Fix |
|----------|------------|----------------|
| `missing_faq` | No FAQ record covers the intent/domain combination | Add FAQ seed record |
| `missing_policy` | No Policy record covers the rule/compliance topic | Add Policy seed record |
| `missing_case` | No Case record covers the scenario/precedent | Add Case seed record |
| `doc_type_mismatch` | Retrieved docs exist but are the wrong type | Review query construction |
| `business_domain_gap` | Entire business domain has sparse or no coverage | Add cross-type seed records |
| `risk_level_gap` | Knowledge lacks records annotated at the required risk level | Add risk-tagged records |
| `query_expansion_gap` | Retrieval query is underspecified for existing knowledge | Improve query builder |
| `golden_label_gap` | Golden expectations are incomplete or empty | Fix golden labels |

### Requirement: Phase 8 vs Phase 9 wrong-case comparison
The system SHALL support comparing wrong-case distributions between Phase 8 baseline and Phase 9 expanded knowledge.
The comparison SHALL report delta per category.

#### Scenario: Phase 9 comparison delta computed
- **GIVEN** Phase 8 wrong-case distribution and Phase 9 wrong-case distribution
- **WHEN** comparison is computed
- **THEN** per-category delta is reported (Phase 8 count, Phase 9 count, change)

#### Scenario: Missing_doc_type reduction reported
- **GIVEN** Phase 8 has 41 `missing_doc_type` cases (pre-refinement) and Phase 9 has N cases across refined categories
- **WHEN** comparison report is generated
- **THEN** the reduction in total wrong cases and shift in category distribution is reported

### Requirement: Optional doc-level golden labels
The golden expectations schema SHALL support an optional `expected_relevant_doc_ids` column containing document UUIDs.
When present, evaluation SHALL compute Recall@K at document level. When absent, evaluation SHALL fall back to doc_type-level matching only.

#### Scenario: Doc-level labels used when present
- **GIVEN** a golden expectation row with `expected_relevant_doc_ids=["uuid-1", "uuid-2"]`
- **WHEN** Recall@3 is computed
- **THEN** hit/miss is determined by whether any of the listed UUIDs appear in top-3 results

#### Scenario: Doc-level labels absent, fallback to doc_type
- **GIVEN** a golden expectation row without `expected_relevant_doc_ids`
- **WHEN** evaluation runs
- **THEN** doc_type-level recall is used (existing behavior, unchanged)

### Requirement: Immutable Phase 7/8 baselines
Phase 9 evaluation SHALL NOT modify any Phase 7 or Phase 8 report files.
Phase 9 SHALL write outputs to its own namespaced paths.

#### Scenario: Phase 8 report unchanged after Phase 9 run
- **GIVEN** Phase 8 fake_vs_real_comparison reports exist at `reports/retrieval/`
- **WHEN** Phase 9 evaluation runs
- **THEN** Phase 8 report files remain unmodified

#### Scenario: Phase 9 outputs namespaced
- **GIVEN** a Phase 9 evaluation run
- **WHEN** outputs are written
- **THEN** they are written to `reports/retrieval/phase9_*` paths distinct from Phase 8 paths

### Requirement: Knowledge-driven comparison (not provider-driven)
Phase 9 comparison SHALL isolate knowledge base size as the independent variable.
Provider SHALL remain fixed (fake default; real opt-in) across baseline and expanded runs within the same comparison.

#### Scenario: Same provider used for Phase 9 comparison pair
- **GIVEN** a Phase 9 before-vs-after comparison run
- **WHEN** both baseline and expanded evaluation execute
- **THEN** the same embedding provider is used for both runs

