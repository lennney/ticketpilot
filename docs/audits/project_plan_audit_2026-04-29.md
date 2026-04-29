# Project Plan Audit — 2026-04-29

**Branch**: `audit/project-plan-review`
**Auditor**: project-auditor agent (4 sub-agents, read-only)
**Scope**: OpenSpec, src/ticketpilot/, tests/, docs/, scripts/, db/, data/, README.md, pyproject.toml, docker-compose.yml
**Final Decision**: HOLD_NEW_FEATURES

---

## 1. Executive Summary

TicketPilot has implemented two foundation layers (Stage 1A: intake + risk, Stage 1B: retrieval infrastructure) with solid unit test coverage. However, the project carries five blocking issues that must be resolved before proceeding to any new features:

1. **Quality gate is a no-op** — `|| true` on every check means nothing can fail.
2. **Physical DB separation violated** — spec demands FAQ/Policy/Case in 3 separate tables; implementation uses 1 table with `doc_type` column.
3. **Retrieval disconnected from main pipeline** — `pipeline.py` stops at risk assessment, never calls retrieval.
4. **Integration tests never run against real DB** — 26 conditionally skipped, zero end-to-end verification.
5. **README describes a finished product** — only ~25% of pipeline stages exist.

Positives: phase_status.md is accurate and honest. changelog.md is factually correct for Batch 2. Unit tests (115) are meaningful and pass. The documented gaps (DB gap, fake embedding) are disclosed.

---

## 2. Current Phase Status (Corrected)

| Phase | Claimed | Evidence | Verdict |
|-------|---------|----------|---------|
| Stage 1A (intake + risk) | ACCEPTED | Code + 69 passing unit tests + 8 golden cases | **CORRECT** |
| Stage 1B Batch 1 (knowledge schema + chunking) | ACCEPTED | Code + unit tests + seed data validation | **CORRECT** |
| Stage 1B Batch 2 (hybrid retrieval) | ACCEPTED_WITH_DB_GAP | Code exists, unit tests pass, **26 integration tests skipped** | **CORRECT** |

**Correction needed**: The DB gap is broader than disclosed. Not only are integration tests skipped — the physical DB table separation required by spec (FAQ/Policy/Case in 3 source tables) is not implemented. The current `knowledge_chunks` single-table design with `doc_type` discriminator violates the design's own FORBIDDEN rule.

---

## 3. Requirement-to-Evidence Matrix

### Stage 1A — Ticket Intake Risk Triage

| # | Requirement | Implementation | Test Evidence | Status |
|---|------------|---------------|---------------|--------|
| 1 | RawTicket schema | `schema/ticket.py:43-48` | `test_schema_validation.py` | PASS |
| 2 | NormalizedTicket schema | `schema/ticket.py:51-59` | `test_schema_validation.py` | PASS |
| 3 | IntentClass enum (8 values) | `schema/ticket.py:9-19` | `test_schema_validation.py` | PASS |
| 4 | ClassificationResult schema | `schema/ticket.py:62-67` | `test_schema_validation.py` | PASS |
| 5 | RiskFlag enum (8 values) | `schema/ticket.py:22-32` | `test_schema_validation.py` | PASS |
| 6 | RiskAssessment schema | `schema/ticket.py:70-75` | `test_schema_validation.py` | PASS |
| 7 | TicketOutput schema | `schema/ticket.py:78-86` | `test_schema_validation.py` | PASS |
| 8 | Text normalization | `intake/normalizer.py` | `test_intake.py` (TestTextNormalizer: 4 tests) | PASS |
| 9 | Entity extraction (order numbers) | `intake/entity_extractor.py` | `test_intake.py` (TestEntityExtractor: 5 tests) | PASS |
| 10 | Entity extraction (product_info, amount) | `intake/entity_extractor.py:39-43` | None | **GAP — stubs, always return None** |
| 11 | 8-class intent classification | `classification/classifier.py` | `test_classification.py` (12 tests) | PASS |
| 12 | Risk flag detection (6 keyword flags) | `risk/assessor.py` | `test_risk.py` (12 tests) | PASS |
| 13 | PRIVACY_RISK flag trigger | `risk/rules.py` (keywords: "泄露","隐私","个人信息") | None | **GAP — no test exercises it** |
| 14 | Risk severity calculation | `risk/assessor.py:64-81` | `test_risk.py` | PASS |
| 15 | Intake-risk pipeline | `pipeline.py` | `test_pipeline.py` (7 tests), `test_intake_risk_triage.py` (11 tests) | PASS |
| 16 | Golden cases (8 scenarios) | `test_intake_risk_triage.py` | 8 parametrized cases | PASS |

