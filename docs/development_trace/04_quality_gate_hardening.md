# Stage 4: Quality Gate Hardening and Audit Remediation

## Stage Goal

Resolve the 5 blocking issues identified in the 2026-04-29 project plan audit: fix the quality gate so it can detect failures, correct the README to accurately reflect project maturity, implement the spec-required two-layer source table architecture, close the integration test DB gap, and sync technical documentation with actual implementation.

## Business Problem Addressed

The project had accumulated significant technical debt in its first three stages:

- **Quality gate was a no-op**: Every check used `|| true`, making it impossible to detect failures. 26 skipped integration tests were invisible. The `set -e` at the top had no effect since every command used `|| true`.
- **README was misleading**: Described 11 Copilot workflow stages but only ~3 existed. No gap disclosure.
- **Spec vs. implementation mismatch**: The knowledge schema spec required physically separate FAQ/Policy/Case tables, but the implementation had only a single `knowledge_chunks` table with a discriminator column. The spec said "FORBIDDEN: mixing sources into one table."
- **Integration tests were unreliable**: 26 tests conditionally skipped when DB was unavailable, with no visibility into which tests were skipped or why.
- **Technical documentation was inaccurate**: `technical_decisions.md` contained aspirational values (ef_construction=64, fake dim=128, FTS config=chinese, SourceRouter) that did not match the implementation.

Without this remediation, all subsequent development would be built on an untestable, misdocumented foundation.

## Key Design Decisions

### 1. Quality gate: remove `|| true`, add two-phase pytest, add skip-count guard
- **Decision**: Remove `|| true` from all checks. Run unit tests and integration tests as separate phases. Add a skip-count guard that fails the gate if integration tests are skipped (unless `TICKETPILOT_SKIP_DB_TESTS=1` is set). Add `--strict-markers` to pytest. Add `--cov=src/ticketpilot --cov-fail-under=70` to unit tests.
- **Rationale**: A quality gate that cannot fail is worthless. The two-phase approach allows unit tests to pass (always) while integration tests have a meaningful skip check. Coverage threshold ensures new code doesn't go untested.

### 2. Two-layer source table architecture (BLOCK-2)
- **Decision**: Implement source layer (3 tables: knowledge_faq, knowledge_policy, knowledge_case) + chunk layer (1 unified knowledge_chunks with source_table/source_id columns).
- **Rationale**: Satisfies the spec's physical separation requirement while preserving retrieval efficiency. This is the standard pattern used by LangChain, LlamaIndex, and production RAG systems. Source tables carry type-specific columns (FAQ: intent_tags, Policy: policy_code, Case: risk_level, compensation_amount).
- **Alternatives considered**: Accept single-table-with-discriminator (zero work but violates spec), three chunk tables (maximum separation but complicates retrieval with union queries).
- **Spec amendment**: The spec was updated to reflect the two-layer design rather than fully separate chunk tables.

### 3. README accuracy with Current Status section
- **Decision**: Add a "Current Status" section listing implemented stages with acceptance status, planned stages as "not started," key limitations, and a link to `docs/phase_status.md`.
- **Rationale**: New readers need an honest assessment of project maturity. Hiding gaps erodes trust.

### 4. WSL-specific coverage fix
- **Decision**: Export `COVERAGE_FILE` to `/tmp/` because WSL `\\wsl.localhost\...` paths don't support SQLite file locking, causing `pytest-cov` INTERNALERROR.
- **Rationale**: The coverage database uses SQLite, which requires file locking. The cross-filesystem WSL path does not support this. Writing to `/tmp/` (native Linux filesystem) resolves the issue.

## Implementation Scope

### Batch A: Quality Gate and Documentation Truthfulness
- Removed `|| true` from ruff, pytest, and openspec validate lines
- Added two-phase pytest: unit tests (must pass) + integration tests (skip count checked)
- Added skip-count guard with `TICKETPILOT_SKIP_DB_TESTS` bypass
- Added `--cov=src/ticketpilot --cov-fail-under=70` to unit tests
- Added `--strict-markers` to pytest
- Added Current Status section to README
- Deleted duplicate `docs/acceptance_report_batch1.md`
- Added "PIPELINE VERIFICATION ONLY" label to fake_embedding.py

### Batch B: Technical Documentation and Infrastructure Fixes
- Synced `docs/technical_decisions.md` with actual code: ef_construction=200, fake dim=384, FTS=simple, removed SourceRouter references
- Fixed docker-compose.yml volume path: `./db/seed` -> `./db/migrations`
- Annotated `002_seed_knowledge_chunks.sql` as no-op marker migration

### Batch C: Two-Layer Source Table Architecture
- Created `db/migrations/003_add_source_tables.sql` with knowledge_faq, knowledge_policy, knowledge_case tables
- Added source_table and source_id columns to knowledge_chunks
- Added indexes on business_domain, created_at for source tables, and (source_table, source_id) on chunks
- Updated Python seeding to insert into source tables and set source_table/source_id on chunks
- Updated KnowledgeChunk Pydantic model with source_table, source_id fields
- Delta spec written documenting the two-layer design amendment

