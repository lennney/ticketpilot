# TicketPilot Changelog


## 2026-05-03 — Batch 5: Evaluation Pipeline Finalization and Documentation (add-evaluation-pipeline)

### Added
- Created `docs/technical/evaluation_pipeline.md` — comprehensive documentation covering:
  - Evaluation dataset design (tickets_eval.csv, golden_expectations.csv, sample_predictions.csv)
  - Metric definitions (intent_accuracy, severity_accuracy, must_human_review_accuracy, evidence_doc_type_recall, fallback_correctness, no_auto_send_compliance, risk_flag_metrics)
  - CLI usage for both CSV and pipeline prediction modes
  - JSON and Markdown report output formats
  - Current limitations (seed data, fake embedding, no real-world performance)
  - Deferred: realistic data pack, real embedding evaluation, real LLM evaluation, online evaluation, regression detection
  - References to evaluation_plan.md, testing_strategy.md, and CLI entrypoint

### Changed
- Updated `docs/phase_status.md` — "Evaluation Pipeline" entry set to ACCEPTED with test counts (433 unit, 85 integration, 0 skipped, 80.25% coverage), clearly stating evaluation is local deterministic / seed-data based
- Updated `openspec/changes/add-evaluation-pipeline/tasks.md` — Phase 6 (Documentation) tasks 6.1 and 6.3 marked complete; all phases now fully complete

### Why
- Completes the documentation and finalization phase of the add-evaluation-pipeline OpenSpec change
- Provides a single reference document for the evaluation dataset design, metric formulas, CLI usage, and report formats
- Documents current limitations and deferred items to prevent misinterpretation of evaluation results

### Constraints
- No src/ or tests/ files modified
- No data/eval/ files modified
- No pipeline behavior modified
- No retrieval, risk, drafting, review, intake, classification, or database logic modified
- No real embedding provider or real LLM provider introduced
- No network, API, or external service calls
- No real-world performance claims
- All limitations (seed data, fake embedding) explicitly documented

### Tests / Evaluation
- Unit tests: 433 passed (unchanged)
- Integration tests: 85 passed, 0 skipped (unchanged)
- Ruff clean
- OpenSpec validate --all passed
- Quality gate: PASSED
- All evaluation CLI commands produce correct reports
- CSV prediction mode: 100% on all metrics (perfect match)
- Pipeline prediction mode: realistic current performance with identified mismatches
- Archive validation confirms clean post-archive state

### Remaining risks
- Real embedding provider would change evidence retrieval behavior
- Realistic data pack needed for statistically significant evaluation
- Real LLM integration would enable draft quality measurement
- Online / regression evaluation not yet implemented

## 2026-05-02 — Batch 4: Pipeline-Backed Prediction Generation and Integration Tests (add-evaluation-pipeline)

### Added
- Created `src/ticketpilot/evaluation/pipeline_predictions.py` with `predict_from_pipeline()` — maps local TicketPilot pipeline output (via `run_pipeline_with_draft`) to `EvalPrediction` objects by deriving:
  - `predicted_issue_type` from intent classification
  - `predicted_risk_flags` from risk assessment
  - `predicted_severity` from risk assessment
  - `predicted_must_human_review` from risk assessment and DraftReply
  - `predicted_evidence_doc_types` from evidence candidate doc types
  - `predicted_fallback_required` from DraftReply fallback state
  - `predicted_no_auto_send` always True
- Updated `scripts/run_eval.py` with `--prediction-mode` argument (`csv` | `pipeline`) — `csv` mode (default) loads predictions from `--predictions` file, `pipeline` mode runs the local pipeline for each eval ticket
- Updated `src/ticketpilot/evaluation/reporting.py` — both `write_json_report()` and `write_markdown_report()` accept optional `prediction_mode` keyword and include it in report metadata
- Updated `src/ticketpilot/evaluation/__init__.py` with `predict_from_pipeline` export
- Created `tests/integration/test_evaluation_pipeline.py` — 11 integration tests covering:
  - Pipeline prediction shape (one per case, no missing/extra)
  - All required EvalPrediction fields present
  - `predicted_no_auto_send` always True
  - High-risk cases have `predicted_must_human_review=True`
  - No-risk cases have `predicted_must_human_review=False` (when no flags)
  - Fallback detection for no-evidence ticket
  - Predictions can be scored by `metrics.py`
  - Pipeline mode report generation (JSON + Markdown)
  - CLI pipeline mode works end-to-end
  - CLI CSV prediction mode still works (regression)
