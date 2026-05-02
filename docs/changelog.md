# TicketPilot Changelog

## 2026-04-29 — Audit Remediation: Quality Gate, Documentation, and Two-Layer Schema (close-project-audit-blockers)

### Changed
- Fixed quality gate to detect real failures: removed `|| true` from ruff, pytest, and openspec validate lines; added `--strict-markers` to pytest; added integration test skip-count guard with `TICKETPILOT_SKIP_DB_TESTS` bypass.
- Added `--cov=src/ticketpilot --cov-fail-under=70` to unit test invocation.
- Created `scripts/run_integration_tests.sh` for standalone integration test execution.
- Added Current Status section to README documenting which stages are ACCEPTED, ACCEPTED_WITH_DB_GAP, or not started, plus key limitations and link to phase_status.md.
- Synced `docs/technical_decisions.md` with actual code: ef_construction=200, fake embedding dim=384, FTS config=simple, removed SourceRouter references, labeled fake embeddings as PIPELINE VERIFICATION ONLY.
- Implemented two-layer source table architecture (BLOCK-2): added `knowledge_faq`, `knowledge_policy`, `knowledge_case` source tables with type-specific columns; added `source_table` and `source_id` columns to `knowledge_chunks` for source traceability.
- Fixed docker-compose.yml volume path: `./db/seed` → `./db/migrations`.
- Annotated `002_seed_knowledge_chunks.sql` as a no-op marker migration.
- Deleted duplicate `docs/acceptance_report_batch1.md`.

### Why
- Prior quality gate used `|| true` on every check, making it impossible to detect failures. 26 skipped integration tests were invisible.
- README described 11 Copilot stages but only ~3 existed, with no gap disclosure.
- Spec required physically separate FAQ/Policy/Case tables but implementation had only a single `knowledge_chunks` table with a discriminator column.
- `technical_decisions.md` contained aspirational values (ef_construction=64, fake dim=128, FTS=chinese, SourceRouter) that did not match the implementation.

### Tests / Evaluation
- Quality gate now exits non-zero on ruff failure, unit test failure, integration test failure (not skip), openspec validation failure, or secret detection.
- Unit tests: 202 pass (unchanged).
- Integration tests: 55 pass with 0 skipped when DB is available.
- All Batches A, B, C committed and merged via `fix/audit-blockers` branch.

### Remaining risks
- Migration 004 (separate source refs migration) not created — source refs folded into migration 003.
- `map_intent_to_doc_types` and `RetrievalTrace` naming collision remain deferred cleanup items from connecting pipeline change.
- Spec Purpose sections in promoted specs still contain placeholder TBD text.

---

## 2026-04-30 — Quality Gate Fix: Mock Isolation, Dependency Restoration, Coverage (close-project-audit-blockers)

### Changed
- Fixed 7 golden case test failures in `tests/unit/test_intake_risk_triage.py` by adding `@patch("ticketpilot.pipeline.retrieve_evidence")` mock with `_make_non_empty_evidence()` helper, isolating unit tests from Stage 4 DB dependency. Decorator order corrected: `@patch` placed above `@pytest.mark.parametrize`.
- Restored `psycopg-pool>=3.3.0` to project dependencies in `pyproject.toml` — `uv sync` had removed it because it wasn't declared, breaking all integration tests (33 skipped).
- Added `COVERAGE_FILE` export to `scripts/run_quality_gate.sh` pointing to `/tmp/` to work around WSL cross-filesystem SQLite lock issue that caused INTERNALERROR during coverage collection.
- Added `pytest-cov>=7.0.0` to dev dependencies in `pyproject.toml`.

### Why
- Quality gate run after Batch D implementation revealed 7 golden case test failures, 33 skipped integration tests, and coverage at 68.97% (below 70% threshold).
- The 4-stage pipeline's Stage 4 (`retrieve_evidence`) requires a live DB, but golden case unit tests did not mock it. With DB unavailable, retrieval returned empty evidence, adding INSUFFICIENT_EVIDENCE flag to all cases.
- Missing `psycopg-pool` dependency caused all integration tests to skip because `connection.py` could not import `ConnectionPool`.
- WSL `\\wsl.localhost\...` paths don't support SQLite file locking, so `pytest-cov` failed to write `.coverage` files in the repo directory.

### Tests / Evaluation
- Quality gate now exits 0 with all checks passing: Ruff clean, 202 unit tests passed (80.25% coverage), 55 integration tests passed (0 skipped), OpenSpec 10/10 passed, no secrets detected.
- No production code modified. No tests weakened. Coverage threshold preserved at 70%.

### Remaining risks
- `test_embedding_dimension_validation` in `tests/integration/test_vector_retrieval.py` still imports from DB module inline — deferred cleanup.
- Batch D Docker/migration/seed verification tasks (D.1.2–D.3.3) not explicitly verified as separate steps, though all integration tests pass.

---

## 2026-04-30 - Batch 1: Schema Foundation + Evidence Mapper (connect-retrieval-to-intake-risk-pipeline)

