# draft-generation Specification

## ADDED Requirements

### Requirement: LLM Provider Interface
The system SHALL define an abstract LLMProvider interface with a generate(prompt: str) -> str method and a provider_id property.

#### Scenario: LLMProvider is abstract
- **WHEN** LLMProvider is inspected
- **THEN** it is an abstract base class and cannot be instantiated directly

#### Scenario: LLMProvider declares generate signature
- **WHEN** LLMProvider abstract methods are inspected
- **THEN** it has generate method with signature (prompt: str) -> str

#### Scenario: LLMProvider has provider_id property
- **WHEN** provider_id is accessed on any concrete subclass
- **THEN** it returns a non-empty string identifying the provider

### Requirement: FakeLLMProvider
The system SHALL implement FakeLLMProvider as a deterministic provider that returns template-based output without calling any external API.

#### Scenario: FakeLLMProvider constructs successfully
- **WHEN** FakeLLMProvider is instantiated
- **THEN** it is an instance of LLMProvider

#### Scenario: FakeLLMProvider is deterministic
- **WHEN** FakeLLMProvider.generate is called twice with identical inputs
- **THEN** both outputs are identical strings

#### Scenario: FakeLLMProvider requires no network
- **WHEN** FakeLLMProvider.generate is called
- **THEN** no HTTP requests, no API calls, and no database queries are made

#### Scenario: FakeLLMProvider is default provider
- **WHEN** no real provider is configured
- **THEN** FakeLLMProvider is used by default

### Requirement: Evidence-Grounded Generation
The system SHALL generate draft replies grounded in retrieved EvidenceCandidate objects.

#### Scenario: Draft uses provided evidence
- **WHEN** evidence candidates are provided to draft generation
- **THEN** draft_text references content from the evidence candidates

#### Scenario: No factual claims without evidence
- **WHEN** a draft contains a factual or policy statement
- **THEN** the statement has a corresponding citation to an evidence candidate

#### Scenario: Generic greetings do not require citations
- **WHEN** the draft contains "您好" or similar greeting
- **THEN** the greeting is exempt from citation requirements

### Requirement: Citation-Required Output
The system SHALL produce structured Citation entries linking statements to evidence chunk_ids.

#### Scenario: Citations reference valid chunk_ids
- **WHEN** a draft includes citations
- **THEN** each citation.chunk_id matches a provided EvidenceCandidate.chunk_id

#### Scenario: Inline citation notation
- **WHEN** a draft text references evidence
- **THEN** the reference uses [chunk_id] notation inline in draft_text

### Requirement: Structured Draft Output
The system SHALL produce DraftReply with provider_id, guard_results, and escalation_reason fields.

#### Scenario: DraftReply includes provider_id
- **WHEN** DraftReply is generated
- **THEN** provider_id is a non-empty string identifying which provider generated it

#### Scenario: DraftReply includes guard_results
- **WHEN** DraftReply is generated and guard check runs
- **THEN** guard_results is populated with GuardResult

#### Scenario: DraftReply includes escalation_reason
- **WHEN** must_human_review is True
- **THEN** escalation_reason explains why human review is required

### Requirement: Safe Fallback
The system SHALL generate a safe fallback draft when no evidence is available.

#### Scenario: Fallback on empty evidence
- **WHEN** generate is called with an empty evidence list
- **THEN** returns DraftReply with fallback_reason="no_evidence"

#### Scenario: Fallback forces human review
- **WHEN** fallback is triggered
- **THEN** must_human_review is True

#### Scenario: Fallback is in Chinese
- **WHEN** fallback is triggered
- **THEN** draft_text is a Chinese message indicating insufficient information

### Requirement: Provider Identity in Trace
The system SHALL record which provider generated each draft.

#### Scenario: Provider identity in DraftReply
- **WHEN** any provider generates a draft
- **THEN** provider_id in DraftReply matches the provider's provider_id

#### Scenario: Provider identity in evaluation
- **WHEN** draft evaluation runs
- **THEN** the evaluation report records which provider was used

### Requirement: No Auto-Send
The system SHALL NOT contain any code path that sends draft replies to customers.

#### Scenario: No send method in generation
- **WHEN** LLMProvider interface and all implementations are inspected
- **THEN** no method exists for dispatching or sending replies

#### Scenario: No send code path in generate_draft
- **WHEN** generate_draft() is called
- **THEN** the return value is always DraftReply, never a send/dispatch action

### Requirement: No Policy Decision by LLM
The system SHALL prohibit LLM from determining policy, refund, compensation, legal, or account-security actions.

#### Scenario: Prompt constrains LLM
- **WHEN** a prompt is built for LLM generation
- **THEN** the system prompt instructs the LLM not to make policy decisions

#### Scenario: Post-generation guard catches policy promises
- **WHEN** a draft contains policy promises (refund amount, legal action, account change)
- **THEN** the claim guard detects and flags them

### Requirement: Deterministic Provider for Tests
The system SHALL provide FakeLLMProvider usable in all unit and integration tests without network access.

#### Scenario: Unit tests use FakeLLMProvider
- **WHEN** unit tests run
- **THEN** FakeLLMProvider is the default provider and requires no configuration

#### Scenario: Integration tests use FakeLLMProvider
- **WHEN** integration tests run with DB but without real API keys
- **THEN** the full pipeline uses FakeLLMProvider and completes successfully
