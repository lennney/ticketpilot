## ADDED Requirements

### Requirement: EmbeddingProvider interface
The system SHALL define EmbeddingProvider as an abstract interface with method: embed(text: str) -> list[float].

#### Scenario: EmbeddingProvider interface defined
- **WHEN** EmbeddingProvider is inspected
- **THEN** it has embed(text: str) -> list[float] method signature

### Requirement: FakeEmbeddingProvider
The system SHALL implement FakeEmbeddingProvider that returns random vectors of 1536 dimensions.

#### Scenario: Fake embedding generation
- **WHEN** FakeEmbeddingProvider.embed("test") is called
- **THEN** returns a list of 1536 float values

#### Scenario: Fake embeddings are deterministic per text
- **WHEN** FakeEmbeddingProvider.embed("test") is called twice
- **THEN** returns identical vectors (seeded by text hash)

### Requirement: SmallEmbeddingProvider
The system SHALL implement SmallEmbeddingProvider using text-embedding-3-small (placeholder returning fake for MVP).

#### Scenario: Small embedding generation
- **WHEN** SmallEmbeddingProvider.embed("test") is called
- **THEN** returns a list of 1536 float values

### Requirement: QualityEmbeddingProvider
The system SHALL implement QualityEmbeddingProvider using text-embedding-3-large (placeholder returning 3072-dim fake for MVP).

#### Scenario: Quality embedding generation
- **WHEN** QualityEmbeddingProvider.embed("test") is called
- **THEN** returns a list of 3072 float values (placeholder)

### Requirement: KeywordRetrieval top-k return
The system SHALL return top-k keyword search results from PostgreSQL full-text search.

#### Scenario: Keyword retrieval returns top-10
- **WHEN** keyword retrieval is called with k=10
- **THEN** returns up to 10 results sorted by ts_rank descending

#### Scenario: Keyword retrieval includes scores
- **WHEN** keyword retrieval returns results
- **THEN** each result includes ts_rank score

### Requirement: VectorRetrieval top-k return
The system SHALL return top-k vector search results from pgvector HNSW.

#### Scenario: Vector retrieval returns top-10
- **WHEN** vector retrieval is called with k=10
- **THEN** returns up to 10 results sorted by cosine similarity descending

#### Scenario: Vector retrieval includes scores
- **WHEN** vector retrieval returns results
- **THEN** each result includes cosine similarity score

### Requirement: RRF fusion input
The system SHALL perform RRF fusion combining keyword_rank and vector_rank.

#### Scenario: RRF fusion requires keyword_rank
- **WHEN** RRF fusion is called
- **THEN** keyword results with rank positions are provided

#### Scenario: RRF fusion requires vector_rank
- **WHEN** RRF fusion is called
- **THEN** vector results with rank positions are provided

### Requirement: RRF algorithm with k=60
The system SHALL implement RRF with k=60 constant.

#### Scenario: RRF fusion formula
- **WHEN** RRF fusion is called with k=60
- **THEN** score = sum(1 / (60 + rank)) for each ranker

#### Scenario: RRF combines both retrievers
- **WHEN** doc appears in both keyword and vector results
- **THEN** RRF score includes contribution from both rankers

### Requirement: HybridRetrievalPipeline
The system SHALL implement HybridRetrievalPipeline that:
1. Accepts query text
2. Generates query embedding
3. Calls keyword retrieval
4. Calls vector retrieval
5. Applies RRF fusion
6. Returns fused results

#### Scenario: Pipeline processes query
- **WHEN** HybridRetrievalPipeline.retrieve("如何退货？", k=10) is called
- **THEN** returns RetrievalResult with fused top-10

#### Scenario: Pipeline returns evidence
- **WHEN** HybridRetrievalPipeline.retrieve is called
- **THEN** results include content, doc_type, source_id, and scores

### Requirement: RetrievalTrace schema
The system SHALL define RetrievalTrace with fields: id (UUID), query (str), query_embedding (list[float]), keyword_results (JSON), vector_results (JSON), fused_results (JSON), final_evidence (JSON), retrieved_doc_ids (list[UUID]), retrieval_latency_ms (int), created_at (datetime).

#### Scenario: RetrievalTrace validation
- **WHEN** RetrievalTrace is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: RetrievalTrace captures full pipeline
- **WHEN** retrieval pipeline completes
- **THEN** RetrievalTrace contains query, keyword_results, vector_results, fused_results

### Requirement: RetrievalTrace records doc_type and source ids
The system SHALL record doc_type and source document IDs in retrieval traces.

#### Scenario: Trace includes doc_type
- **WHEN** retrieval trace is created
- **THEN** each result includes doc_type (FAQ/POLICY/CASE)

#### Scenario: Trace includes source ids
- **WHEN** retrieval trace is created
- **THEN** retrieved_doc_ids contains all source document UUIDs

### Requirement: HNSW index configuration
The system SHALL use HNSW index with m=16, ef_construction=200.

#### Scenario: HNSW index exists
- **WHEN** database is checked for vector index
- **THEN** idx_chunks_embedding_hnsw exists

#### Scenario: PostgreSQL FTS index exists
- **WHEN** database is checked for text index
- **THEN** idx_chunks_content_fts exists using gin