### Stage 1B — Layered Knowledge Retrieval

| # | Requirement | Implementation | Test Evidence | Status |
|---|------------|---------------|---------------|--------|
| 17 | DocType/ChunkLevel/BusinessDomain enums | `retrieval/schema/knowledge.py` | `test_knowledge_schema.py` (15 tests) | PASS |
| 18 | FAQDocument/PolicyDocument/CaseDocument | `retrieval/schema/knowledge.py` | `test_knowledge_schema.py` | PASS |
| 19 | KnowledgeChunk schema | `retrieval/schema/knowledge.py:131-168` | `test_knowledge_schema.py` | PASS |
| 20 | Parent-child chunking | `retrieval/chunker.py` | `test_chunking.py` (14 tests) | PASS |
| 21 | Seed data (12+12+12 docs) | `data/knowledge/*.json` | `test_seed_data.py` (18 tests) | PASS |
| 22 | Fake embedding (384-d, deterministic) | `retrieval/providers/fake_embedding.py` | `test_fake_embedding.py` (12 tests) | PASS |
| 23 | Keyword search (FTS + LIKE) | `retrieval/keyword_search.py` | `test_keyword_retrieval.py` (5 mocked pass, **5 DB skipped**) | **GAP** |
| 24 | Vector search (HNSW, cosine) | `retrieval/vector_search.py` | `test_vector_retrieval.py` (4 mocked pass, **6 DB skipped**) | **GAP** |
| 25 | RRF fusion (k=60) | `retrieval/rrf.py` | `test_rrf.py` (10 tests) | PASS |
| 26 | Hybrid retrieval pipeline | `retrieval/pipeline.py` | `test_retrieval_pipeline.py` (3 mocked pass, **7 DB skipped**) | **GAP** |
| 27 | Retrieval trace | `retrieval/traces.py` | `test_retrieval_trace.py` (9 pass, **8 DB skipped**) | **GAP** |
| 28 | Retrieval trace DB persistence | None — no `retrieval_traces` table | None | **GAP — no migration** |
| 29 | FAQ/Policy/Case physical DB separation | `knowledge_chunks` single table | None | **GAP — spec requires 3 source tables** |
| 30 | Golden cases (6 retrieval scenarios) | None at `tests/unit/test_retrieval.py` | None | **GAP — file does not exist** |
| 31 | Retrieval wired to main pipeline | `pipeline.py` stops at risk, never calls retrieval | None | **GAP — disconnected** |
| 32 | Evidence-grounded draft reply | None | None | **GAP — not implemented** |
| 33 | Human review routing | None | None | **GAP — not implemented** |
| 34 | Evaluation harness | None | None | **GAP — not implemented** |

**Summary**: 16 PASS, 15 GAP, 0 FAIL. All gaps are documented or discovered by this audit.

---

## 4. Module-by-Module Audit

### 4.1 schema (`src/ticketpilot/schema/`)
- **Purpose**: Pydantic models for ticket lifecycle
- **Input**: Raw ticket text
- **Output**: RawTicket, NormalizedTicket, IntentClass, ClassificationResult, RiskFlag, RiskSeverity, RiskAssessment, TicketOutput
- **Dependencies**: pydantic only
- **Files**: 2 (109 lines)
- **Test coverage**: 11 tests, all pass
- **Issues**: TicketOutput embeds all prior stages — acceptable for MVP, may be too coupled later

