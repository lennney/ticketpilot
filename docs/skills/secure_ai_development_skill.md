# Secure AI Development Skill

## Purpose

Prevent secret leakage, enforce provider boundaries, and maintain safe defaults in an AI-assisted development project. This skill covers secret handling (no API keys in repository), provider abstraction for safe swapping between fake and real implementations, local-only configuration, and safe defaults that prevent accidental production behavior.

## When to Use

- Setting up a new AI project with external provider dependencies
- Adding API keys, tokens, or other secrets to a project
- Implementing provider abstractions (embeddings, LLMs, etc.) that may later connect to real services
- Configuring environment variables, .env files, or runtime settings
- Reviewing code for secrets before committing
- Setting up quality gate for secret detection

## Required Inputs

- List of external providers the system may need (LLM, embeddings, database, etc.)
- Environment configuration approach (.env files, environment variables, config classes)
- Provider interface definitions (abstract classes or protocols)
- Quality gate script location

## Allowed Scope

- Creating .env.example templates with placeholder values (no real secrets)
- Implementing abstract provider interfaces with fake/deterministic implementations for MVP
- Adding provider selection logic (fake vs real) via environment configuration
- Implementing environment variable validation (required vars, format checks)
- Adding secret detection to the quality gate
- Documenting required environment variables without revealing values
- Using local-only configuration for MVP development

## Forbidden Scope

- Do NOT commit real API keys, tokens, passwords, or secrets to the repository
- Do NOT hardcode secrets in source code, tests, or configuration files
- Do NOT add .env files (with real values) to the repository (add to .gitignore)
- Do NOT implement real LLM or embedding provider integrations without explicit design review and security assessment
- Do NOT expose internal provider interfaces or credentials through logs, error messages, or debug output
- Do NOT skip secret detection in the quality gate

## Step-by-Step Procedure

1. **Set up environment configuration**
   - Create `.env.example` with ALL required environment variables and clear placeholder values
   - Add `.env` to `.gitignore` (never commit real secrets)
   - Document each variable: purpose, format, whether required, what happens if missing

2. **Define provider boundaries with abstract interfaces**
   - Create abstract base classes or protocols for each external provider type:
     - Embedding provider: Abstract class with `embed(text) -> list[float]` method
     - Draft generation provider: Abstract class with `generate(ticket_output) -> DraftReply` method
   - Keep interfaces small and focused (single responsibility)
   - Document what each provider is expected to do and what guarantees it provides

3. **Implement fake/deterministic providers first**
   - FakeEmbeddingProvider: Deterministic, SHA-256 seeded pseudo-random vectors
   - FakeDraftProvider: Template-based, no external dependencies, no API keys needed
   - These prove the pipeline mechanics without any external service dependency
   - Label fake providers clearly: "PIPELINE VERIFICATION ONLY" or "MVP only — no production use"

4. **Add provider selection mechanism**
   - Use environment variables or config classes to select between fake and real providers
   - Default to fake providers (safe default, no API keys required)
   - Real providers require explicit configuration and are never the default

5. **Add secret detection to quality gate**
   - Add a stage to the quality gate script that scans for potential secrets:
     - Pattern: `sk-[a-zA-Z0-9]{20,}` (OpenAI-style API keys) and similar patterns for other providers
     - Exclude: `.git/`, virtual environments, `.env.example`
   - The quality gate must fail if any potential secret is detected

6. **Validate environment at startup (optional for MVP)**
   - If a real provider is selected, validate that all required environment variables are present
   - If required variables are missing, log a clear error message and fall back to fake provider (safe default)
   - Never crash with an unhelpful key error

7. **Audit for secrets before every commit**
   - Run the quality gate (which includes secret detection)
   - Scan staged files manually: check for hardcoded keys, tokens, passwords
   - Check test fixtures and example data for accidental secrets

8. **Document provider strategy**
   - Document which providers are fake vs real
   - Document the interface mechanisms so real providers can be added without pipeline changes
   - Document what each fake provider can and cannot verify

## Acceptance Checklist

