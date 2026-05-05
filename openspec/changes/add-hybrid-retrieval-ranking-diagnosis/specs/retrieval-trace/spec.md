# retrieval-trace Specification Delta — Phase 10

## ADDED Requirements

### Requirement: Trace field completeness for diagnosis
The RetrievalTrace SHALL contain sufficient fields for layered retrieval diagnosis.
The following fields are required per result in each layer:

#### Scenario: KeywordResult has required diagnosis fields
- **GIVEN** a KeywordResult in a retrieval trace
- **WHEN** inspected for diagnosis fields
- **THEN** it contains chunk_id, doc_id, doc_type, content, score, rank, and search_method

#### Scenario: VectorResult has required diagnosis fields
- **GIVEN** a VectorResult in a retrieval trace
- **WHEN** inspected for diagnosis fields
- **THEN** it contains chunk_id, doc_id, doc_type, content, score, rank, and embedding_provider

#### Scenario: FusedResult has required diagnosis fields
- **GIVEN** a FusedResult in a retrieval trace
- **WHEN** inspected for diagnosis fields
- **THEN** it contains chunk_id, doc_id, doc_type, content, rrf_score, keyword_rank, keyword_contribution, vector_rank, vector_contribution, and sources

### Requirement: Per-chunk cross-layer lookup
The RetrievalTrace SHALL support querying a specific chunk_id across all three retrieval layers.

#### Scenario: Chunk found in keyword results
- **GIVEN** a retrieval trace and a chunk_id that appeared in keyword search
- **WHEN** cross-layer lookup is performed
- **THEN** the keyword result is returned with its rank and score

#### Scenario: Chunk found in vector results
- **GIVEN** a retrieval trace and a chunk_id that appeared in vector search
- **WHEN** cross-layer lookup is performed
- **THEN** the vector result is returned with its rank and score

#### Scenario: Chunk found in fused results
- **GIVEN** a retrieval trace and a chunk_id that appeared in fused results
- **WHEN** cross-layer lookup is performed
- **THEN** the fused result is returned with its rrf_score and per-ranker contributions

#### Scenario: Chunk absent from all layers
- **GIVEN** a retrieval trace and a chunk_id not found in any layer
- **WHEN** cross-layer lookup is performed
- **THEN** the lookup returns None for all three layers

### Requirement: Provider-aware trace export
The retrieval trace export SHALL include provider identity metadata.
Reports SHALL distinguish between fake and real provider traces.

#### Scenario: Provider recorded in trace
- **GIVEN** a retrieval trace generated with openai_compatible provider
- **WHEN** trace is exported for diagnosis
- **THEN** the export includes `embedding_provider: "openai_compatible"`

#### Scenario: Fake provider trace disclaimer
- **GIVEN** a retrieval trace generated with fake embedding provider
- **WHEN** trace is exported for diagnosis
- **THEN** the export or accompanying report includes a disclaimer that ranking conclusions from fake traces are pipeline-mechanical only

### Requirement: Trace export format
The diagnosis trace export SHALL use a structured format suitable for both programmatic analysis and human review.

#### Scenario: JSON export for programmatic analysis
- **GIVEN** a set of retrieval traces for P0-related cases
- **WHEN** traces are exported for programmatic analysis
- **THEN** the export is in JSON format with case_id as key and per-layer results as nested objects

#### Scenario: Markdown export for human review
- **GIVEN** bottleneck classification results
- **WHEN** a human-readable report is generated
- **THEN** the report includes per-case layered trace summaries with keyword/vector/fused/final status and bottleneck classification

### Requirement: No trace schema regression
Existing RetrievalTrace consumers SHALL NOT break due to Phase 10 changes.

#### Scenario: Existing trace tests pass unchanged
- **GIVEN** existing RetrievalTrace schema tests
- **WHEN** Phase 10 trace export or analysis code is added
- **THEN** existing trace tests continue to pass

#### Scenario: Existing pipeline trace generation unchanged
- **GIVEN** the hybrid retrieval pipeline
- **WHEN** Phase 10 trace export runs
- **THEN** the pipeline's trace generation behavior is not modified