### 4.2 intake (`src/ticketpilot/intake/`)
- **Purpose**: Text normalization + entity extraction
- **Input**: RawTicket
- **Output**: NormalizedTicket
- **Dependencies**: schema, re (stdlib)
- **Files**: 3 (129 lines)
- **Test coverage**: 13 tests, all pass
- **Issues**: product_info and amount extraction are stubs (always None). TextNormalizer could be a plain function.

### 4.3 classification (`src/ticketpilot/classification/`)
- **Purpose**: Keyword-based intent classification (8 Chinese ticket categories)
- **Input**: Normalized ticket text (str)
- **Output**: ClassificationResult (intent + confidence)
- **Dependencies**: schema, rules.py
- **Files**: 3 (127 lines)
- **Test coverage**: 12 tests, all pass
- **Issues**: Implicit rule-ordering dependency; `strong_indicator` field dead weight for 7/8 rules; "态度" (attitude) keyword in COMPLAINT rule may cause false positives

### 4.4 risk (`src/ticketpilot/risk/`)
- **Purpose**: Risk flag detection + severity calculation
- **Input**: NormalizedTicket + ClassificationResult
- **Output**: RiskAssessment
- **Dependencies**: schema, rules.py
- **Files**: 3 (136 lines)
- **Test coverage**: 12 tests, all pass
- **Issues**: PRIVACY_RISK has no direct test; POLICY_CONFLICT can only trigger via keywords (no procedural logic)

### 4.5 retrieval (`src/ticketpilot/retrieval/`)
- **Purpose**: Full hybrid retrieval (chunking, keyword, vector, RRF, traces, DB, seeding)
- **Input**: Query string + optional filters
- **Output**: RetrievalTrace (or list of content strings)
- **Dependencies**: pydantic, psycopg, hashlib, re, uuid, json, pathlib
- **Files**: 17 (1986 lines — 75% of codebase)
- **Test coverage**: 41 unit tests pass, 26 integration tests skipped
- **Issues**:
  - Completely disconnected from main pipeline
  - Duplicate `RetrievalTrace` class (schema/retrieval.py vs traces.py)
  - Inconsistent lazy import patterns (`__getattr__` vs `__import__`)
  - `keyword_search_for_testing` / `vector_search_for_testing` wrappers belong in tests, not source
  - BusinessDomain enum duplicated (vs IntentClass in schema)

### 4.6 pipeline (`src/ticketpilot/pipeline.py`)
- **Purpose**: Orchestrates intake → classification → risk
- **Input**: Raw ticket dict
- **Output**: TicketOutput
- **Files**: 1 (83 lines)
- **Issues**: Stops at stage 3 of 8 planned stages. Retrieval, reply generation, human review routing, and evaluation are not connected.
- **Graceful degradation issue**: Intake failures produce an empty NormalizedTicket that silently flows through — caller cannot distinguish "everything worked" from "intake crashed."

---

## 5. Test Coverage Audit

### 5.1 Unit Tests

| Test File | Tests | Status | Quality |
|-----------|-------|--------|---------|
| test_schema_validation.py | 11 | PASS | Meaningful |
| test_intake.py | 13 | PASS | Meaningful |
| test_classification.py | 12 | PASS | Meaningful |
| test_risk.py | 12 | PASS | Missing PRIVACY_RISK test |
| test_pipeline.py | 7 | PASS | Meaningful |
| test_intake_risk_triage.py | 11 | PASS | Strong (8 golden cases) |
| test_knowledge_schema.py | 15 | PASS | Meaningful |
| test_chunking.py | 14 | PASS | Meaningful |
| test_fake_embedding.py | 12 | PASS | Meaningful |
| test_rrf.py | 10 | PASS | Excellent |
| test_seed_data.py | 18 | PASS | Meaningful |
| **Total** | **135** | **All pass** | |

