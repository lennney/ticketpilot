# Controller Session Log — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Structured handoff summaries only — no chat transcripts, no secrets, no raw conversation.*

---

---

## 2026-05-06 — Phase 11.7: Human Review Console Update

**Summary**: Extended ReviewDecision schema with 15 optional audit fields for evidence-grounded draft generation, added draft_gen_to_audit_fields() pure converter, extended build_review_decision() with optional gen_result parameter, and added guard status display section in Streamlit console. 107 review tests pass. Full quality gate passed.

**Key Deliverables**:
- `src/ticketpilot/review/schemas.py` — +15 optional audit fields (provider_name, model_name, citation_validation_valid, valid/invalid_cited_evidence_ids, missing_citation_required, guard_passed, guard_uncited_claims, guard_forbidden_promise, guard_forbidden_details, guard_risk_not_acknowledged, human_review_forced, human_review_reasons, escalation_reason)
- `src/ticketpilot/review/console.py` — draft_gen_to_audit_fields() converter + guard display section in _render_draft_and_actions()
- `tests/unit/test_review_schemas.py` — +14 TestReviewDecisionAuditFields tests
- `tests/unit/test_review_console_helpers.py` — +33 new tests (TestDraftGenToAuditFields + TestBuildReviewDecisionWithGenResult)

**Key Design Decisions**:
- All audit fields default to None/[] — old JSONL records deserialize without error (backward compatible)
- draft_gen_to_audit_fields() is pure: no side effects, no API calls, excludes prompts/draft text
- build_review_decision() gen_result parameter is optional — old callers work unchanged
- Streamlit guard section shows provider, citation validation (green/red), guard status (green/red), forbidden promise errors, uncited claim warnings, human review reasons, escalation reason, confidence, no-auto-send notice
- Reviewer remains final decision-maker: approve/edit/escalate/reject actions unchanged

**Validation**: Review tests PASSED — 107/107 (existing + new), ruff clean

**Phase Status**: Phase 11.7 complete. Phase 11.8 pending (offline draft evaluation).

**Next Batch**: Phase 11.8 — Offline Draft Evaluation

---

## 2026-05-06 — Phase 11.2: Draft Schema and Deterministic Provider

**Summary**: Implemented the foundation for evidence-grounded LLM draft generation: LLMProvider abstract interface, FakeLLMProvider (deterministic, no network, no API keys), provider config/factory, and DraftReply schema extensions with cross-field validation. 27 new unit tests added. Full quality gate passed.

**Key Deliverables**:
- `src/ticketpilot/drafting/llm_provider.py` — LLMProvider ABC with `generate_draft()`, FakeLLMProvider with safe fallback
- `src/ticketpilot/drafting/provider_config.py` — config + factory (`TICKETPILOT_LLM_PROVIDER` env var, default "fake")
- `src/ticketpilot/drafting/schemas.py` — extended DraftReply with 4 fields + cross-field validation
- `tests/unit/test_llm_provider.py` — 17 tests covering all FakeLLMProvider behaviors
- `tests/unit/test_llm_config.py` — 10 tests for config/factory and DraftReply validation

**Key Design Decisions**:
- LLM provider follows same pattern as embedding provider (fake default, real via env)
- FakeLLMProvider has 4 safety mechanisms: no-evidence fallback → must_human_review, risk_flags → escalation_reason + safety_notes, cited_evidence_ids tracking, confidence from evidence scores
- No fake policy promises: tested against forbidden patterns
- Schema backward compatible — all 59 existing tests pass unchanged

**Validation**: Quality gate PASSED — 807 unit, 119 integration (0 skip), 85.74% coverage, ruff clean, OpenSpec 17/17, secret scan clean

**Decisions Made**: See D9 in decision log (applies to both 11.1 planning and 11.2 implementation)

**Phase Status**: Phase 11.2 complete. Phase 11.3 pending (prompt builder).

**Next Batch**: Phase 11.3 — Evidence-Grounded Prompt Builder

---

---

## 2026-05-06 — Phase 11.3: Evidence-Grounded Prompt Builder

**Summary**: Implemented the evidence-grounded prompt/input builder for LLM draft generation. Creates structured prompts from ticket context + evidence candidates with deterministic evidence packing, safety instructions, and output format specification. 50 unit tests added. Full quality gate passed.

**Key Deliverables**:
- `src/ticketpilot/drafting/prompt_builder.py` — DraftPromptInput schema, build_prompt(), format_evidence_block(), build_safety_instructions(), build_output_format_instructions()
- `tests/unit/test_prompt_builder.py` — 50 tests across 5 test classes

