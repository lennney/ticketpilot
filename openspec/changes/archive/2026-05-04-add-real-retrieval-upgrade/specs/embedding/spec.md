## ADDED Requirements

### Requirement: EmbeddedProvider abstract interface
The system SHALL define or maintain an abstract EmbeddingProvider interface with method: embed(text: str) -> list[float].
The interface MAY be an existing ABC or Protocol in the retrieval.providers module.

#### Scenario: EmbeddingProvider interface exists
- **GIVEN** the retrieval.providers module
- **WHEN** EmbeddingProvider is imported
- **THEN** it defines embed(text: str) -> list[float]

### Requirement: FakeEmbeddingProvider remains unchanged as default
The existing FakeEmbeddingProvider SHALL remain the default provider.
Its behavior SHALL NOT change: deterministic 384-dim SHA-256 hash vectors.
All existing tests using FakeEmbeddingProvider SHALL continue to pass without modification.

#### Scenario: FakeEmbeddingProvider is default
- **GIVEN** no EMBEDDING_PROVIDER environment variable is set
- **WHEN** the provider factory resolves the provider
- **THEN** it returns FakeEmbeddingProvider

#### Scenario: FakeEmbeddingProvider output unchanged
- **GIVEN** FakeEmbeddingProvider is instantiated
- **WHEN** embed("test") is called twice
- **THEN** both calls return identical 384-dim vectors

### Requirement: RealEmbeddingProvider as opt-in
The system SHALL implement a RealEmbeddingProvider that calls an OpenAI-compatible embedding API.
The provider SHALL be opt-in, selected via EMBEDDING_PROVIDER environment variable.

#### Scenario: RealEmbeddingProvider selected by env
- **GIVEN** EMBEDDING_PROVIDER=openai is set
- **AND** EMBEDDING_API_KEY is set in environment
- **WHEN** the provider factory resolves the provider
- **THEN** it returns RealEmbeddingProvider configured with the given model and base URL

#### Scenario: RealEmbeddingProvider without API key
- **GIVEN** EMBEDDING_PROVIDER=openai is set
- **AND** EMBEDDING_API_KEY is NOT set
- **WHEN** RealEmbeddingProvider is instantiated
- **THEN** it SHALL raise a clear configuration error

#### Scenario: RealEmbeddingProvider dimension contract
- **GIVEN** RealEmbeddingProvider is configured with EMBEDDING_DIM=768
- **WHEN** embed("test") returns a vector
- **THEN** the vector length SHALL equal EMBEDDING_DIM
- **AND** a dimension mismatch SHALL raise an error

### Requirement: Provider metadata
Every provider SHALL expose metadata: provider_name, model_name, dimension.
FakeEmbeddingProvider SHALL return provider_name="fake", model_name="sha-256", dimension=384.

#### Scenario: Provider metadata accessible
- **GIVEN** any EmbeddingProvider instance
- **WHEN** metadata is accessed
- **THEN** it returns provider_name, model_name, and dimension

### Requirement: Dimension mismatch fails loudly
If the configured EMBEDDING_DIM does not match the existing index dimension, any embedding operation SHALL fail with a clear error message.
The system SHALL NOT silently produce mismatched-dimension vectors.

#### Scenario: Dimension mismatch detected
- **GIVEN** an existing index with dimension 384
- **AND** EMBEDDING_DIM=768 is configured
- **WHEN** a rebuild or embedding operation is attempted
- **THEN** the system SHALL raise an error: "Dimension mismatch: configured EMBEDDING_DIM=768 but existing index uses 384. Trigger index rebuild."

### Requirement: Network tests not in default CI
Tests for RealEmbeddingProvider SHALL use mocked HTTP responses.
No test SHALL require a live embedding API endpoint in default pytest runs.
Tests that require network SHALL use a pytest marker that excludes them from default CI.

#### Scenario: Real provider unit test with mock
- **GIVEN** a mocked HTTP endpoint
- **WHEN** RealEmbeddingProvider.embed("test") is called
- **THEN** it returns the mocked vector response

#### Scenario: No live network in default tests
- **GIVEN** default pytest configuration
- **WHEN** the provider test suite runs
- **THEN** no HTTP request is made to an external embedding API

### Requirement: No API key committed
No file in the repository SHALL contain a real embedding API key.
The .env.example MAY list variable names but SHALL NOT contain real secrets.
The .env.local file SHALL remain in .gitignore.

#### Scenario: Secret scan clean
- **GIVEN** the repository
- **WHEN** secret scan runs
- **THEN** no embedding API keys are detected

### Requirement: Batch embedding method
The EmbeddingProvider SHALL expose an embed_batch(texts: list[str]) -> list[list[float]] method for batch embedding.
The batch size SHALL be configurable via EMBEDDING_BATCH_SIZE.

#### Scenario: Batch embedding
- **GIVEN** a provider with batch support
- **WHEN** embed_batch(["a", "b", "c"]) is called
- **THEN** it returns a list of vectors equal in length to the input list
