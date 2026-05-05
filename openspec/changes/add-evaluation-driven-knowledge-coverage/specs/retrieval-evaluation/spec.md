## ADDED Requirements

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