### Changed
- Added EvidenceCandidate Pydantic model in `src/ticketpilot/schema/evidence.py` with 9 fields: chunk_id, doc_id, doc_type, source_id, source_table, content, score, rank, title.
- Extended TicketOutput in `src/ticketpilot/schema/ticket.py` with evidence_candidates (list[EvidenceCandidate]) and retrieval_trace (RetrievalTrace | None).
- Added evidence_mapper in `src/ticketpilot/retrieval/evidence_mapper.py` to map FusedResult to EvidenceCandidate.
- Exported EvidenceCandidate from `src/ticketpilot/schema/__init__.py`.

### Why
- To establish the bridge schema and adapter layer between the verified retrieval engine and the intake-risk pipeline output.
- EvidenceCandidate provides a clean boundary type that hides FusedResult internals from downstream consumers (future reply generation, Streamlit UI).
- TicketOutput extension is backward compatible — existing constructors work without modification.

### Tests / Evaluation
- Added tests/unit/test_evidence_schema.py: 11 tests covering valid construction, invalid doc_type, invalid rank, and TicketOutput defaults.
- Added tests/unit/test_evidence_mapper.py: 9 tests covering non-empty mapping, rank ordering, source table derivation, and empty input.
- Full suite: 170 unit tests passed, 49 integration tests passed with 0 skips, Ruff clean.
- No production pipeline orchestration changed.
- No retrieval engine internals changed.
- No DB migrations added.

### Remaining risks
- source_id = doc_id is a seed-only assumption and must be replaced by DB lookup when multi-chunk documents are supported.
- Schema layer currently imports RetrievalTrace and DocType from retrieval modules; acceptable for MVP, possible future clean-up.
- Retrieval is not yet connected to the intake-risk pipeline — evidence_candidates and retrieval_trace are never populated by pipeline.py.

---

## 2026-04-30 - Batch 2: Query Builder + retrieve_evidence Wrapper (connect-retrieval-to-intake-risk-pipeline)

### Changed
- Added `build_retrieval_query()` in `src/ticketpilot/retrieval/query_builder.py` — a pure function that constructs Chinese retrieval queries from ticket state.
- Added Chinese intent-to-business-term mapping for all 8 intents (REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER).
- Added risk-flag-to-business-term mapping for 5 substantive risk flags (COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT).
- Meta flags (LOW_CONFIDENCE, INSUFFICIENT_EVIDENCE) are excluded from query expansion.
- Term deduplication preserves insertion order.
- Added `retrieve_evidence()` in `src/ticketpilot/retrieval/retrieve_evidence.py` — thin wrapper composing `build_retrieval_query` → `hybrid_retrieval` → `map_fused_to_evidence`.
- Returns `tuple[list[EvidenceCandidate], RetrievalTrace]` — trace is always present even for empty results.

### Why
- Query builder provides a single, testable function that enriches retrieval queries with domain-specific Chinese business terms, improving recall for classified tickets and flagged risks.
- retrieve_evidence wrapper isolates the retrieval orchestration from the main pipeline, keeping pipeline.py decoupled from retrieval internals.

### Tests / Evaluation
- Added `tests/unit/test_query_builder.py`: 13 tests covering all intents, all risk flags, dedup, meta flag exclusion, empty text, cross-category dedup, insertion order.
- Added `tests/unit/test_retrieve_evidence.py`: 9 tests covering pass-through of top_k/doc_types, tuple return shape, empty results, flag non-mutation, default values.
- Full suite: 192 unit tests passed, 49 integration tests passed, 0 skipped.
- Ruff: all checks passed.
- No pipeline.py changes.
- No INSUFFICIENT_EVIDENCE handling yet.
- No risk_assessment.flags mutation.

### Remaining risks
- Retrieval is not yet connected to the intake-risk pipeline — evidence_candidates and retrieval_trace are never populated by pipeline.py.
- Empty-evidence behavior (INSUFFICIENT_EVIDENCE flag) will be handled in Batch 3.
- Stage-ordering test is still required in Batch 3.

---

## 2026-04-30 - Batch 3: Pipeline Integration (connect-retrieval-to-intake-risk-pipeline)

### Changed
- Wired `retrieve_evidence()` into `intake_risk_pipeline()` as Stage 4 after risk assessment.
- `TicketOutput` now receives `evidence_candidates` and `retrieval_trace` from retrieval.
- Added `_with_added_risk_flag()` helper in pipeline.py — creates a new `RiskAssessment` with an added flag, never mutates the original `flags` set.
- Empty evidence adds `RiskFlag.INSUFFICIENT_EVIDENCE` via the helper.
- Retrieval exceptions degrade gracefully: empty evidence, `None` trace, `INSUFFICIENT_EVIDENCE` added.
- `INSUFFICIENT_EVIDENCE` is treated as a meta flag and does not increase severity by itself.
- `must_human_review` becomes `True` when `INSUFFICIENT_EVIDENCE` is added.
- No reply/draft/generated_response behavior was added.

### Why
- Completes the 4-stage pipeline: intake → classify → assess risk → retrieve evidence.
- Stage 4 is isolated in its own try/except; failures in retrieval never break the pipeline output.
- Immutable flag handling prevents subtle bugs from in-place set mutation across pipeline stages.

