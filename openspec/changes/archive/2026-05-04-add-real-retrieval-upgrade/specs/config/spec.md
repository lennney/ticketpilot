## ADDED Requirements

### Requirement: EMBEDDING_PROVIDER environment variable
The system SHALL read EMBEDDING_PROVIDER to select the active embedding provider.
Valid values: "fake" (default), "openai" (OpenAI-compatible API).
Unknown values SHALL fall back to fake with a warning.

#### Scenario: Default provider
- **GIVEN** EMBEDDING_PROVIDER is not set
- **WHEN** the provider factory resolves the provider
- **THEN** FakeEmbeddingProvider is returned

#### Scenario: Real provider selected
- **GIVEN** EMBEDDING_PROVIDER=openai
- **WHEN** the provider factory resolves the provider
- **THEN** RealEmbeddingProvider is returned

#### Scenario: Unknown provider value
- **GIVEN** EMBEDDING_PROVIDER=unknown
- **WHEN** the provider factory resolves the provider
- **THEN** a warning is logged
- **AND** FakeEmbeddingProvider is returned as safe default

### Requirement: EMBEDDING_MODEL environment variable
The system SHALL read EMBEDDING_MODEL to select the embedding model name.
For OpenAI-compatible providers, this maps to the model parameter in the API request.
Default: "text-embedding-3-small".

#### Scenario: Model selected
- **GIVEN** EMBEDDING_MODEL=text-embedding-3-small
- **WHEN** RealEmbeddingProvider is initialized
- **THEN** the model name is passed to the API

### Requirement: EMBEDDING_DIM environment variable
The system SHALL read EMBEDDING_DIM to specify the expected embedding vector dimension.
Default: 384 (matching FakeEmbeddingProvider).
MUST match the actual provider output dimension.

#### Scenario: Default dimension
- **GIVEN** EMBEDDING_DIM is not set
- **WHEN** FakeEmbeddingProvider is initialized
- **THEN** dimension=384

#### Scenario: Real provider dimension
- **GIVEN** EMBEDDING_DIM=768
- **WHEN** RealEmbeddingProvider is initialized
- **THEN** the dimension contract is set to 768

### Requirement: EMBEDDING_BASE_URL environment variable
The system SHALL read EMBEDDING_BASE_URL to specify the API endpoint for OpenAI-compatible providers.
Default: "https://api.openai.com/v1".
MUST support custom endpoints for local or alternative embedding services.

#### Scenario: Custom base URL
- **GIVEN** EMBEDDING_BASE_URL=http://localhost:1234/v1
- **WHEN** RealEmbeddingProvider is initialized
- **THEN** API requests use the custom base URL

### Requirement: EMBEDDING_API_KEY environment variable
The system SHALL read EMBEDDING_API_KEY from environment for API authentication.
This MUST NOT be read from a config file in the repository.
The variable name MAY appear in .env.example but MUST NOT contain a real value.

#### Scenario: API key from environment
- **GIVEN** EMBEDDING_API_KEY is set in the shell environment
- **WHEN** RealEmbeddingProvider is initialized
- **THEN** the key is used for API authentication

#### Scenario: .env.example contains only variable name
- **GIVEN** the .env.example file
- **WHEN** inspected
- **THEN** it contains "EMBEDDING_API_KEY=" with no real key value

### Requirement: EMBEDDING_BATCH_SIZE environment variable
The system SHALL read EMBEDDING_BATCH_SIZE to control how many texts are sent per API request.
Default: 10.
Minimum: 1.
This is only used when batch embedding is implemented.

#### Scenario: Batch size configured
- **GIVEN** EMBEDDING_BATCH_SIZE=20
- **WHEN** batch embedding is used
- **THEN** at most 20 texts are sent per API request

### Requirement: .env.example variable listing
The .env.example file SHALL include the following variable names with safe defaults:

```
EMBEDDING_PROVIDER=fake
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=384
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_BATCH_SIZE=10
```

No real API keys or secrets SHALL be present in .env.example.

#### Scenario: .env.example contains no secrets
- **GIVEN** the .env.example file
- **WHEN** inspected for real API keys
- **THEN** no real keys or secrets are found

### Requirement: Config summary table
The system SHALL support the following configuration environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| EMBEDDING_PROVIDER | No | "fake" | Provider name: "fake" or "openai" |
| EMBEDDING_MODEL | No | "text-embedding-3-small" | Model name for real provider |
| EMBEDDING_DIM | No | 384 | Expected vector dimension |
| EMBEDDING_BASE_URL | No | "https://api.openai.com/v1" | API endpoint base URL |
| EMBEDDING_API_KEY | Conditional | — | API key (required for real provider) |
| EMBEDDING_BATCH_SIZE | No | 10 | Batch size for batch embedding |

#### Scenario: All config variables have safe defaults
- **GIVEN** no EMBEDDING_* environment variables are set
- **WHEN** the provider factory resolves configuration
- **THEN** EMBEDDING_PROVIDER defaults to "fake"
- **AND** EMBEDDING_DIM defaults to 384
