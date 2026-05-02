# Testing Strategy

## Overview

TicketPilot uses a two-tier testing approach: unit tests (fast, isolated, always run) and integration tests (require database, run when available). Both tiers are enforced by the quality gate.

## Unit Tests

**Location:** `tests/unit/`

**Characteristics:**
- Fast (sub-second per test)
- No external dependencies (all database calls mocked)
- Always run in the quality gate
- Coverage target: >= 70% line coverage

**Coverage by area (as of Stage 1D):**

| Area | Test File(s) | Test Count |
|------|-------------|------------|
| Ticket schema | `test_ticket_schema.py` | ~25 |
| Evidence schema | `test_evidence_schema.py` | 11 |
| Evidence mapper | `test_evidence_mapper.py` | 9 |
| Intake/risk triage | `test_intake_risk_triage.py` | ~30 |
| Query builder | `test_query_builder.py` | 13 |
| Retrieve evidence | `test_retrieve_evidence.py` | 9 |
| Pipeline retrieval | `test_pipeline_retrieval.py` | 10 |
| Pipeline (mocked) | `test_pipeline.py` | 7 |
| Drafting schemas | `test_drafting_schemas.py` | ~15 |
| Drafting provider | `test_drafting_provider.py` | ~20 |
| Citation validator | `test_citation_validator.py` | ~17 |
| Drafting pipeline | `test_drafting_pipeline.py` | 9 |
| Review schema | `test_review_schema.py` | 11 |
| Review store | `test_review_store.py` | 11 |
| Review console helpers | `test_review_console_helpers.py` | 40 |
| Other unit tests | (classification, risk, retrieval, etc.) | ~90 |
| **Total** | | **325** |

**Mock strategy:**
- Database connections are mocked where unit tests interact with retrieval
- `retrieve_evidence()` is mocked in pipeline tests to avoid Stage 4 DB dependency
- `@patch` decorators are placed above `@pytest.mark.parametrize` (decorator order matters)
- The `_make_non_empty_evidence()` helper provides realistic mock data for tests that need non-empty evidence

## Integration Tests

**Location:** `tests/integration/`

**Characteristics:**
- Require live PostgreSQL + pgvector database
- Load seed data (12 FAQ, 12 Policy, 12 Case documents)
- Conditionally skipped when DB is unavailable
- Skip-count guard in quality gate ensures 0 skipped tests unless explicitly bypassed

**Coverage by area (as of Stage 1D):**

| Area | Test File(s) | Test Count |
|------|-------------|------------|
| Retrieval pipeline | Various `test_vector_retrieval.py`, etc. | ~55 |
| Pipeline retrieval integration | `test_pipeline_retrieval_integration.py` | 6 |
| Drafting workflow | `test_drafting_integration.py` | 10 |
| Review console | `test_review_console.py` | 9 |
| **Total** | | **74 (0 skipped)** |

**Key integration scenarios verified:**
- Refund query returns policy and FAQ evidence
- Account security query returns security-related results
- High-risk tickets preserve `must_human_review` through the full pipeline
- `LOW_CONFIDENCE` does not block retrieval
- Evidence candidate field validation against live DB
- Retrieval trace field validation
- DraftedTicketResult structure with real seed data
- Evidence-backed citations in generated drafts
- CitationValidator with real evidence candidates
- Review decision persistence and round-trip
- No-auto-send verification (only JSONL append)

## Golden Cases

TicketPilot has 8 golden cases originally defined in the Batch 1 QA report:

| ID | Scenario | Intent | Key Risk Flag |
|----|----------|--------|---------------|
| GC1 | Standard refund request | REFUND | — |
| GC2 | Refund with compensation demand | REFUND | COMPENSATION_RISK |
| GC3 | Complaint about defective product | COMPLAINT | COMPLAINT_RISK |
| GC4 | Privacy concern | ACCOUNT_ISSUE | PRIVACY_RISK |
| GC5 | Account security alert | ACCOUNT_ISSUE | ACCOUNT_SECURITY_RISK |
| GC6 | Legal threat | COMPLAINT | LEGAL_RISK |
| GC7 | Complex multi-issue ticket | LOGISTICS | Multiple flags |
| GC8 | Vague/lazy ticket | OTHER | INSUFFICIENT_EVIDENCE |

These golden cases are used for manual smoke testing and were referenced during the audit remediation to fix the 7 test failures caused by missing `retrieve_evidence` mocks.

## Quality Gate

See [quality_gate.md](quality_gate.md) for full documentation of the quality gate stages and thresholds.

## Fake Provider Testing Boundaries

### Fake Embeddings (PIPELINE VERIFICATION ONLY)

Fake embeddings verify:
- Embedding generation and storage pipeline works
- HNSW index creation and vector search mechanics work
- RRF fusion correctly combines keyword and vector rankings
- Full retrieval pipeline integration

Fake embeddings **cannot** verify:
- Semantic retrieval quality
- Meaningful relevance ranking
- Any real-world precision or recall

**Testing implication:** All retrieval integration tests use fake embeddings. Tests that pass with fake embeddings do **not** guarantee acceptable retrieval quality with real embeddings. A separate evaluation pipeline (deferred) is needed for real quality measurement.

### FakeDraftProvider (No LLM)

FakeDraftProvider verifies:
- Draft generation data flow (provider -> validator -> output)
- Citation correctness and formatting
- No-evidence and high-risk fallback paths
- Confidence calculation logic
- Must_human_review flag propagation

FakeDraftProvider **cannot** verify:
- Natural language quality of generated drafts
- Response appropriateness for complex tickets
- Tone, empathy, or brand voice alignment

**Testing implication:** Draft generation tests prove the pipeline mechanics work correctly. Full evaluation of draft quality requires a real LLM provider and an evaluation pipeline (both deferred).

### ReviewStore (JSONL)

ReviewStore tests verify:
- Decision persistence (save -> load -> count)
- Append-only behavior
- Round-trip serialization/deserialization
- Error handling (invalid JSON, missing files)

ReviewStore tests **cannot** verify:
- Multi-user concurrent access (no locking)
- Production database performance
- Authentication or authorization behavior

## Deferred Evaluation Components

The following evaluation capabilities are explicitly deferred:

- **Full evaluation pipeline**: No automated retrieval or generation evaluation scripts exist. The 5-layer evaluation taxonomy is documented in `docs/evaluation_plan.md` but no scripts implement it.
- **Golden-answer test sets**: No curated question-answer pairs for precision/recall/mRR measurement.
- **Retrieval quality metrics**: No NDCG, MRR, recall@k, or precision@k measurements.
- **Draft quality evaluation**: No automated assessment of draft quality, citation accuracy, or hallucination rate.
- **Regression benchmark suite**: No performance regression detection across pipeline versions.
- **User acceptance testing**: No structured UAT process beyond manual golden case review.