### 5.2 Integration Tests

| Test File | Pass (mocked) | DB Skipped | Status |
|-----------|---------------|------------|--------|
| test_keyword_retrieval.py | 9 | 5 | **GAP** |
| test_vector_retrieval.py | 4 | 6 | **GAP** |
| test_retrieval_pipeline.py | 3 | 7 | **GAP** |
| test_retrieval_trace.py | 9 | 8 | **GAP** |
| **Total** | **25** | **26** | |

### 5.3 Missing Tests (Priority)

1. **PRIVACY_RISK flag trigger** — `risk/rules.py` defines it, no test exercises it (HIGH)
2. **Full end-to-end pipeline** — intake → classification → risk → retrieval → reply (BLOCKING)
3. **6 retrieval golden cases** — specified as `tests/unit/test_retrieval.py`, file does not exist (HIGH)
4. **DB connection failure handling** — no test for graceful degradation (MEDIUM)
5. **Empty seed data / partial result scenarios** (MEDIUM)
6. **Negative tests for chunk boundary conditions** (LOW)

---

## 6. Skipped Test Audit

**Zero permanently skipped tests.** All 26 skips are conditional (DB unavailable).

### Complete Skipped Test Inventory

**tests/integration/test_keyword_retrieval.py (5 skipped)**:
- `test_fts_search_returns_results` — FTS results for known term
- `test_fts_search_ranks_by_relevance` — FTS ordering
- `test_fts_search_with_doc_type_filter` — doc_type filter in FTS
- `test_like_fallback_for_business_terms` — LIKE fallback for business terms
- `test_keyword_search_returns_trace_fields` — KeywordResult field completeness

**tests/integration/test_vector_retrieval.py (6 skipped)**:
- `test_embedding_dimension_validation` — should NOT need DB but imports db.connection
- `test_vector_search_returns_results` — vector search returns results
- `test_vector_search_ranks_by_similarity` — sorted by similarity desc
- `test_vector_search_with_doc_type_filter` — doc_type filter
- `test_vector_search_returns_trace_fields` — VectorResult fields
- `test_vector_search_scores_are_cosine_similarity` — score range and properties

**tests/integration/test_retrieval_pipeline.py (7 skipped)**:
- `test_hybrid_retrieval_integration` — full hybrid pipeline
- `test_pipeline_combines_keyword_and_vector` — both search paths contribute
- `test_pipeline_ranking_differs_from_inputs` — fused ranking diverges
- `test_pipeline_trace_timing` — timing totals >= sum of parts
- `test_pipeline_top_k_limit` — results capped at top_k
- `test_pipeline_with_doc_type_filter` — doc_type filter in pipeline
- `test_pipeline_trace_explainability` — per-ranker breakdown

**tests/integration/test_retrieval_trace.py (8 skipped)**:
- `test_trace_captures_query_and_embedding` — query + embedding in trace
- `test_trace_captures_keyword_results` — KeywordResult instances
- `test_trace_captures_vector_results` — VectorResult instances
- `test_trace_captures_fused_results_with_contributions` — per-ranker math
- `test_trace_captures_latency` — stage latency fields
- `test_trace_explain_result` — explain_result output
- `test_trace_get_result_by_chunk_id` — chunk_id lookup
- `test_trace_nonexistent_chunk_id` — None for unknown ID

**Requirement to unskip**: PostgreSQL with pgvector extension + seeded `knowledge_chunks` table + HNSW index.

---

## 7. Documentation Accuracy Audit

