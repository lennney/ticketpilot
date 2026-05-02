# Stage 1C: Evidence-Grounded Draft Generation

## Stage Goal

Add an optional draft generation stage to TicketPilot that produces evidence-grounded Chinese customer service reply drafts, with every factual claim explicitly linked to its supporting evidence chunk via numbered citations, without using any real LLM.

## Business Problem Addressed

After pipeline processing (intake -> classification -> risk assessment -> retrieval), TicketPilot has a fully analyzed ticket with evidence candidates, but no actionable reply. Customer support agents must manually compose replies by reading the evidence and synthesizing a response. Draft generation automates the first draft, giving agents a head start:

- Reduces reply composition time from minutes to seconds
- Ensures every factual claim is grounded in retrieved evidence (citations)
- Flags unsupported claims automatically via the CitationValidator
- Provides a confidence score so agents can prioritize which drafts need the most attention
- High-risk and no-evidence tickets produce safe fallback messages, never fabricated promises

## Key Design Decisions

### 1. Optional workflow (NOT part of default pipeline contract)

**Decision**: Draft generation is exposed as a standalone `generate_draft(ticket_output)` function and an optional `run_pipeline_with_draft(raw_ticket)` entrypoint. The existing `intake_risk_pipeline()` return type (`TicketOutput`) is unchanged.

**Rationale**: Prevents the draft module from creating a breaking change in any downstream consumer (Streamlit, API, tests). Existing code that calls `intake_risk_pipeline()` continues to work without modification. An earlier design considered changing the return type to a `PipelineResult` wrapper but was rejected because it would break ~30 test assertions and `isinstance()` checks.

### 2. FakeDraftProvider (deterministic, template-based)

**Decision**: The only MVP draft provider implementation is `FakeDraftProvider` — a deterministic, template-based generator that constructs Chinese replies from evidence candidates without any LLM calls.

**Rationale**: Zero external dependencies (no API keys, no network, no latency). Deterministic output enables reliable testing. The template is simple: opening ("您好...") -> evidence body with `[N]` citation markers -> closing. The `AbstractDraftProvider` interface is designed so a real LLM provider can replace it without changing the pipeline.

### 3. CitationValidator as a deterministic guardrail

**Decision**: `CitationValidator` performs regex-based checks: citation existence (every `[N]` has a matching Citation) and claim-coverage scan (Chinese claim keywords like 根据, 按照, 可以 without a citation marker in the same sentence are flagged).

**Rationale**: Lightweight, deterministic, zero-LLM. Catches obvious citation errors (mismatched `[N]` markers) and potential unsupported claims. Known limitations: regex patterns are imprecise — false positives and negatives expected with real Chinese text. A future LLM-based semantic claim verifier can replace the regex scanner.

### 4. `DraftedTicketResult` wrapper schema

**Decision**: A narrow wrapper combining `ticket_output: TicketOutput` + `draft_reply: DraftReply`, returned by `run_pipeline_with_draft()`.

**Rationale**: Clean separation — the pipeline's default return type is unchanged, while the optional workflow returns a composite result. No additional fields, no pipeline-result abstraction that could replace `TicketOutput`.

### 5. Safety guarantees for no-evidence, high-risk, and error scenarios

**Decision**: Three safety paths:
- **No evidence**: Safe fallback Chinese message with no policy promises ("根据现有信息，无法确认具体政策条款，建议转人工处理"), confidence=0.0, no citations.
- **High risk**: Draft generated but `must_human_review=True`, confidence capped at 0.5.
- **Exception**: Safe fallback draft returned (never crashes), `fallback_reason="generation_error"`.

**Rationale**: The system must never fabricate policy promises or auto-send drafts. Every path is documented and tested.

## Implementation Scope

### Batch 1: Drafting Foundation (Schemas + Provider + Validator)
- Created `src/ticketpilot/drafting/schemas.py` with Citation, DraftReply, DraftGenerationTrace Pydantic models
- Created `src/ticketpilot/drafting/provider.py` with AbstractDraftProvider interface and FakeDraftProvider
- Created `src/ticketpilot/drafting/citation_validator.py` with CitationValidator
- Created `src/ticketpilot/drafting/__init__.py` with clean module exports
- Added unit tests: 52 new tests (schemas, provider, validator)
- No modifications to pipeline.py, schema/ticket.py, or any existing module

### Batch 2B: Optional Pipeline Entrypoint
- Added `DraftedTicketResult` wrapper schema
- Created `src/ticketpilot/drafting/pipeline.py` with `run_pipeline_with_draft(raw_ticket)`
- Added 9 new unit tests for the optional entrypoint

