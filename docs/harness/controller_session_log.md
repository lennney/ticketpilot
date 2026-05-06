# Controller Session Log — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Structured handoff summaries only — no chat transcripts, no secrets, no raw conversation.*

---

## 2026-05-06 — Phase 10.3/10.4: P0 Trace Export + Bottleneck Classification

**Summary**: Ran P0 layered trace export with real provider (OpenAICompatible, 1024-d) for 14 P0-related cases (16 record-case pairs). Classified each case using 8-category bottleneck taxonomy.

**Key Deliverables**:
- `scripts/run_retrieval_comparison.py` — extended export mode with full trace serialization
- `scripts/export_p0_layered_trace.py` — targeted P0 export script
- `reports/retrieval/phase10_p0_layered_trace_export.md`
- `reports/retrieval/phase10_p0_bottleneck_classification.md`
- `reports/retrieval/phase10_ranking_diagnosis_summary.md`
- `reports/retrieval/phase10_p0_layered_traces.json`

**Key Findings**:
- Vector recall: 93.8%, Keyword recall: 31.2%, Fused top-10: 75.0%
- 75% of "wrong" cases = metric granularity problem (doc_type-level)
- Primary recommendation: add doc-level golden labels

**Validation**: openspec --strict passed, ruff clean, 32/32 retrieval metrics tests passed

**Decisions Made**: See D6 in decision log

**Phase Status**: 10.2–10.4 complete, 10.5–10.7 pending

**Next Batch**: Phase 10.5 — Recommendation report + doc-level labels

---

## 2026-05-06 — Phase 10.2: Trace Data Audit

**Summary**: Audited RetrievalTrace schema — all 26 fields verified. Confirmed runtime trace has all data needed for layered diagnosis. Only gap: export serialization (keyword_results, vector_results, fused_results not in current export format).

**Key Deliverables**:
- `reports/retrieval/phase10_trace_data_audit.md`

**Validation**: openspec --strict passed, ruff clean

**Phase Status**: 10.1–10.2 complete, 10.3+ pending

**Next Batch**: Phase 10.3 — P0 layered trace export

---

## 2026-05-06 — AI Development Harness Created

**Summary**: Created AGENTS.md (10-section project constitution), docs/technical/ai_development_harness.md (6-layer harness design), and 7 prompt templates in prompts/harness/. Inspired by OpenAI Codex sandboxed task paradigm.

**Key Deliverables**:
- `AGENTS.md` — project constitution
- `docs/technical/ai_development_harness.md` — harness design doc
- `prompts/harness/*.md` (7 files) — reusable batch templates

**Validation**: openspec validate --all 16/16 passed, ruff clean

**Decisions Made**: See D4 in decision log

**Next Batch**: Phase 10.2 — Trace data audit

---

## 2026-05-06 — Phase 9.7.1: Post-Archive Validation Repair

**Summary**: Fixed 54 skipped integration tests (root cause: psycopg-binary missing + WSL UNC path DLL loading + pytest entry point). Fixed 8 dimension-mismatch tests (hardcoded 384 vs DB vector(1024)). Ran full quality gate: 770 unit, 119 integration, 0 skipped, 85.29% coverage, ruff clean, OpenSpec 15/15.

**Key Deliverables**:
- `docs/technical/phase9_post_archive_validation_repair.md`
- Fixed `src/ticketpilot/retrieval/db/connection.py` — DLL copy logic
- Fixed `tests/conftest.py` — DLL bootstrap
- Fixed 3 integration test files — dimension detection

**Validation**: Quality gate PASSED

**Next Phase**: Phase 10 — Hybrid Retrieval Ranking Diagnosis

---

## 2026-05-06 — Phase 10 Planning

**Summary**: Created OpenSpec change `add-hybrid-retrieval-ranking-diagnosis` with proposal, design, tasks, and 2 spec files. Defined 8-category bottleneck taxonomy for per-case classification.

**Key Deliverables**:
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/` (6 files)

**Decisions Made**: See D1, D2, D3 in decision log

**Validation**: openspec --strict passed

**Next Batch**: Phase 9.7.1 — Validation repair (then Phase 10.2)