**Key Design Decisions**:
- Prompt builder is fully deterministic — same input always produces same output
- Evidence packing: sorts by rank ascending, formats with chunk_id/doc_id/type/title/score, truncates at 200 chars (configurable), skips empty content, max count configurable (default 5)
- Safety instructions adapt to risk flags, severity, and must_human_review state
- Output format instructions align with existing DraftReply schema fields for future parsing
- Empty ticket_text raises ValueError (fail-fast on invalid input)

**Validation**: Quality gate PASSED — 857 unit, 119 integration (0 skip), 86.04% coverage, ruff clean, OpenSpec 17/17, secret scan clean, overclaim scan clean

**Phase Status**: Phase 11.3 complete. Phase 11.4 pending (citation validator extension).

**Next Batch**: Phase 11.4 — Citation Validator Extension

---

---

## 2026-05-06 — Phase 11.4: Draft Citation Validation

**Summary**: Extended citation validation for DraftReply objects. Created `DraftCitationValidationResult` schema and `validate_draft_citations()` function that validates cited_evidence_ids against evidence candidates. 21 unit tests added. Full quality gate passed.

**Key Deliverables**:
- `src/ticketpilot/drafting/draft_citation_validator.py` — DraftCitationValidationResult + validate_draft_citations()
- `tests/unit/test_draft_citation_validator.py` — 21 tests covering evidence ID existence, duplicates, missing citation heuristic, human review propagation

**Key Design Decisions**:
- Evidence ID matching uses chunk_id UUIDs from EvidenceCandidate — consistent with existing Citation schema
- Duplicates reported as warnings (non-fatal) to avoid over-penalizing drafts with repeated IDs
- Missing citation heuristic exempts safe-fallback patterns and non-substantive greetings to avoid false positives on legitimate no-evidence responses
- Human review propagation is one-way: never downgrades; validation failures and unsupported_claims both force must_human_review
- Fully deterministic — sorted output lists ensure stable results

**Validation**: Quality gate PASSED — 878 unit, 119 integration (0 skip), 86.35% coverage, ruff clean, OpenSpec 17/17, secret scan clean, overclaim scan clean

**Phase Status**: Phase 11.4 complete. Phase 11.5 pending (unsupported-claim guard).

**Next Batch**: Phase 11.5 — Unsupported-Claim Guard

---

## 2026-05-06 — Phase 11.5: Unsupported-Claim Guard

**Summary**: Implemented deterministic claim guard for evidence-grounded draft replies. GuardResult schema with 7 fields, check_claim_guard() with 5 checks: citation coverage (parsing [chunk_id] from draft_text), uncited claim detection, forbidden promise detection (9 regex patterns), evidence sufficiency, and risk-aware escalation acknowledgment. 58 unit tests. All deterministic — no network, no LLM API, no semantic analysis.

**Key Deliverables**:
- `src/ticketpilot/drafting/claim_guard.py` — GuardResult schema + check_claim_guard() with 5 checks
- `tests/unit/test_claim_guard.py` — 58 tests across 8 test classes

**Key Design Decisions**:
- GuardResult defined in claim_guard.py (self-contained module; schemas.py integration in Phase 11.6)
- Citation coverage operates on raw draft_text [UUID] patterns (content-level), distinct from draft_citation_validator's cited_evidence_ids (structural-level)
- Forbidden promises: 9 regex patterns for refund/compensation/legal/account/timeline/liability
- Safe-fallback and greeting-only messages exempt from uncited-claim flagging
- Risk-aware: 5 escalation patterns; any match passes for high-risk flags
- Evidence sufficiency is deliberately simple (evidence exists → "sufficient")

**Validation**: 58/58 unit tests passed, ruff clean, OpenSpec 17/17

**Phase Status**: Phase 11.5 complete. Phase 11.6 pending (pipeline integration).

**Next Batch**: Phase 11.6 — Pipeline Integration

---

## 2026-05-06 — Phase 11.6: Pipeline Integration

**Summary**: Integrated all Phase 11 components into a unified draft generation workflow. Created DraftGenerationResult wrapper + generate_draft() function that wires prompt builder → LLM provider → CitationValidator → draft_citation_validator → claim_guard → human review propagation in sequence. 33 unit + 14 integration tests. Full quality gate passed.

**Key Deliverables**:
- `src/ticketpilot/drafting/generator.py` — DraftGenerationResult wrapper with provider_name, model_name, citation_validation, guard_result, to_trace_dict() + generate_draft() function
- `tests/unit/test_draft_generator.py` — 33 tests covering all generator behaviors
- `tests/integration/test_draft_generation_integration.py` — 14 integration tests for end-to-end workflow

**Key Design Decisions**:
- Option B wrapper preserves DraftReply backward compatibility (no schema changes to DraftReply)
- Provider injection via `provider` argument enables clean mocking without monkeypatching
- CitationValidator (content-level [N] checks) + draft_citation_validator (structural ID checks) run in parallel — complementary layers
- Human review propagation is one-way: never downgrades; guard failure and validation failure both force must_human_review
- guard_result lives on DraftGenerationResult (not DraftReply) — Phase 11.7 will integrate into display
- to_trace_dict() excludes draft text and prompts — compact for audit, no sensitive data