- [ ] `.env.example` exists with all required variables and placeholder values
- [ ] `.env` is in `.gitignore`
- [ ] No real API keys, tokens, or secrets in the repository
- [ ] Abstract provider interfaces defined for embedding, draft generation, and any external services
- [ ] Fake/deterministic provider implementations exist as the default (safe default)
- [ ] Real provider selection requires explicit configuration (never default)
- [ ] Quality gate includes secret detection stage
- [ ] Secret detection pattern excludes legitimate files (.gitignore, virtual envs, examples)
- [ ] Provider strategy documented in technical documentation
- [ ] No provider credentials exposed in logs, error messages, or test output

## Common Failure Modes

- **Accidentally committing .env**: Always check `git status --short` before committing. If .env appears, add it to .gitignore immediately.
- **Hardcoding a test API key**: A test key in a test file is still a secret in the repository. Use environment variables or placeholder values even for test keys.
- **Logging provider credentials**: If a provider connection fails and the error message includes the API key, the key is now in your logs. Sanitize error messages.
- **Defaulting to real provider**: If the code tries to connect to a real LLM provider when no API key is configured, it will either crash or leak credentials in the error. Default to fake providers; require explicit opt-in for real providers.
- **Missing .env.example variables**: If a new developer clones the repo and the .env.example doesn't document all required variables, they cannot run the project. Keep .env.example in sync with actual config requirements.
- **Secret detection false positives**: A commit message or docstring that mentions "sk-..." could trigger the secret scan. Use exclusion patterns carefully, but do not exclude entire file types that could contain secrets.
- **Fake provider not labeled as fake**: If a fake provider is not clearly labeled, future developers may confuse it with a real implementation. Use explicit class names (FakeEmbeddingProvider, not EmbeddingProvider) and docstring warnings.

## Reusable Claude Code Prompt Template

```
I need to set up secure provider configuration for an AI project. Walk through:

1. **Environment config** — Create .env.example with all required variables (placeholder values, no real secrets). Add .env to .gitignore.

2. **Provider interfaces** — Define abstract classes/protocols for each external service:
   - Embedding provider: abstract class with `embed(text) -> list[float]`
   - Generation provider: abstract class with `generate(input) -> Output`
   - Keep interfaces small (single responsibility)

3. **Fake providers first** — Implement deterministic, zero-dependency fake providers:
   - No API keys, no network, no external calls
   - Label clearly: "PIPELINE VERIFICATION ONLY" or "MVP only"
   - These prove pipeline mechanics without production dependencies

4. **Provider selection** — Default to fake providers. Real providers require explicit config.
   - Use environment variable or config class
   - Validate required vars when real provider is selected
   - Fall back to fake provider gracefully on missing config

5. **Secret detection** — Add to quality gate:
   - Scan for `sk-` patterns and similar
   - Exclude .git, virtual envs, .env.example
   - Gate fails on detection

6. **Audit** — Before every commit:
   - Run quality gate (includes secret detection)
   - Check staged files for hardcoded secrets
   - Verify no credentials in logs or error messages

Critical rules:
- Never commit real secrets
- Never default to real providers
- Label fake providers clearly
- Sanitize error messages
- Keep .env.example in sync
```

## TicketPilot Example

TicketPilot implements all secure development practices:

**Environment config**: `.env.example` documents all required environment variables (database connection, provider selection) with placeholder values. `.env` is in `.gitignore`.

**Provider interfaces**:
- `EmbeddingProvider` abstract class with `embed(text) -> NDArray` in `src/ticketpilot/retrieval/providers/embedding.py`
- `AbstractDraftProvider` abstract class with `generate(ticket_output) -> DraftReply` in `src/ticketpilot/drafting/provider.py`

**Fake providers**:
- `FakeEmbeddingProvider`: SHA-256 seeded pseudo-random 384-dim vectors. Labeled "PIPELINE VERIFICATION ONLY — no semantic meaning."
- `FakeDraftProvider`: Template-based Chinese draft generator. Zero external dependencies. Labeled as MVP-only.
- Both are default providers. Real providers require explicit configuration.

**Provider selection**: The system defaults to fake providers. Selecting a real provider requires environment variable configuration. If a real provider is selected but not configured, the system gracefully falls back to the fake provider.

**Quality gate secret detection**: Stage 5 scans for `sk-[a-zA-Z0-9]{20,}` pattern, excluding `.git/`, `.venv/`, `.venv_broken/`, and `.env.example`.

**No real secrets in repository**: Verified by quality gate. All provider implementations in the MVP are fake (zero external dependencies, zero API keys required).