### Tests / Evaluation
- Added `tests/unit/test_pipeline_retrieval.py`: 10 tests covering stage ordering, successful retrieval, empty evidence, no in-place mutation, high-risk human-review preservation, exception graceful degradation, no fabricated evidence, no reply fields, trace preservation, meta flag severity preservation.
- Full suite: 202 unit tests passed, 49 integration tests passed, 0 skipped.
- Ruff: all checks passed.
- OpenSpec validate --changes: 4/4 passed.
- No integration tests added in this batch.
- No retrieval engine internals modified.

### Remaining risks
- Some existing unit-level pipeline tests (`tests/unit/test_pipeline.py`) depend on live DB because Stage 4 calls retrieval without mocking; Batch 4 should separate mocked unit tests from live-DB integration tests.
- `map_intent_to_doc_types` is not yet implemented (deferred from design.md).
- `RetrievalTrace` naming collision with `retrieval.pipeline` remains deferred cleanup.
- C.4 / `__init__.py` export task remains open.

---

## 2026-04-30 - Batch 4: C.4 Export Cleanup + Integration Tests + Quality Gate (connect-retrieval-to-intake-risk-pipeline)

### Changed
- Added `build_retrieval_query`, `map_fused_to_evidence`, and `retrieve_evidence` to `src/ticketpilot/retrieval/__init__.py` exports via lazy `__getattr__` (resolves C.4).
- Retrofitted `tests/unit/test_pipeline.py` — all 7 tests now mock `retrieve_evidence` to avoid live DB dependency from Stage 4.
- Added `tests/integration/test_pipeline_retrieval_integration.py`: 6 live-DB tests covering refund query, account security query, high-risk human-review preservation, LOW_CONFIDENCE not blocking retrieval, evidence candidate field validation, and retrieval trace field validation.
- Quality gate passes: 202 unit + 55 integration = 257 passed, 0 skipped.

### Why
- C.4 export cleanup enables `from ticketpilot.retrieval import retrieve_evidence` without circular imports.
- Mock retrofit isolates unit tests from Stage 4's DB dependency, fixing the latent fragility identified in the Batch 3 review.
- Integration tests validate the full 4-stage pipeline against the live knowledge base.

### Tests / Evaluation
- Unit: 202 passed (unchanged count; 7 retrofitted with mocks, 10 Batch 3, 185 prior)
- Integration: 55 passed (+6 new, 0 skipped)
- Ruff: all checks passed
- OpenSpec validate --changes: 4/4 passed
- Quality gate: PASSED

### Remaining risks
- `map_intent_to_doc_types` is deferred (not required by spec; design.md goal only).
- `RetrievalTrace` naming collision with `retrieval.pipeline` remains deferred cleanup.
- `enable_retrieval` flag from design.md is not implemented (simplification).

---

---

## 2026-05-02 — Batch 1: Draft Generation Schemas, Provider, and Validator (add-evidence-draft-generation)

### Changed
- Added `src/ticketpilot/drafting/` module with four new files:
  - `schemas.py` — Citation, DraftReply, and DraftGenerationTrace Pydantic models
  - `provider.py` — AbstractDraftProvider interface and deterministic FakeDraftProvider
  - `citation_validator.py` — CitationValidator for unsupported claim detection
  - `__init__.py` — clean module exports
- FakeDraftProvider generates template-based, evidence-grounded draft replies without LLM calls
- No-evidence fallback produces a safe message with no policy promises
- High-risk tickets produce drafts flagged with `must_human_review=True`
- CitationValidator performs deterministic checks: citation existence, claim-coverage scan, and evidence cross-reference
- Added 3 unit test files (test_drafting_schemas, test_drafting_provider, test_citation_validator)
- No modifications to pipeline.py, schema/ticket.py, or any existing module

### Why
- Completes the drafting data model and provider interface without any pipeline breaking changes
- Enables standalone `generate_draft(ticket_output)` composition without modifying existing return types
- Lays the foundation for pipeline integration in Batch 2

### Tests / Evaluation
- Unit tests: 202 prior + 52 new = 254 unit tests passed
- Ruff clean
- OpenSpec validate —all: 10/10 passed
- No existing tests modified

### Remaining risks
- Pipeline integration (calling generate_draft inside intake_risk_pipeline) deferred to Batch 2
- Regex-based claim detection may produce false positives/negatives with real Chinese text
- FakeDraftProvider is MVP-only; real LLM provider implementation deferred

### Changed
- Initialized TicketPilot project structure.
- Added uv-based Python project setup.
- Added Docker Compose configuration for PostgreSQL + pgvector.
- Added environment template without secrets.
- Prepared Claude Code agents and skills directories.
- Prepared documentation and quality gate structure.

### Why
- To support spec-driven, traceable, AI-assisted development.
- To prevent uncontrolled code generation and requirement drift.

### Tests / Evaluation
- No product code yet.
- Quality gate script will be added in this initialization stage.

### Remaining risks
- No backend workflow implemented yet.
- No database schema implemented yet.
- No evaluation cases yet.
