# TicketPilot Changelog

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

## 2026-04-29 - Initialize development management workflow

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