- Updated `openspec/changes/add-evaluation-pipeline/tasks.md` — Phase 5 (integration tests) marked complete

### Why
- Enables pipeline-backed evaluation of the current local TicketPilot pipeline against the deterministic eval dataset
- Provides a single CLI command to generate pipeline predictions, compute metrics, and produce reports
- All 10 evaluation tickets are processed through the full pipeline (intake → classify → assess risk → retrieve evidence → draft)

### Constraints
- Uses the existing local pipeline only — no real LLM, embedding provider, network, or external API calls
- Default pipeline contract (`intake_risk_pipeline` → `TicketOutput`) remains unchanged
- Report limitations clearly state seed data, fake embedding limitation, and no real-world performance claim

### Tests / Evaluation
- Integration tests: 74 prior + 11 new = **85 passed, 0 skipped** (when DB available)
- Unit tests: 433 passed (unchanged)
- Ruff clean
- OpenSpec validate --all passed
- Quality gate: PASSED
- No pipeline.py, retrieval, risk, drafting, review console, intake, classification, or database logic modified
- No forbidden files touched
- No real LLM, embedding provider, network, or external API introduced

### Remaining risks
- Technical documentation and phase status update pending (Batch 4)
- Real embedding provider would change evidence retrieval behavior

## 2026-05-02 — Batch 3: CLI Evaluation Runner and Report Generation (add-evaluation-pipeline)

### Added
- Created `src/ticketpilot/evaluation/predictions.py` with `load_predictions()` — loads prediction CSV rows into `EvalPrediction` objects with semicolon-separated list parsing, duplicate/column validation, and issue type/severity validation
- Created `src/ticketpilot/evaluation/reporting.py` with:
  - `write_json_report()` — writes structured JSON report with aggregate metrics, per-case results, mismatches, and metadata
  - `write_markdown_report()` — writes human-readable Markdown report with dataset summary, aggregate metric tables, risk flag tables, mismatch summary, and limitations section
- Created `scripts/run_eval.py` — CLI runner accepting `--tickets`, `--golden`, `--predictions`, `--out-json`, `--out-md` arguments; loads data, computes metrics, writes both reports; returns non-zero exit code on invalid input
- Created `data/eval/sample_predictions.csv` — matching predictions for all 10 evaluation tickets for CLI smoke tests
- Created `tests/unit/test_evaluation_predictions.py` — tests for prediction loading, semicolon parsing, duplicate/missing/extra/column validation
- Created `tests/unit/test_evaluation_reporting.py` — tests for JSON/Markdown report structure, keys, limitations section, determinism
- Created `tests/unit/test_run_eval_cli.py` — tests for CLI happy path, invalid input, pipeline isolation, determinism, extra prediction rejection
- Updated `__init__.py` with `load_predictions`, `write_json_report`, `write_markdown_report` exports

### Why
- Enables offline deterministic evaluation of predictions against golden expectations via CLI
- Provides both machine-readable (JSON) and human-readable (Markdown) evaluation reports
- Documented limitations explicitly state current evaluation constraints (small data, fake embeddings, no real-world claim)

### Constraints
- No real pipeline, DB, LLM, or embedding provider calls in `run_eval.py`
- All metric computation is deterministic and operates on in-memory objects only
- Reports include explicit limitations section

### Remaining risks
- Technical documentation and phase status update pending (Batch 4)
- Integration tests for evaluation pipeline pending (Batch 4)
- Real pipeline mode not yet implemented

## 2026-05-02 — Batch 2: Deterministic Metric Computation (add-evaluation-pipeline)