### Additional (Quality Gate Fix Round 2 - 2026-04-30)
- Fixed 7 golden case test failures by adding mock for `retrieve_evidence` in unit tests (test isolation from Stage 4 DB dependency)
- Restored `psycopg-pool>=3.3.0` to project dependencies (was removed by `uv sync` because undeclared)
- Added `pytest-cov>=7.0.0` to dev dependencies
- Added `COVERAGE_FILE` export to work around WSL SQLite lock issue

## Forbidden Scope

- No new product features (strictly remediation)
- No wiring retrieval into the pipeline (BLOCK-3 deferred to separate change)
- No fixing all 17 non-blocking audit gaps (only highest-priority documentation and infrastructure gaps)
- No real embedding provider, reranker, Langfuse/Ragas
- No Docker/migration/seed verification scripts (D.1.2-D.3.3 tasks not explicitly verified as separate steps)

## Tests and Quality Gate Result

| Metric | Value |
|--------|-------|
| Quality gate BEFORE fix | Always exits 0 (meaningless) |
| Quality gate AFTER fix | Exits non-zero on: ruff failure, unit test failure, integration test skip, openspec validation failure, secret detection |
| Unit tests | 202 passed (80.25% coverage) |
| Integration tests | 55 passed, 0 skipped (when DB available) |
| Ruff | All checks passed |
| OpenSpec validate | 10/10 passed |
| Secret detection | No secrets detected |
| Coverage | 80.25% (above 70% threshold) |

## Major Risks

| Risk | Handling |
|------|----------|
| **WSL filesystem causes coverage SQLite lock failures** | Workaround: export `COVERAGE_FILE` to `/tmp/` (native Linux filesystem). Long-term fix: use WSL-native project path. |
| **Migration 004 (separate source refs) not created** | Source refs folded into migration 003. Acceptable — fewer migrations, same result. |
| **Batch D Docker/migration/seed verification tasks not explicitly verified** | Not critical — all integration tests pass, which implicitly validates the DB state. |
| **`test_embedding_dimension_validation` still imports from DB inline** | Deferred cleanup; not blocking quality gate. |

## Deferred Items

- BLOCK-3 wiring (connect-retrieval-to-intake-risk-pipeline) — separate OpenSpec change
- GAP-1: PRIVACY_RISK flag test
- GAP-2: 6 retrieval golden cases as formal smoke tests (covered by 55 integration tests)
- GAP-3: retrieval_traces DB migration
- GAP-4: product_info / amount extraction stubs
- GAP-5: SourceRouter implementation
- GAP-6: 8 unused production dependencies
- GAP-7: duplicate RetrievalTrace class
- GAP-11: BusinessDomain/IntentClass enum duplication
- `test_embedding_dimension_validation` inline DB import cleanup

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `09bd8ea` | 2026-04-29 | audit: project plan audit 2026-04-29 — HOLD_NEW_FEATURES |
| `44f5dbb` | 2026-04-30 | fix: Batch A — quality gate and documentation truthfulness (BLOCK-1, BLOCK-5) |
| `588cf1d` | 2026-04-30 | fix: Batch B — sync technical_decisions.md, fix docker volume, annotate seed migration (GAP-9, GAP-10, GAP-12) |
| `d963c30` | 2026-04-30 | fix: Batch C — two-layer source table architecture (BLOCK-2) |
| `9738f37` | 2026-04-30 | Merge branch 'fix/audit-blockers' |
| (Second round: quality gate fix for mock isolation, dependency restoration, coverage) | 2026-04-30 | |
| `f12b19c` | 2026-05-02 | chore: archive close-project-audit-blockers OpenSpec change |

## Reusable Patterns

1. **Quality gate with proper failure detection** — The two-phase pytest (unit + integration) with skip-count guard pattern is reusable for any project with conditional test dependencies (e.g., database availability).
2. **Skip-count guard with env var bypass** — `TICKETPILOT_SKIP_DB_TESTS=1` allows intentional bypass while catching accidental skips. Pattern usable for any flaky or environment-dependent tests.
3. **Two-layer source architecture (source tables + chunks)** — Separating type-specific document storage from unified chunk retrieval is a production RAG pattern documented by LangChain and LlamaIndex. The migration approach (add new tables, add columns to chunks, update seeds) is reusable.
4. **Coverage workaround for WSL cross-filesystem** — Setting `COVERAGE_FILE` to a Linux-native path resolves SQLite locking issues on WSL. Reusable for any pytest-cov project on WSL.
5. **Documentation sync as a batch task** — The pattern of auditing documentation against code and fixing each discrepancy is reusable for any project that needs to align docs with implementation.
