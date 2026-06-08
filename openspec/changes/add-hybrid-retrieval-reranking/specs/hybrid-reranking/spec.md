# hybrid-reranking Specification

## Purpose
Define the hybrid reranking system that combines multiple scoring signals (RRF score, embedding similarity, intent metadata boost, content quality) to produce higher-quality Top-K retrieval results for customer support ticket evidence retrieval.

## Requirements

### Requirement: HybridReranker multi-signal fusion
The system SHALL implement a HybridReranker that combines at least 4 scoring signals with configurable weights.

#### Scenario: HybridReranker produces ranked results
- **WHEN** HybridReranker.rerank() is called with candidates, query, and config
- **THEN** returns a list of RerankResult sorted by final_score descending

#### Scenario: Signal weights sum to 1.0
- **WHEN** RerankerConfig is loaded
- **THEN** all signal weights sum to 1.0 (validated at load time)

#### Scenario: Weight auto-adjustment on missing signals
- **WHEN** a signal is unavailable (e.g., fake embedding)
- **THEN** its weight is redistributed proportionally among available signals

### Requirement: RRF Score Signal
The system SHALL use the existing RRF fusion score as the primary reranking signal.

#### Scenario: RRF score normalization
- **WHEN** RRF scores are processed
- **THEN** scores are min-max normalized to [0, 1] range within the candidate set

### Requirement: Embedding Similarity Signal
The system SHALL compute cosine similarity between query embedding and document embedding as a reranking signal.

#### Scenario: Real embedding similarity
- **WHEN** real embedding provider is active
- **THEN** embedding_similarity signal contributes to final score per configured weight

#### Scenario: Fake embedding auto-downgrade
- **WHEN** FakeEmbeddingProvider is detected
- **THEN** embedding_similarity weight is set to 0 and redistributed to other signals

### Requirement: Intent Metadata Boost Signal
The system SHALL boost documents whose doc_type matches the classified intent.

#### Scenario: Intent-doc_type match
- **WHEN** intent is REFUND and doc_type is "policy"
- **THEN** intent_metadata_boost score = 1.0 (boost applied)

#### Scenario: Intent-doc_type mismatch
- **WHEN** intent is REFUND and doc_type is "case"
- **THEN** intent_metadata_boost score = 0.0 (no boost)

#### Scenario: No intent available
- **WHEN** intent is None
- **THEN** intent_metadata_boost score = 0.0 for all candidates

### Requirement: Content Quality Signal
The system SHALL score documents based on content length appropriateness and keyword density.

#### Scenario: Optimal length content scores highest
- **WHEN** content length is between 200-800 characters
- **THEN** length_score is at its peak

#### Scenario: Very short content scores lower
- **WHEN** content length < 50 characters
- **THEN** length_score is significantly below peak

#### Scenario: Keyword density scoring
- **WHEN** query contains "退款" and document contains "退款" 3 times
- **THEN** keyword_density is higher than a document containing it 0 times

### Requirement: MultiQueryExpander
The system SHALL generate query variants using LLM to improve recall.

#### Scenario: Successful expansion
- **WHEN** expand("退款没到账", intent="refund") is called with LLM available
- **THEN** returns ["退款没到账", variant_1, variant_2] (3 queries total)

#### Scenario: LLM failure fallback
- **WHEN** LLM call fails (timeout, error, no API key)
- **THEN** returns ["退款没到账"] (original query only) with warning logged

#### Scenario: Variant quality control
- **WHEN** LLM returns variants longer than 50 characters or empty
- **THEN** invalid variants are filtered out

### Requirement: ResultMerger
The system SHALL merge results from multiple query retrievals with deduplication.

#### Scenario: Sum-score merge
- **WHEN** chunk X appears in query_1 results (score=0.3) and query_2 results (score=0.2)
- **THEN** merged score for chunk X = 0.5 (sum)

#### Scenario: Deduplication
- **WHEN** same chunk_id appears in multiple result sets
- **THEN** only one entry in merged results with aggregated score

#### Scenario: Empty result sets
- **WHEN** all result sets are empty
- **THEN** returns empty list

### Requirement: RetrievalTrace extension
The system SHALL record all hybrid reranking signals in the retrieval trace.

#### Scenario: Trace records query variants
- **WHEN** query expansion is used
- **THEN** trace.query_variants contains all query strings used

#### Scenario: Trace records per-result signals
- **WHEN** hybrid reranking completes
- **THEN** trace.rerank_signals contains signal breakdown for each result

#### Scenario: Trace records actual weights used
- **WHEN** weights are auto-adjusted
- **THEN** trace.reranker_weights reflects the adjusted weights

#### Scenario: Trace records embedding provider status
- **WHEN** pipeline completes
- **THEN** trace.has_real_embedding indicates if real embedding was used

### Requirement: Pipeline backward compatibility
The system SHALL maintain backward compatibility with existing callers.

#### Scenario: Existing retrieve_evidence call without intent
- **WHEN** retrieve_evidence() is called without intent parameter
- **THEN** works identically to before (intent=None, no intent boost)

#### Scenario: Existing hybrid_retrieval call without new params
- **WHEN** hybrid_retrieval() is called without enable_query_expansion and reranker_config
- **THEN** uses defaults (expansion enabled, default reranker config)

### Requirement: RerankerConfig from YAML
The system SHALL support loading reranker configuration from YAML files.

#### Scenario: Load default config
- **WHEN** RerankerConfig.default() is called
- **THEN** returns config with balanced weights (0.40, 0.25, 0.20, 0.15)

#### Scenario: Load from YAML file
- **WHEN** RerankerConfig.from_yaml("config/reranker.yaml") is called
- **THEN** loads and validates weights from file

#### Scenario: Invalid YAML weights
- **WHEN** YAML weights sum to 0.8 (not 1.0)
- **THEN** raises ValueError with descriptive message

### Requirement: Graceful degradation
The system SHALL degrade gracefully when components are unavailable.

#### Scenario: No LLM for query expansion
- **WHEN** no LLM API key configured
- **THEN** query expansion is skipped, pipeline continues with original query

#### Scenario: No real embedding provider
- **WHEN** FakeEmbeddingProvider is the only available provider
- **THEN** reranker runs with embedding signal weight = 0, other signals adjusted

#### Scenario: RerankerConfig file missing
- **WHEN** config/reranker.yaml does not exist
- **THEN** falls back to RerankerConfig.default()