### Changed
- Added `EvalPrediction` schema mirroring `GoldenExpectation` shape with `predicted_*` fields for representing pipeline output
- Added metric schemas: `RiskFlagMetrics` (precision, recall, F1, exact_match), `EvaluationMetrics` (all 7 per-case metric categories), `MismatchEntry` (case_id, metric, expected, predicted), `CaseResult` (full per-case evaluation), `EvaluationSummary` (aggregate metrics with micro-averaged risk flag scores)
- Created `src/ticketpilot/evaluation/metrics.py` with pure, deterministic functions:
  - `compute_risk_flag_metrics()` — handles exact match, missing flag, extra flag, empty sets
  - `compute_evidence_doc_type_recall()` — recall of expected doc types, 1.0 for empty expected
  - `compute_case_metrics()` — all 7 metric categories with mismatch recording
  - `validate_predictions()` — missing/extra case_id detection
  - `compute_evaluation_summary()` — per-case results, aggregate rates, micro-averaged risk flag metrics
- Updated `__init__.py` with new schema and metric function exports
- Added unit tests: `tests/unit/test_evaluation_metrics.py` covering all metric functions, edge cases, validation failures, and determinism

### Why
- Provides deterministic, in-memory metric computation without pipeline, DB, embedding provider, LLM, network, or filesystem dependencies
- Enables offline evaluation of pipeline outputs against golden expectations for post-Batch 3 integration
- Micro-averaged risk flag metrics correctly handle multi-flag cases where per-case averaging would be misleading

### Tests / Evaluation
- Unit tests: 372 prior + 47 new = 419 unit tests passed
- Integration tests: 74 passed, 0 skipped (unchanged — no new integration tests)
- Ruff clean
- OpenSpec validate --all passed
- Quality gate: PASSED
- No pipeline, retrieval, risk, drafting, review, intake, classification, database, or runner code modified
- No forbidden files touched
- .claude/worktrees/ unchanged

### Remaining risks
- Comparison, report, and runner scripts not yet implemented (Batch 3)
- No integration tests for the evaluation pipeline yet (Batch 3)
- Technical documentation and phase status update pending (Batch 4)

### Changed
- Created `data/eval/tickets_eval.csv` with 10 deterministic evaluation tickets covering 8 intent classes, 5 risk flag categories, all 3 severity levels, and edge cases (no-evidence, high-risk legal)
- Created `data/eval/golden_expectations.csv` with golden expectations for all 10 tickets, including semicolon-separated risk flags and evidence doc types
- Created `src/ticketpilot/evaluation/` module with:
  - `schemas.py` — Pydantic models: `EvalTicket`, `GoldenExpectation`, `EvalDataset`, `LoadResult`
  - `loaders.py` — Deterministic CSV loading with validation (required columns, unique case_ids, cross-reference checks, boolean coercion, semicolon-list parsing, issue type/severity validation)
- Added unit tests: `tests/unit/test_evaluation_schemas.py` covering schema validation, issue type/severity validation, boolean coercion, deterministic frozenset comparison
- Added unit tests: `tests/unit/test_evaluation_loaders.py` covering valid CSV loading, duplicate rejection, missing column rejection, unknown issue type/severity rejection, semicolon parsing, cross-reference validation, loader determinism
- Updated `openspec/changes/add-evaluation-pipeline/tasks.md` — Phase 1 tasks, Phase 2.1-2.3, and Phase 4.2-4.3 marked complete

### Why
- Establishes the evaluation data contract (CSV schemas, Pydantic models, validation) before any metric or runner code is written
- Separates golden expectations from ticket text for independent versioning
- Pure I/O loaders with no pipeline, database, LLM, or external service dependencies

### Tests / Evaluation
- Unit tests: 325 prior + 47 new = 372 unit tests passed
- Ruff clean
- No existing tests modified
- No integration tests added in this batch
- Loaders verified deterministic: two consecutive loads produce identical results

### Remaining risks
- Metrics, comparison, and report modules not yet implemented (Batch 2)
- Runner script not yet created (Batch 2)
- No integration tests yet (Batch 3)
- Technical documentation and phase status update pending

## 2026-05-02 — Batch 3A: Reusable Skill Documentation (document-development-process-and-demo-package)

