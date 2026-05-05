# retrieval-evaluation Specification Delta — Phase 10

## ADDED Requirements

### Requirement: Per-case layered trace export
The system SHALL support exporting layered retrieval traces for diagnostic purposes.
A layered trace export SHALL include, for each case:
- keyword results with chunk_id, doc_id, doc_type, score, rank
- vector results with chunk_id, doc_id, doc_type, score, rank
- fused results with chunk_id, doc_id, doc_type, rrf_score, keyword_rank, keyword_contribution, vector_rank, vector_contribution, sources
- final evidence candidate IDs
- embedding provider identity

#### Scenario: Layered trace includes all three ranks
- **GIVEN** a retrieval trace for a P0-related case
- **WHEN** the layered trace is exported
- **THEN** for each expected evidence, the export shows rank in keyword results (or None), rank in vector results (or None), and rank in fused results (or None)

#### Scenario: Embedding provider recorded in export
- **GIVEN** a retrieval trace generated with openai_compatible provider
- **WHEN** the layered trace is exported
- **THEN** the export includes `embedding_provider: "openai_compatible"`

### Requirement: Bottleneck classification taxonomy
The system SHALL classify retrieval failures using a ranking bottleneck taxonomy.
Each P0-related wrong case SHALL be assigned to exactly one primary bottleneck category.

#### Scenario: Keyword not recalled classification
- **GIVEN** a P0 added record chunk_id
- **WHEN** the chunk_id is absent from trace.keyword_results
- **THEN** the case SHALL be classified as `keyword_not_recalled`

#### Scenario: Vector not recalled classification
- **GIVEN** a P0 added record chunk_id
- **WHEN** the chunk_id is absent from trace.vector_results
- **THEN** the case SHALL be classified as `vector_not_recalled`

#### Scenario: Recalled but fused low classification
- **GIVEN** a P0 added record chunk_id present in keyword or vector results
- **WHEN** its fused rank is greater than top_k (or absent from fused results)
- **THEN** the case SHALL be classified as `recalled_but_fused_low`

#### Scenario: Fused top-10 but metric still wrong classification
- **GIVEN** a P0 added record chunk_id present in fused top_k
- **WHEN** the case is still in the wrong-case list
- **THEN** the case SHALL be classified as `fused_top10_but_metric_still_wrong`

#### Scenario: Doc-level label missing classification
- **GIVEN** a golden expectation row with empty or missing `expected_relevant_doc_ids`
- **WHEN** the case is wrong at doc_type level
- **THEN** the case SHALL be classified as `doc_level_label_missing`

#### Scenario: Empty retrieval classification
- **GIVEN** a retrieval trace where both keyword and vector results are empty
- **WHEN** the case is classified
- **THEN** the case SHALL be classified as `empty_retrieval`

### Requirement: Bottleneck taxonomy categories defined
The bottleneck taxonomy SHALL include all 8 categories with definitions.

#### Scenario: All bottleneck categories available
- **GIVEN** the bottleneck taxonomy module
- **WHEN** the taxonomy constants are accessed
- **THEN** all 8 categories SHALL be defined: keyword_not_recalled, vector_not_recalled, recalled_but_fused_low, fused_top10_but_metric_still_wrong, doc_level_label_missing, query_expansion_gap, empty_retrieval, provider_identity_issue

| Category | Definition | Detection |
|---|---|---|
| `keyword_not_recalled` | P0 record absent from keyword results entirely | Programmatic |
| `vector_not_recalled` | P0 record absent from vector results entirely | Programmatic |
| `recalled_but_fused_low` | P0 record in keyword/vector but fused rank > top_k | Programmatic |
| `fused_top10_but_metric_still_wrong` | P0 record in fused top_k but case still classified wrong | Programmatic |
| `doc_level_label_missing` | Golden expectations lack doc_id-level labels | Programmatic |
| `query_expansion_gap` | Query underspecified for knowledge that exists | Manual |
| `empty_retrieval` | Both retrievers return zero results | Programmatic |
| `provider_identity_issue` | Trace embedding provider differs from expected | Programmatic |

### Requirement: P0 added-record rank tracking
For each P0 added record (from Phase 9.4.1), the system SHALL track its best rank
across keyword, vector, and fused results for every related case.

#### Scenario: Best rank reported per retriever
- **GIVEN** a P0 record with chunk_id X and a related case with retrieval trace T
- **WHEN** rank tracking is computed
- **THEN** `best_keyword_rank`, `best_vector_rank`, `best_fused_rank` are reported (or None if absent)

#### Scenario: Absent from all retrievers
- **GIVEN** a P0 record not found in any retrieval layer for a case
- **WHEN** rank tracking is computed
- **THEN** all three ranks are None, and the case is flagged for provider or query investigation

### Requirement: Recommendation report
The diagnosis SHALL produce a recommendation report classifying the dominant bottleneck(s)
and recommending next-step actions.

#### Scenario: Dominant bottleneck identified
- **GIVEN** bottleneck classifications across all P0 cases
- **WHEN** recommendation report is generated
- **THEN** the report identifies which bottleneck category is most frequent

#### Scenario: Next-step recommendation
- **GIVEN** bottleneck distribution
- **WHEN** recommendation report is generated
- **THEN** the report recommends one or more of: doc-level labels, query expansion tuning, RRF parameter adjustment, reranker introduction, or limitation acceptance

### Requirement: Provider identity declaration in diagnosis reports
Every Phase 10 diagnosis report SHALL declare the embedding provider used.
Reports using fake provider SHALL carry a disclaimer.

#### Scenario: Real provider report
- **GIVEN** diagnosis was performed using openai_compatible traces
- **WHEN** report is generated
- **THEN** report declares `embedding_provider: openai_compatible / text-embedding-v4 / 1024-dim` and may draw semantic ranking conclusions

#### Scenario: Fake provider report
- **GIVEN** diagnosis was performed using fake embedding traces
- **WHEN** report is generated
- **THEN** report includes disclaimer: "Fake embeddings carry no semantic meaning. Ranking conclusions are pipeline-mechanical only."