### Batch 2C: Integration Tests
- Added `tests/integration/test_drafting_integration.py` with 10 integration tests
- Tests verify: DraftedTicketResult structure, evidence-backed citations, high-risk preservation, confidence bounds, empty-input safety, determinism

### Batch 2D (Partial): Documentation
- Updated `docs/technical_decisions.md` with drafting architecture decisions

## Forbidden Scope

- No modifications to `pipeline.py`, `schema/ticket.py`, `schema/evidence.py`, or any existing module
- No real LLM provider (FakeDraftProvider is the only implementation)
- No LangGraph workflow orchestration
- No Streamlit review UI (handled in Stage 1D)
- No Langfuse/Ragas observability
- No evaluation pipeline with golden-answer test sets
- No auto-send or one-click reply dispatch
- No persistent DraftGenerationTrace storage in database
- No multi-turn or conversational draft generation
- No improved reranker or embedding fine-tuning
- No `source_id` DB lookup for multi-chunk documents (maintains seed-only assumption)

## Tests and Quality Gate Result

| Metric | Value |
|--------|-------|
| Unit tests (Batch 1) | 52 new (schemas, provider, validator) |
| Unit tests (Batch 2B) | 9 new (optional entrypoint) |
| Integration tests (Batch 2C) | 10 new (full drafting workflow) |
| Total unit tests | 263 passed (203 prior + 60 new drafting-specific) |
| Total integration tests | 65 passed (55 prior + 10 new) |
| Ruff | All checks passed |
| OpenSpec validate --all | 10/10 passed |
| Quality gate | PASSED |
| No existing tests modified | Confirmed |

## Major Risks

| Risk | Handling |
|------|----------|
| **Template-based replies sound mechanical** | Acceptable for MVP. Real LLM provider (future) replaces template with natural language. |
| **Regex-based unsupported claim guard has high false-positive/negative rate** | Conservative patterns for MVP. Future LLM-based semantic check can replace regex scanner via same `CitationValidator` interface. |
| **FakeDraftProvider may mask real provider issues** | Interface mismatches caught at compile time. CI runs with fake provider; separate evaluation pipeline (future) runs with real provider. |
| **No-evidence fallback is hardcoded Chinese text** | Acceptable for MVP. Future change should make fallback messages configurable or locale-aware. |
| **Regex claim detection may not work well with real Chinese text** | Documented limitation. Patterns tuned for typical support reply phrasing. |

## Deferred Items

- Real LLM provider (OpenAI, Claude, etc.) — `AbstractDraftProvider` interface ready
- Automatic pipeline integration (calling `generate_draft` inside `intake_risk_pipeline`) — requires no schema changes
- Pipeline draft entrypoint integration test for audit fields — deferred to final gate
- Evaluation pipeline with golden-answer test sets for draft quality
- Persistent `DraftGenerationTrace` storage in database
- Configurable/locale-aware fallback messages
- LLM-based semantic claim verifier (replaces regex `CitationValidator`)
- Multi-turn or conversational draft generation

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `e30ff5d` | 2026-05-02 | feat: add evidence-grounded drafting foundation |
| `320840f` | 2026-05-02 | feat: add standalone evidence draft generation |
| `b7c5e4f` | 2026-05-02 | test: harden standalone draft generation checks |
| `ff7e8bd` | 2026-05-02 | feat: add optional pipeline draft entrypoint |
| `58bb199` | 2026-05-02 | test: add drafting workflow integration coverage |
| `0a7dd5c` | 2026-05-02 | docs: finalize evidence draft generation decisions |
| `afa8885` | 2026-05-02 | chore: archive evidence draft generation OpenSpec change |

## Reusable Patterns

1. **AbstractDraftProvider interface** — A clean provider abstraction that decouples draft generation from the pipeline. Any generation strategy (template, LLM, hybrid) can be plugged in without changing the pipeline contract.
2. **CitationValidator as deterministic guardrail** — A lightweight, regex-based validator that enforces citation completeness and flags potential unsupported claims. The pattern of post-generation validation with the same interface is reusable for any RAG system.
3. **Optional workflow pattern** — `generate_draft(ticket_output)` as a standalone composition function preserves backward compatibility while enabling optional enhancement. The `run_pipeline_with_draft()` entrypoint demonstrates composition of optional stages without modifying the core pipeline.
4. **DraftedTicketResult wrapper** — A narrow wrapper that preserves the original return type while adding new capabilities. Reusable for any system that needs to extend a function's return value without breaking callers.
5. **Safe fallback hierarchy** — Three-tier safety (no evidence -> safe message, high risk -> capped confidence, exception -> recovery) ensures the system never produces an unsafe or fabricated output. Enforceable for any AI-assisted content generation system.