### Changed
- Created `docs/skills/` directory with 10 reusable skill documents extracted from the TicketPilot development process:
  - `spec_driven_development_skill.md` — How to start each feature with an OpenSpec change before implementation
  - `batch_implementation_skill.md` — How to split implementation into safe batches with allowed/forbidden scope
  - `quality_gate_acceptance_skill.md` — Acceptance review, full quality gate, skipped integration test policy, and no `|| true`
  - `openspec_archive_skill.md` — Final validation, task closure, archive, promoted specs, and clean working tree
  - `ticketpilot_product_boundary_skill.md` — How to prevent the system from becoming a generic chatbot, generic RAG demo, or auto-send tool
  - `retrieval_evaluation_skill.md` — Retrieval architecture review, fake embedding limitation, evidence recall, and deferred evaluation
  - `evidence_grounded_generation_skill.md` — DraftReply, citation validation, unsupported claim guard, no-evidence fallback, and high-risk review
  - `human_review_workflow_skill.md` — ReviewDecision, ReviewStore, Approve/Edit/Escalate/Reject, audit trail, and no auto-send
  - `secure_ai_development_skill.md` — Secret handling, no API keys in repo, provider boundaries, local config, and safe defaults
  - `portfolio_project_packaging_skill.md` — How to convert the project into development trace, technical docs, portfolio docs, demo script, and interview talking points
- Updated `openspec/changes/document-development-process-and-demo-package/tasks.md` — Phase 4 tasks marked complete

### Why
- Skills documents extract repeatable methodologies from the TicketPilot development process for reuse in future projects
- Each skill documents purpose, allowed/forbidden scope, step-by-step procedure, acceptance checklist, common failure modes, and a reusable Claude Code prompt template with a TicketPilot example
- Completes Phase 4 (Reusable Skills) of the document-development-process-and-demo-package OpenSpec change

### Content Constraints Enforced in All Skill Docs
- Fake embeddings labeled as pipeline verification only, no semantic meaning
- Seed data stated as synthetic, not real enterprise data
- No auto-send documented as architectural constraint
- High-risk / unsupported / no-evidence outputs require human review
- Evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, and production deployment are listed as deferred
- No exaggerated claims about production readiness, retrieval quality, or LLM capabilities

### Tests / Evaluation
- No source code modified (docs-only change)
- No src/ or tests/ files modified
- Skill docs verified against source material (changelog, technical docs, development trace, OpenSpec specs, portfolio docs)
- All claims traceable to project artifacts, not aspirational plans
- `ruff check` passes (no Python code changed)

### Remaining risks
- Phase 5 (Prompt Library), Phase 7 (Finalization including changelog, quality gate, archive) not yet started
- Skills docs content accuracy depends on accuracy of underlying source materials
- Prompt library docs will cross-reference skill documents

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

## 2026-05-02 — Batch 1: Review Schema and Store Foundation (add-human-review-console)

### Changed
- Added `src/ticketpilot/review/` module with:
  - `ReviewAction` enum: APPROVE, EDIT, ESCALATE, REJECT
  - `ReviewDecision` Pydantic model with audit trail fields (review_id, ticket_id, ticket_text, action, edited_text, decision_reason, original_draft_text, confidence, had_unsupported_claims, was_high_risk, intent, risk_flags, citations_summary, evidence_used_count, reviewed_at)
  - `ReviewStore` class with append-only JSONL persistence (save, load_all, count)

### Why
- Establishes the data contract for human review decisions before any UI code is written
- Ensures every review action is recorded as a self-contained, traceable business decision

### Tests / Evaluation
- Unit tests: 285 passed (263 prior + 22 new)
- Ruff clean
- No existing tests modified

### Remaining risks
- Streamlit console UI not yet implemented (Phase 2)
- No integration tests yet (Phase 3)
- Reviewer identity is MVP-only (label field, no auth)

---

## 2026-05-02 — Batch 2C: Drafting Workflow Integration Tests (add-evidence-draft-generation)

### Changed
- Added `tests/integration/test_drafting_integration.py` with 10 integration tests for the optional drafting workflow
- Tests cover: `DraftedTicketResult` structure, evidence-backed citations, high-risk `must_human_review` preservation, confidence bounds, empty-input safety, determinism, and unsupported policy claim prevention

### Why
- Validates the full real-pipeline-then-draft workflow against the live knowledge base
- Confirms high-risk routing, no-evidence fallback, and citation integrity work end-to-end