| Document | Accuracy | Issues |
|----------|----------|--------|
| README.md | **LOW** | Describes full 11-stage Copilot; ~3 stages implemented. No mention of gaps, fake embeddings, or DB status. Lists FastAPI/LangGraph/Streamlit as stack — zero code exists. |
| docs/phase_status.md | **HIGH** | Accurate ACCEPTED_WITH_DB_GAP status. Honest gap disclosure. |
| docs/changelog.md | **HIGH** | Batch 2 claims all corroborated by code. Excluded items accurate. |
| docs/technical_decisions.md | **MEDIUM** | Internal contradictions: ef_construction (64 vs 200), fake dim (128 vs 384), FTS config (chinese vs simple). SourceRouter documented but does not exist. Aspirational file layout differs from actual. |
| docs/acceptance_report_batch1.md | **HIGH** (for scope) | **DUPLICATE** of docs/qa_evaluation_batch1.md — identical content. "Production-ready" claim excessive. |
| docs/qa_evaluation_batch1.md | **HIGH** (for scope) | Same as above. |
| docs/retrieval_design.md | **LOW** | Describes 128-d fake embedding, ef_construction=64, FTS config=chinese — all outdated vs actual code. References non-existent files. |
| docs/retrieval_spec.md | N/A | Draft spec, all tasks unchecked. Appropriately marked. |
| docs/evaluation_plan.md | N/A | Aspirational plan only. No implementation. |

### Documents requiring correction:
1. **README.md** — Add "current status" section with phase/batch status, gap disclosure, limitations
2. **docs/technical_decisions.md** — Synchronize ef_construction (200), fake dim (384), FTS config (simple); mark unimplemented sections; remove non-existent file paths
3. **docs/retrieval_design.md** — Update to match actual implementation or mark as aspirational design
4. **docs/acceptance_report_batch1.md** AND **docs/qa_evaluation_batch1.md** — Delete one duplicate; soften "production-ready" claim

---

## 8. Over-Engineering / Under-Engineering Findings

### Over-Engineering

| Item | Severity | Note |
|------|----------|------|
| LIKE fallback in keyword search (~150 lines) | LOW | Design.md says "may not be needed" for MVP |
| RRF per-ranker explanation math | LOW | Good engineering, not required by spec |
| Dual BusinessDomain/IntentClass enums | MEDIUM | Same conceptual domain, different names |
| chunker.py Chinese/English boundary detection (~170 lines) | MEDIUM | Parent-child relationship unused by retrieval code |
| content_hash regex validation in KnowledgeChunk | LOW | Simpler to just store the hash |
| FakeEmbeddingProvider Protocol (vs ABC) | LOW | No static interface checking benefit for protocol |
| Lazy import inconsistency (__getattr__ vs __import__) | LOW | Two patterns for same problem |

### Under-Engineering (Gaps)

| Item | Severity | Note |
|------|----------|------|
| Quality gate uses `\|\| true` on every check | **BLOCKING** | Gate cannot fail; skipped tests invisible |
| No test coverage enforcement | **BLOCKING** | No pytest-cov, no threshold |
| Retrieval not wired to main pipeline | **BLOCKING** | Two subsystems cannot interact |
| Physical DB separation missing | **BLOCKING** | Violates design's FORBIDDEN rule |
| 26 integration tests skipped, never verified | **BLOCKING** | No end-to-end evidence |
| draft reply / human review / evaluation not started | HIGH | Planned but zero code |
| PRIVACY_RISK no test | HIGH | Rule defined but unverified |
| product_info / amount extraction stubs | MEDIUM | Fields exist, never populated |
| SourceRouter documented but not built | MEDIUM | Intent-to-source routing missing |
| 8 of 12 production deps unused | MEDIUM | FastAPI, LangGraph, Streamlit, etc. |
| docker-compose volume path wrong (db/seed/ vs db/migrations/) | LOW | InitDB would silently fail |

---

## 9. Blocking Issues

These must be resolved before proceeding to any new features:

