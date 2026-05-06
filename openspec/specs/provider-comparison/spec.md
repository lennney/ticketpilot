# provider-comparison Specification

## Purpose
TBD - created by archiving change add-real-llm-provider-comparison. Update Purpose after archive.
## Requirements
### Requirement: Provider Types

The system SHALL support multiple LLM providers:

- `fake` (default): Deterministic, no network, no API key
- `openai_compatible`: Opt-in via environment variable

Each provider implements the `LLMProvider` ABC.

#### Scenario: Create fake provider
- **WHEN** create_llm_provider() is called with no TICKETPILOT_LLM_PROVIDER env var
- **THEN** FakeLLMProvider is returned

#### Scenario: Create openai_compatible provider
- **WHEN** create_llm_provider() is called with TICKETPILOT_LLM_PROVIDER=openai_compatible and all required env vars
- **THEN** OpenAICompatibleProvider is returned

---

### Requirement: Env-Only Configuration

The system SHALL activate real provider via environment variables only. No code-level configuration.

Required env vars for `openai_compatible`:

- `TICKETPILOT_LLM_PROVIDER=openai_compatible`
- `TICKETPILOT_LLM_BASE_URL`
- `TICKETPILOT_LLM_API_KEY`
- `TICKETPILOT_LLM_MODEL` (default: `gpt-4o-mini`)
- `TICKETPILOT_LLM_TIMEOUT_SECONDS` (default: 30)
- `TICKETPILOT_LLM_MAX_TOKENS` (default: 512)
- `TICKETPILOT_LLM_TEMPERATURE` (default: 0.3)

#### Scenario: Missing env vars
- **WHEN** TICKETPILOT_LLM_PROVIDER=openai_compatible but TICKETPILOT_LLM_BASE_URL or TICKETPILOT_LLM_API_KEY is missing
- **THEN** ValueError is raised with clear message indicating missing vars

---

### Requirement: Clear Error on Missing Env

The system SHALL raise ValueError with clear message when required env vars are missing.

#### Scenario: Missing API key
- **WHEN** TICKETPILOT_LLM_PROVIDER=openai_compatible but TICKETPILOT_LLM_API_KEY is not set
- **THEN** ValueError is raised with message "TICKETPILOT_LLM_API_KEY is required"

---

### Requirement: No Secret Exposure

The system SHALL never expose API key in logs, reports, or repr output.

#### Scenario: API key not in repr
- **WHEN** repr(provider) is called on OpenAICompatibleProvider with api_key="sk-..."
- **THEN** "sk-" does not appear in the output

#### Scenario: API key not in trace
- **WHEN** trace dict is retrieved from OpenAICompatibleProvider draft generation
- **THEN** TICKETPILOT_LLM_API_KEY value does not appear in the trace

---

### Requirement: Safe Fallback

The system SHALL return safe fallback DraftReply on API error (network, timeout, invalid JSON).

#### Scenario: Network error triggers safe fallback
- **WHEN** OpenAICompatibleProvider API call fails with network error
- **THEN** safe fallback DraftReply is returned with must_human_review=True

#### Scenario: Invalid JSON triggers safe fallback
- **WHEN** OpenAICompatibleProvider API returns non-JSON response
- **THEN** safe fallback DraftReply is returned with must_human_review=True

---

### Requirement: Offline Comparison Runner

The system SHALL provide a runner script that compares fake and real provider outputs.

#### Scenario: Runner without real provider
- **WHEN** runner script is executed without TICKETPILOT_LLM_PROVIDER=openai_compatible
- **THEN** FakeLLMProvider baseline rows are generated
- **AND** real provider status is "not configured"

#### Scenario: Runner with real provider
- **WHEN** runner script is executed with TICKETPILOT_LLM_PROVIDER=openai_compatible and all required env vars
- **THEN** both fake and real provider rows are generated

---

### Requirement: Fixture Set

The system SHALL provide a synthetic fixture set of 25 cases covering diverse scenarios.

#### Scenario: Fixture covers ordinary product consulting
- **WHEN** fixture is loaded
- **THEN** it includes cases for ordinary product consulting scenario

#### Scenario: Fixture covers refund
- **WHEN** fixture is loaded
- **THEN** it includes cases for refund scenario

#### Scenario: Fixture covers return/exchange
- **WHEN** fixture is loaded
- **THEN** it includes cases for return/exchange scenario

#### Scenario: Fixture covers logistics
- **WHEN** fixture is loaded
- **THEN** it includes cases for logistics scenario

#### Scenario: Fixture covers complaint
- **WHEN** fixture is loaded
- **THEN** it includes cases for complaint scenario

#### Scenario: Fixture covers privacy risk
- **WHEN** fixture is loaded
- **THEN** it includes cases for privacy risk scenario

#### Scenario: Fixture covers account security risk
- **WHEN** fixture is loaded
- **THEN** it includes cases for account security risk scenario

#### Scenario: Fixture covers legal-ish complaint
- **WHEN** fixture is loaded
- **THEN** it includes cases for legal-ish complaint scenario

#### Scenario: Fixture covers compensation risk
- **WHEN** fixture is loaded
- **THEN** it includes cases for compensation risk scenario

#### Scenario: Fixture covers evidence insufficient
- **WHEN** fixture is loaded
- **THEN** it includes cases for evidence insufficient scenario

#### Scenario: Fixture covers policy conflict
- **WHEN** fixture is loaded
- **THEN** it includes cases for policy conflict scenario

#### Scenario: Fixture covers technical issue
- **WHEN** fixture is loaded
- **THEN** it includes cases for technical issue scenario

---

### Requirement: Markdown Report

The system SHALL generate a comparison report with scope boundary and no overclaims.

#### Scenario: Report contains boundary wording
- **WHEN** markdown report is generated
- **THEN** "local demo / portfolio prototype" appears in the report

#### Scenario: Report does not contain overclaims
- **WHEN** markdown report is generated
- **THEN** "benchmark" does not appear in the report except in boundary/limitation context

---

### Requirement: Mock Unit Tests

The system SHALL provide mock unit tests that do not call network.

#### Scenario: Mock API returns DraftReply
- **WHEN** monkeypatched HTTP client returns valid JSON DraftReply
- **AND** generate_draft is called
- **THEN** DraftReply is returned with provider metadata

---

### Requirement: Integration Tests

The system SHALL provide runner integration tests.

#### Scenario: Runner generates fake baseline
- **WHEN** runner script is executed without TICKETPILOT_LLM_PROVIDER=openai_compatible
- **THEN** row JSON with fake provider is generated