### Tests / Evaluation
- Integration tests: 55 prior + 10 new = 65 integration tests passed, 0 skipped
- Unit tests: 263 passed (unchanged)
- Full quality gate: PASSED
- Ruff clean
- OpenSpec validate —all: 10/10 passed

### Remaining risks
- Phase 6 (final quality gate + technical_decisions.md + archive) not yet started
- Integration test for `DraftGenerationTrace` audit fields deferred to final gate

---

## 2026-05-02 — Batch 2B: Optional Pipeline Draft Entrypoint (add-evidence-draft-generation)

### Changed
- Added `DraftedTicketResult` wrapper schema combining `TicketOutput` + `DraftReply` in `drafting/schemas.py`
- Added `run_pipeline_with_draft(raw_ticket)` in `drafting/pipeline.py` — optional entrypoint that runs the existing 4-stage pipeline then generates a draft reply
- `run_pipeline_with_draft()` composes `intake_risk_pipeline()` + `generate_draft()` without modifying either function's contract
- Default `intake_risk_pipeline()` behavior unchanged — `TicketOutput` return type preserved
- No modifications to `pipeline.py`, `schema/ticket.py`, or any existing module

### Why
- Provides a clean, discoverable entrypoint for workflows that need both ticket processing and draft generation
- Keeps the optional workflow separate from the default pipeline contract
- Enables Streamlit UI and API consumers to call a single function without composing manually

### Tests / Evaluation
- Unit tests: 254 prior + 9 new = 263 unit tests passed
- Ruff clean
- No existing tests modified

### Remaining risks
- Integration tests (Phase 5) not yet started — requires DB seed data and seed-specific assertions
- Pipeline integration (modifying `intake_risk_pipeline` default behavior) intentionally deferred

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

---

## 2026-05-02 — Batch 2: Streamlit Human Review Console MVP (add-human-review-console)

### Changed
- Created `src/ticketpilot/review/console.py` — Streamlit console for human reviewers to:
  - Paste RawTicket JSON and process through the full pipeline
  - View ticket info, risk assessment, evidence candidates, citations, and draft reply
  - Approve, edit, escalate, or reject draft replies
  - Persist review decisions to `ReviewStore` (JSONL)
  - Display clear "不自动发送回复" disclaimer
- Added `determine_trigger_reasons(result)` — pure function that inspects risk flags, fallback reason, and unsupported claims to populate `ReviewDecision.review_trigger_reasons`
- Added `build_review_decision(result, action, ...)` — pure data-transformation function converting `DraftedTicketResult` + reviewer action into a `ReviewDecision`

### Why
- Provides a working UI for human reviewers to interact with TicketPilot's draft replies without any frontend framework dependency
- Keeps all data transformations testable as pure functions separate from Streamlit's widget lifecycle

### Tests / Evaluation
- Added `tests/unit/test_review_console_helpers.py`: 40 tests covering:
  - `determine_trigger_reasons` for 5 trigger scenarios (high_risk, no_evidence, unsupported_claims, generation_error, empty)
  - `build_review_decision` for all 4 actions (APPROVE, EDIT, ESCALATE, REJECT)
  - Field population correctness (risk flags, citations summary, evidence count, was_high_risk, had_unsupported_claims)
  - Round-trip persistence through ReviewStore for all 4 action types
  - Scenario-based tests combining multiple trigger conditions
- Full unit suite: 325 passed (285 prior + 40 new)
- Ruff clean
- No existing tests modified

### Remaining risks
- Streamlit UI is an MVP prototype — no auth, no reviewer identity, no auto-refresh
- No integration tests for the console (no browser automation)
- Review decisions are stored on local filesystem only — no shared database backend

---

## 2026-05-02 — Batch 3: Integration Tests + Documentation + Quality Gate (add-human-review-console)

### Changed
- Added `tests/integration/test_review_console.py` with 9 integration tests:
  - Console module imports without Streamlit side effects
  - APPROVE persists original draft
  - EDIT preserves original draft and stores edited final reply
  - ESCALATE stores decision_reason
  - REJECT stores decision_reason
  - Saved record preserves all key audit fields (ticket_id, action, risk_flags, was_high_risk, evidence_used_count)
  - No auto-send side effect (only JSONL append)