**Validation**: 33 unit + 14 integration tests passed, ruff clean, OpenSpec 17/17

**Phase Status**: Phase 11.6 complete. Phase 11.7 pending (human review console update).

**Next Batch**: Phase 11.7 — Human Review Console Update

---

## 2026-05-06 — Phase 11.1: Evidence-Grounded LLM Draft Generation Planning

**Summary**: Created the OpenSpec planning layer for Phase 11 — Evidence-Grounded LLM Draft Generation. This planning batch produced 7 files: proposal, design, tasks, and 4 spec files (draft-generation, claim-guard, human-review, draft-evaluation). No code changes were made.

**Key Deliverables**:
- `openspec/changes/add-evidence-grounded-llm-draft/proposal.md` — problem statement, scope, non-goals
- `openspec/changes/add-evidence-grounded-llm-draft/design.md` — architecture: LLM provider interface, prompt builder, claim guard, pipeline integration, 8 safety layers
- `openspec/changes/add-evidence-grounded-llm-draft/tasks.md` — 10 sub-phases (11.2–11.10) with allowed/forbidden files per phase
- `openspec/changes/add-evidence-grounded-llm-draft/specs/draft-generation/spec.md` — 9 requirements
- `openspec/changes/add-evidence-grounded-llm-draft/specs/claim-guard/spec.md` — 10 requirements
- `openspec/changes/add-evidence-grounded-llm-draft/specs/human-review/spec.md` — 8 requirements
- `openspec/changes/add-evidence-grounded-llm-draft/specs/draft-evaluation/spec.md` — 12 requirements

**Key Design Decisions**:
- LLM provider interface follows the same pattern as FakeEmbeddingProvider (fake default, real provider opt-in via .env.local)
- Claim guard is deterministic (rule-based, no ML/NLP) — same pattern as existing CitationValidator
- Evidence-grounded prompt builder constrains LLM to retrieved evidence only
- 8-layer safety design from prompt constraint through human review

**Validation**: OpenSpec --strict ✅, OpenSpec --all ✅ 17/17, Ruff ✅

**Decisions Made**: See D9 in decision log

**Phase Status**: Phase 11.1 complete (planning). Phase 11.2 pending (draft schema + deterministic provider).

**Next Batch**: Phase 11.2 — Draft Schema and Deterministic Provider

---

## 2026-05-06 — Phase 10.7.5/10.8/10.9: Full-Dataset Real Pipeline Eval + Portfolio + Archive

**Summary**: Completed Phase 10 end-to-end: ran full-dataset real pipeline doc-level evaluation (101 cases, 86 labeled), confirmed metric granularity thesis (32/41 = 78% reclassified), created portfolio snapshot, ran final quality gate (778 unit / 119 int / 0 skip / 85.27% coverage / OpenSpec 16/16), and archived the `add-hybrid-retrieval-ranking-diagnosis` OpenSpec change.

**Key Deliverables**:
- `reports/retrieval/phase10_full_real_doc_level_eval_metrics.json` — Doc-ID Recall@10: 91.9%
- `reports/retrieval/phase10_full_real_doc_level_evaluation.md`
- `reports/retrieval/phase10_full_real_doc_level_wrong_case_recheck.md` — Thesis confirmed: 32/41 (78%)
- `reports/retrieval/phase10_full_real_doc_level_remaining_misses.md` — 7 zero-hit, 32 partial-hit
- `docs/portfolio/phase10_hybrid_ranking_diagnosis_snapshot.md` — portfolio snapshot
- `openspec/changes/archive/2026-05-06-add-hybrid-retrieval-ranking-diagnosis/` — archived change
- `openspec/specs/retrieval-evaluation/spec.md` — delta applied (+6 lines)
- `openspec/specs/retrieval-trace/spec.md` — new spec created (+5 lines)

**Key Findings**:
- Doc-ID Recall@10: **91.9%** (+32.5% over doc-type 59.4%)
- 32/41 (78%) wrong cases reclassified as doc-ID found — **thesis confirmed** ✅
- 7 zero-hit cases (query expansion candidates), 32 partial-hit (fusion ranking candidates)

**Validation**: Quality gate PASSED — 778 unit, 119 integration (0 skip), 85.27% coverage, ruff clean, OpenSpec 16/16, secret scan clean, overclaim scan clean

**Decisions Made**: See D7, D8 in decision log

**Phase Status**: Phase 10 complete and archived

**Next Phase**: Phase 11 — Evidence-Grounded LLM Draft Generation (or alternative: Query Expansion Audit)

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