### BLOCK-1: Quality gate is a no-op
**File**: `scripts/run_quality_gate.sh`
**Problem**: Every check (ruff, pytest, openspec) uses `|| true`. The gate always exits 0. 26 skipped integration tests are invisible.
**Fix**: Remove `|| true`, add `--strict-markers` to pytest, add coverage threshold, parse skipped test count and fail if > 0.
**Why blocking**: Without a working gate, all future changes will ship untested. The gate cannot distinguish "everything passes" from "everything skipped."

### BLOCK-2: Physical DB separation not implemented
**Spec**: `openspec/changes/add-layered-knowledge-retrieval-foundation/design.md` — FORBIDDEN: mixing FAQ/Policy/Case into one table.
**Actual**: Single `knowledge_chunks` table with `doc_type` column.
**Missing**: `knowledge_faq`, `knowledge_policy`, `knowledge_case` tables (Tasks 1.6, 1.7, 1.8).
**Fix**: Either (a) add 3 source tables + migration and update seeding, OR (b) amend spec to accept single-table-with-discriminator as valid for MVP.
**Why blocking**: Architectural decision. Future queries, access control, and schema evolution depend on this choice. Spec and implementation must agree.

### BLOCK-3: Retrieval disconnected from main pipeline
**File**: `src/ticketpilot/pipeline.py`
**Problem**: `intake_risk_pipeline` stops after risk assessment. The `hybrid_retrieval` function exists but is never called from the main pipeline. No path from classified ticket to retrieved evidence.
**Fix**: Add a retrieval stage to the main pipeline (or a separate `ticket_to_retrieval` function). Wire intent classification → BusinessDomain mapping.
**Why blocking**: The project's core value proposition (retrieval-augmented ticket handling) cannot be demonstrated. Two subsystems exist in isolation.

### BLOCK-4: Integration tests never run against real DB
**Problem**: 26 integration tests are conditionally skipped. Zero have ever been verified against a live PostgreSQL+pgvector instance.
**Fix**: Set up a real pgvector database (docker), run full integration suite, fix any failures.
**Why blocking**: The retrieval infrastructure has never been verified end-to-end. Keyword search, vector search, RRF fusion, and trace capture are implemented but untested against real data.

### BLOCK-5: README overstates completion
**File**: `README.md`
**Problem**: Describes a complete 11-stage Copilot with FastAPI, LangGraph, Streamlit — only 3 stages exist, none of those libraries have any code.
**Fix**: Add "Current Status" section; list implemented vs planned stages; link to phase_status.md; disclose fake embedding and DB gap.
**Why blocking**: Misleads anyone evaluating the project. Sets wrong expectations for contributors.

---

## 10. Non-Blocking Gaps

These should be tracked but do not prevent proceeding:

| ID | Gap | Priority | Fix |
|----|-----|----------|-----|
| GAP-1 | PRIVACY_RISK flag has no test | HIGH | Add test to test_risk.py |
| GAP-2 | 6 retrieval golden cases not in `test_retrieval.py` | HIGH | Create file or reassign to integration tests |
| GAP-3 | Retrieval traces have no DB persistence | MEDIUM | Add `retrieval_traces` migration |
| GAP-4 | product_info / amount extraction stubs | MEDIUM | Implement or remove fields from schema |
| GAP-5 | SourceRouter documented but not implemented | MEDIUM | Implement or remove from docs |
| GAP-6 | 8 unused production dependencies | MEDIUM | Remove from pyproject.toml or add todo comments |
| GAP-7 | Duplicate RetrievalTrace class | MEDIUM | Consolidate into traces.py version |
| GAP-8 | Duplicate acceptance_report_batch1.md / qa_evaluation_batch1.md | LOW | Delete one |
| GAP-9 | technical_decisions.md contradictions | LOW | Sync with actual code values |
| GAP-10 | Docker volume path mismatch | LOW | Fix docker-compose.yml |
| GAP-11 | BusinessDomain/IntentClass enum duplication | LOW | Create mapping or unify |
| GAP-12 | `002_seed_knowledge_chunks.sql` is no-op placeholder | LOW | Add note explaining Python seeding |
| GAP-13 | Fake embedding not labeled "pipeline verification only" | MEDIUM | Add docstring warning in fake_embedding.py |