- Updated `docs/technical_decisions.md` with Human Review Console Architecture section:
  - Streamlit MVP design rationale
  - Audit trail field mapping
  - No-auto-send safety constraint documented
  - Deferred items listed
- Updated `docs/phase_status.md` with Stage 1D — Human Review Console (ACCEPTED)
- Updated `openspec/changes/add-human-review-console/tasks.md` — Phase 3 tasks marked complete
- Verified Streamlit 1.56.0 is importable (no pyproject.toml change needed)

### Why
- Completes the full test coverage for the human review workflow
- Documents architecture decisions for future maintainers
- Ensures the change is ready for OpenSpec archive

### Tests / Evaluation
- Integration tests: 65 prior + 9 new = **74 passed, 0 skipped**
- Unit tests: 325 passed (unchanged)
- Ruff clean
- OpenSpec validate —all: 11/11 passed
- Quality gate: PASSED
- No pipeline, drafting, retrieval, risk, intake, classification, or database code modified
- No auto-send capability added

### Remaining risks
- Console is local-only (no shared DB, no multi-user queue)
- No authentication or reviewer login
- OpenSpec archive not yet performed

---

## 2026-05-02 — Batch 1: Development Trace Documentation (document-development-process-and-demo-package)

### Changed
- Created `docs/development_trace/index.md` — project overview, readiness levels, stage overview, key constraints, and cross-stage deferred items list
- Created `docs/development_trace/timeline.md` — chronological commit history organized by date and stage
- Created `docs/development_trace/00_project_origin.md` — Stage 0: project initialization, toolchain setup, OpenSpec workflow
- Created `docs/development_trace/01_intake_risk_triage.md` — Stage 1A: ticket intake, intent classification, risk assessment
- Created `docs/development_trace/02_layered_retrieval_foundation.md` — Stage 1B: knowledge schema, hybrid retrieval engine, fake embeddings
- Created `docs/development_trace/03_connect_retrieval_to_pipeline.md` — Wiring retrieval as Stage 4, query builder, evidence mapper
- Created `docs/development_trace/04_quality_gate_hardening.md` — Audit remediation, quality gate fixes, two-layer schema, doc sync
- Created `docs/development_trace/05_evidence_draft_generation.md` — Stage 1C: drafting schemas, FakeDraftProvider, CitationValidator
- Created `docs/development_trace/06_human_review_console.md` — Stage 1D: review schemas, JSONL store, Streamlit console

### Why
- Provides a complete historical narrative of TicketPilot's 6 OpenSpec changes
- Every stage document documents goal, business problem, design decisions, test results, risks, deferred items, and reusable patterns
- Required before technical, skills, and portfolio documentation can be written

### Content constraints enforced in every relevant document
- Fake embeddings are explicitly stated as pipeline verification only (no semantic retrieval quality)
- Current knowledge base is stated as seed data, not real enterprise data
- No auto-send is documented
- High-risk / unsupported / no-evidence outputs require human review
- Evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, and production deployment are listed as deferred

### Tests / Evaluation
- No source code modified (docs-only change)
- git status clean
- `ruff check` passes (no Python code changed)

## 2026-05-02 — Batch 2B: Portfolio Documentation (document-development-process-and-demo-package)

### Changed
- Created `docs/portfolio/` directory with 5 portfolio-facing documents:
  - `project_case_study_cn.md` — Chinese case study for interview/portfolio use
  - `project_case_study_en.md` — English case study, concise and interview-usable
  - `interview_talking_points.md` — 30-second, 1-minute, 3-minute pitches, PM/engineering/risk angles, Q&A
  - `demo_script.md` — Step-by-step demo flow with sample inputs, expected outputs, and what-not-to-claim
  - `limitations_and_next_steps.md` — Demo vs MVP vs production readiness, comprehensive deferred items
- Updated `openspec/changes/document-development-process-and-demo-package/tasks.md` — Phase 6 marked complete

### Content Constraints Enforced in All Portfolio Docs
- Fake embeddings labeled as pipeline verification only, no semantic meaning
- Seed data stated as synthetic, not real enterprise data
- No auto-send documented as architectural constraint
- High-risk / unsupported / no-evidence outputs require human review
- Evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, and production deployment are listed as deferred
- No exaggerated claims about production readiness or retrieval quality

### Tests / Evaluation
- No source code modified (docs-only change)
- No src/ or tests/ files modified
- Portfolio docs verified against source material (changelog, technical docs, development trace, OpenSpec specs)
- All claims traceable to project artifacts, not aspirational plans

## 2026-05-02 — Batch 3C: Finalization and Archive (document-development-process-and-demo-package)

### Changed
- Updated `docs/changelog.md` with Batch 3C finalization entry
- Updated `docs/phase_status.md` to mark documentation package as accepted/completed
- Updated `openspec/changes/document-development-process-and-demo-package/tasks.md` — Phase 7 (Finalization) tasks all marked complete
- Verified documentation package completeness: `docs/development_trace/`, `docs/technical/`, `docs/portfolio/`, `docs/skills/`, `docs/prompts/` all present
- Verified documentation consistently states:
  - Current system is local demo / portfolio-ready, not production-ready
  - Fake embedding proves pipeline mechanics, not real semantic retrieval quality
  - Current knowledge base is seed data, not real enterprise data
  - No auto-send exists
  - Human review is required for risky or unsupported outputs
  - Evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, auth/multi-user review, production deployment, and real customer service integration are deferred

### Tests / Evaluation
- Unit tests: 325 passed (unchanged — documentation only)
- Integration tests: 74 passed, 0 skipped (unchanged — documentation only)
- Coverage: 76.57% (unchanged — no code modified)

### Finalization
- Pre-archive validation: Ruff clean, OpenSpec validate --all passed, quality gate PASSED
- OpenSpec change archived
- Post-archive validation: OpenSpec validate --all passed, quality gate PASSED, working tree clean

## 2026-05-02 — Batch 3B: Prompt Library (document-development-process-and-demo-package)

### Changed
- Created `docs/prompts/` directory with 7 reusable prompt library documents extracted from the TicketPilot development process:
  - `project_director_prompts.md` — 5 prompts for creating OpenSpec changes, defining product boundary, splitting roadmap into stages, preventing scope creep, and selecting next phase
  - `system_architect_prompts.md` — 5 prompts for architecture review, schema/data contract review, integration boundary review, provider abstraction review, and optional workflow design
  - `qa_evaluator_prompts.md` — 5 prompts for test strategy design, golden case planning, quality gate hardening, skipped integration test detection, and coverage/regression review
  - `phase_supervisor_prompts.md` — 5 prompts for implementation-readiness review, batch acceptance review, forbidden-scope audit, task status audit, and final phase acceptance
  - `claude_code_batch_prompts.md` — 6 prompts for schema/store implementation, standalone function implementation, optional entrypoint implementation, integration test batch, docs-only batch, and no-code planning batch
  - `acceptance_review_prompts.md` — 5 prompts for full validation pack, individual stage review, test gap review, production-code untouched verification, and commit readiness report
  - `archive_prompts.md` — 5 prompts for final documentation update, OpenSpec archive readiness, archive command sequence, post-archive validation, and clean working tree verification

### Why
- Prompt library documents extract reusable prompt templates from the TicketPilot development process for use in future projects
- Each prompt entry includes purpose, when to use, inputs, forbidden scope, template, expected output, acceptance checklist, and common failure modes
- Placeholders like [Change name], [Current accepted state], [Allowed files], [Forbidden scope], [Validation commands], and [Return format] make the prompts reusable across projects

### Tests
- Unit tests: 325 passed (unchanged — documentation only)
- Integration tests: 74 passed, 0 skipped (unchanged — documentation only)
- Coverage: 80.25% (unchanged — no code modified)

### Evaluation
- All 7 new prompt documents follow consistent structure and truth-in-documentation rules
- Source material used: development trace, technical docs, portfolio, skills docs, changelog, phase status, technical decisions, archived OpenSpec changes
- No unsupported claims, no exaggeration of maturity, no claims of production readiness
- New files only: docs/prompts/ directory with 7 markdown files

### Remaining risks
- Prompt library documents have not been reviewed by external users; usability validation is deferred
- Some prompt templates may need adjustment for projects with different toolchains
- No automated validation of prompt document structure or consistency exists