---

## 11. Minimal Fix Plan

### Phase 1: Fix Now (before any new feature work)

| Order | Action | Files | Effort |
|-------|--------|-------|--------|
| 1 | Fix quality gate: remove `\|\| true`, add `--strict-markers`, add skip-count check | `scripts/run_quality_gate.sh` | 30 min |
| 2 | Resolve DB table design (a) add 3 source tables OR (b) amend spec | `db/migrations/`, `openspec/` | 2-4 hours |
| 3 | Wire retrieval into main pipeline (intent → BusinessDomain mapping → hybrid_retrieval call) | `src/ticketpilot/pipeline.py`, `src/ticketpilot/__init__.py` | 2-3 hours |
| 4 | Set up pgvector Docker DB, run full integration suite, fix failures | `docker-compose.yml`, integration tests | 3-4 hours |
| 5 | Fix README: add current status, gap disclosure, link to phase_status.md | `README.md` | 30 min |

### Phase 2: Fix Before Next Feature

| Order | Action | Files | Effort |
|-------|--------|-------|--------|
| 6 | Add PRIVACY_RISK test | `tests/unit/test_risk.py` | 15 min |
| 7 | Create retrieval golden case test file or reassign to integration | `tests/unit/test_retrieval.py` or task update | 1-2 hours |
| 8 | Consolidate duplicate RetrievalTrace | `retrieval/schema/retrieval.py`, `retrieval/traces.py` | 1 hour |
| 9 | Add `retrieval_traces` DB migration | `db/migrations/003_*.sql` | 1 hour |
| 10 | Sync technical_decisions.md and retrieval_design.md with actual code | `docs/technical_decisions.md`, `docs/retrieval_design.md` | 1 hour |
| 11 | Remove or comment unused deps in pyproject.toml | `pyproject.toml` | 15 min |
| 12 | Delete duplicate acceptance report | `docs/acceptance_report_batch1.md` or `docs/qa_evaluation_batch1.md` | 5 min |

### Phase 3: Defer Safely

| Order | Action | Effort |
|-------|--------|--------|
| 13 | Implement product_info / amount extraction | 2-3 hours |
| 14 | Implement SourceRouter (intent→source routing) | 2-3 hours |
| 15 | Add negative/error tests (DB failure, empty seed, edge cases) | 3-4 hours |
| 16 | Label fake embedding as "pipeline verification only" | 5 min |
| 17 | Fix docker-compose volume path | 5 min |

### Phase 4: Remove / Simplify

| Order | Action | Effort |
|-------|--------|--------|
| 18 | Consider removing LIKE fallback if FTS alone is sufficient | 1 hour |
| 19 | Simplify chunker if parent-child relationship unused | 1 hour |
| 20 | Move `*_for_testing` wrappers from source to test utils | 30 min |

---

## 12. Recommended Next Phase

**Do not start any new feature work until BLOCK-1 through BLOCK-5 are resolved.**

Recommended sequence:

1. **Audit remediation sprint** (Phase 1 above) — estimated 1-2 days
2. Re-run quality gate against fixed script — confirm all checks pass, 0 skipped integration tests
3. Re-assess phase status — if all 5 blockers resolved, promote Stage 1B Batch 2 from ACCEPTED_WITH_DB_GAP to ACCEPTED
4. Then proceed to Stage 2: evidence-grounded draft reply + human review routing

The current foundation (intake + classification + risk + retrieval) is solid but the integration between its halves and the verification infrastructure must be completed before building upward.

---

## Final Decision

**HOLD_NEW_FEATURES**

Blocking issues must be resolved before proceeding to draft reply generation, human review routing, or evaluation harness. The foundation is well-built but unverified and disconnected. Fix the gate, wire the pipeline, verify against real DB, then continue.
