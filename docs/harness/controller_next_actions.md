# Controller Next Actions — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Each entry defines scope, validation, and stop conditions for the next batch.*

---

## Completed Batch: Phase 10.7.5 — Full-Dataset Real Pipeline Doc-Level Evaluation

### What Was Done

- Ran real pipeline export (openai_compatible / text-embedding-v4 / 1024-d) on 101 cases
- Computed full-dataset doc_id Recall@K, MRR, wrong-case reclassification
- **Metric granularity thesis confirmed**: 32/41 (78%) of wrong cases are metric granularity problems
- **Doc-ID Recall@10: 91.9%** (+32.5% over doc-type 59.4%)
- Generated 4 reports: metrics JSON, evaluation MD, wrong-case recheck MD, remaining misses MD
- Validation: 143 tests pass, ruff clean, openspec --strict valid

### Files Created

- `reports/retrieval/phase10_full_real_doc_level_rows.json`
- `reports/retrieval/phase10_full_real_doc_level_eval_metrics.json`
- `reports/retrieval/phase10_full_real_doc_level_evaluation.md`
- `reports/retrieval/phase10_full_real_doc_level_wrong_case_recheck.md`
- `reports/retrieval/phase10_full_real_doc_level_remaining_misses.md`

### Files Modified

- `scripts/run_phase10_real_doc_level_eval.py` (added full mode)
- `docs/changelog.md` (Phase 10.7.5 entry)
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md` (7.6 marked done)

### Key Findings

- **Doc-ID Recall@10: 91.9%** — significantly higher than doc-type 59.4%
- **47/86 (54.7%)** labeled cases have all expected doc_ids in top-10
- **32/41 (78%)** wrong cases reclassified as metric granularity → thesis confirmed ✅
- **7 zero-hit cases**: no expected doc_id found (query expansion candidates)
- **32 partial-hit cases**: some doc_ids found, others missing (fusion ranking candidates)
- **5 edge cases + 4 domain cases**: genuine misses requiring deeper investigation

### Validation

- test_retrieval_metrics + test_evaluation*: 143/143 ✅
- ruff check: ✅ Clean
- openspec validate --strict: ✅

### Commit

`16cdae9` pushed to `origin/master`

---

## Completed Batch: Phase 10.8 — Portfolio Snapshot

### What Was Done

- Created comprehensive portfolio snapshot: `docs/portfolio/phase10_hybrid_ranking_diagnosis_snapshot.md`
- Updated `ticketpilot_product_case_onepager.md` with Phase 10 summary + overview updated to Phases 8–10
- Updated `product_portfolio_material_pack.md` next-steps, boundary statements, interview Q&A
- Updated README.md with Phase 10 references
- Validation: ruff clean, openspec --strict and --all valid
- docs/changelog.md, tasks.md, controller_next_actions.md updated

### Key Metrics Documented

- Doc-ID Recall@10: 91.9% (+32.5% over doc-type 59.4%)
- 32/41 (78%) wrong cases reclassified as doc-ID found — metric granularity thesis confirmed
- 7 zero-hit cases (query expansion candidates)
- 32 partial-hit cases (fusion ranking candidates)
- 86/101 cases labeled with doc-level golden labels

### Validation

- ruff check: ✅ Clean
- openspec validate --strict: ✅
- openspec validate --all: ✅

### Commit

`68adc13` pushed to `origin/master`

---

## Completed Batch: Phase 10.9 — Final Validation and Archive

### What Was Done

- Ran full quality gate: ✅ Passed
  - Ruff: All checks passed
  - Unit tests: 778 passed
  - Integration tests: 119 passed, **0 skipped**
  - Coverage: 85.27% (≥70%)
  - OpenSpec: 16/16 passed
  - Secret scan: Clean
- Overclaim scan: Clean — all claims in negative/boundary context
- OpenSpec archive: `add-hybrid-retrieval-ranking-diagnosis` → `archive/2026-05-06-*`
- Post-archive `openspec validate --all`: 16/16 passed (retrieval-trace now included)
- Specs updated: retrieval-evaluation (delta applied), retrieval-trace (created)

### Key Deliverables

- Phase 10 evidence chain complete: audit → export → classify → label → evaluate → confirm → snapshot → archive
- Metric granularity thesis confirmed: 78% of wrong cases reclassified
- Doc-ID evaluation infrastructure built and populated (86/101 cases)
- All portfolio docs updated with Phase 10 status

### Validation

- Unit tests: 778/778 ✅
- Integration tests: 119/119 ✅ (0 skipped)
- Coverage: 85.27% ✅
- ruff check: ✅ Clean
- openspec validate --all: ✅ 16/16 passed
- Secret scan: ✅ Clean
- Overclaim scan: ✅ Clean

### Commit

`199fbf2` pushed to `origin/master`

---

## Completed Batch: Phase 10.7 — Full-Dataset Doc-Level Golden Label Expansion

### What Was Done

- Labeled 72 new cases with `expected_relevant_doc_ids` (14 existing → 86 total, 85.1% coverage)
- 15 cases sent to manual review: 5 edge cases, 4 knowledge gaps, 6 ambiguous/low-confidence
- Ran full-dataset doc-level evaluation (mock mode)
- Verified CSV validity, backward compatibility
- Generated label plan, manual review report, evaluation report, wrong-case recheck

### Files Created

- `scripts/label_full_doc_level.py` — systematic labeling script
- `reports/retrieval/phase10_full_doc_level_label_plan.md`
- `reports/retrieval/phase10_full_doc_level_manual_review.md`
- `reports/retrieval/phase10_full_doc_level_eval_metrics.json`
- `reports/retrieval/phase10_full_doc_level_evaluation.md`
- `reports/retrieval/phase10_full_doc_level_wrong_case_recheck.md`

### Files Modified

- `data/eval/golden_expectations.csv` (14 → 86 labeled cases)
- `scripts/run_p0_doc_level_eval.py` (added `full` mode)

### Validation

- test_retrieval_metrics: 40/40 ✅
- test_evaluation*: 103/103 ✅
- ruff check: ✅ Clean
- openspec validate --strict: ✅

### Key Findings

- **86/101 cases labeled** (85.1%) — label coverage no longer a bottleneck
- **Doc-type hit rate @10**: 96.0% (all wrong cases = edge cases with empty expected_doc_types)
- **Doc-id metrics**: 0% in mock mode (expected — requires real pipeline)
- **Metric granularity thesis**: Full-dataset reclassification possible when real pipeline export is run

### Commit

`2852a42` pushed to `origin/master`

---

## Completed Batch: Phase 10.6 — Recommendation Report + Portfolio Delta

### What Was Done

- Aggregated Phase 10.2–10.5.1 evidence chain into recommendation report
- Created portfolio delta with before/after capability comparison
- Priority-ranked recommendations:
  - P0: Expand doc-level golden labels to all 101 cases
  - P1: Query expansion audit for 4 true misses
  - P2: Fusion ranking experiment (conditional on P1 results)
  - P3: Reranker proposal (future work, not now)
- Explicitly addressed why not to tune RRF now (cannot measure impact without labels)

### Files Created

- `reports/retrieval/phase10_recommendation_report.md`
- `reports/retrieval/phase10_portfolio_delta.md`

### Validation

- openspec validate --strict: ✅
- ruff check: ✅ Clean

### Commit

`aeb4ff5` pushed to `origin/master`

---

## Completed Batch: Phase 11.4 — Draft Citation Validation

### What Was Done

- Created `DraftCitationValidationResult` schema with is_valid, valid/invalid/duplicate IDs, missing_citation_required, available_evidence_ids, errors, warnings, must_human_review
- Created `validate_draft_citations()` function validating DraftReply.cited_evidence_ids against EvidenceCandidate list
- Validation rules: evidence ID existence, duplicate detection, missing citation heuristic, unsupported_claims propagation, human review propagation
- 21 unit tests covering all validation rules
- No LLM API calls, no pipeline integration, no retrieval changes

### Files Created

- `src/ticketpilot/drafting/draft_citation_validator.py`
- `tests/unit/test_draft_citation_validator.py`

### Files Modified

- `src/ticketpilot/drafting/__init__.py` (updated exports)

### Key Findings

- Evidence ID existence: chunk_id UUID matching against evidence candidates; invalid IDs make is_valid false and must_human_review true
- Duplicates are warnings (non-fatal) — validator detects and reports but doesn't fail on repeated IDs
- Missing citation heuristic: substantive text without citations flagged, but safe-fallback patterns ("无法确认具体政策条款", "建议转人工处理") and greetings exempted
- Human review propagation: never downgrades DraftReply.must_human_review; validation failures and unsupported_claims force must_human_review
- Fully deterministic — same input always produces same output

### Validation

- Quality gate: ✅ PASSED — 878 unit (+21), 119 integration, **0 skipped**, 86.35% coverage
- Ruff: ✅ All checks passed
- OpenSpec --all: ✅ 17/17 passed
- Secret scan: ✅ Clean
- Overclaim scan: ✅ Clean

### Commit

`pending`

---

## Completed Batch: Phase 11.5 — Unsupported-Claim Guard

### What Was Done

- Created `GuardResult` schema with 7 fields: citation_coverage, has_uncited_claims, has_forbidden_promise, forbidden_promise_details, evidence_sufficiency, risk_flags_respected, guard_passed
- Created `check_claim_guard()` with 5 deterministic checks: citation coverage (parse [chunk_id] from text), uncited claim detection (substantive content without citations), forbidden promise detection (9 regex patterns), evidence sufficiency, risk-aware check (high-risk flag acknowledgment)
- 58 unit tests covering all guard behaviors
- No LLM API calls, no schemas.py changes, no pipeline integration

### Files Created

- `src/ticketpilot/drafting/claim_guard.py`
- `tests/unit/test_claim_guard.py`

### Key Findings

- GuardResult is self-contained in claim_guard.py — pipeline integration (Phase 11.6) will add GuardResult to DraftReply
- Citation coverage is distinct from draft_citation_validator: operates on raw draft_text [UUID] patterns (content-level) vs cited_evidence_ids (structural-level)
- Forbidden promise patterns are fully deterministic regex — testable and predictable
- Safe-fallback and greeting-only messages exempt from uncited-claim flagging to avoid false positives
- Evidence sufficiency is deliberately simple: evidence exists → "sufficient"

### Validation

- Unit tests: ✅ 58/58 passed
- Ruff: ✅ Clean
- OpenSpec --all: ✅ 17/17 passed
- OpenSpec --strict: ✅ Passed

### Commit

`pending`

---

## Completed Batch: Phase 11.3 — Evidence-Grounded Prompt Builder

### What Was Done

- Created `DraftPromptInput` schema with ticket context fields
- Created `build_prompt()` function — assembles role, ticket context, evidence blocks, safety instructions, and output format instructions
- Created `format_evidence_block()` — sorts by rank ascending, formats chunk_id/doc_id/type/title/score, truncates at 200 chars, skips empty content, configurable max count (default 5)
- Created `build_safety_instructions()` — 8 safety rules: draft-only, evidence-grounded, citation requirement, forbidden promises, risk-flag escalation, severity awareness
- Created `build_output_format_instructions()` — structured output spec aligned with DraftReply fields
- 50 unit tests covering all prompt builder behaviors
- No LLM API calls, no pipeline integration

### Files Created

- `src/ticketpilot/drafting/prompt_builder.py`
- `tests/unit/test_prompt_builder.py`

### Key Findings

- Prompt builder is fully deterministic — same input always produces same output
- Evidence packing preserves ranking order, skips empty content, truncates deterministically
- Safety instructions adapt to risk flags, severity, and must_human_review state
- Output format instructions align with existing DraftReply schema fields
- Empty ticket_text raises ValueError (fail-fast on invalid input)

### Validation

- Quality gate: ✅ PASSED — 857 unit (+50), 119 integration, **0 skipped**, 86.04% coverage
- Ruff: ✅ All checks passed
- OpenSpec --all: ✅ 17/17 passed
- Secret scan: ✅ Clean
- Overclaim scan: ✅ Clean

### Commit

`c7f940b` pushed to `origin/master`

---

## Completed Batch: Phase 11.2 — Draft Schema and Deterministic Provider

### What Was Done

- Created `LLMProvider` abstract interface (`llm_provider.py`) with `provider_name`, `model_name`, `generate_draft()`
- Created `FakeLLMProvider` — deterministic, no network, no API keys, safe fallback when evidence missing
- Created provider config + factory (`provider_config.py`) — reads `TICKETPILOT_LLM_PROVIDER` env var, defaults to `"fake"`, raises ValueError for unknown types
- Extended `DraftReply` schema with 4 new fields + cross-field validation (unsupported_claims/escalation_reason auto-sets must_human_review, rejects empty cited_evidence_ids)
- 27 new unit tests (17 for provider, 10 for config/schema)

### Files Created

- `src/ticketpilot/drafting/llm_provider.py`
- `src/ticketpilot/drafting/provider_config.py`
- `tests/unit/test_llm_provider.py`
- `tests/unit/test_llm_config.py`

### Files Modified

- `src/ticketpilot/drafting/schemas.py` (extended DraftReply)
- `src/ticketpilot/drafting/__init__.py` (updated exports)

### Key Findings

- FakeLLMProvider follows same pattern as FakeEmbeddingProvider: fake default, real provider opt-in via env
- Schema backward compatible — all existing tests pass unchanged
- 4 safety mechanisms in FakeLLMProvider: no-evidence fallback → must_human_review, risk_flags → escalation_reason + safety_notes, cited_evidence_ids tracking, confidence from evidence scores
- No fake policy promises: tested against forbidden patterns ("一定退款", "保证赔偿", "已为您处理账号")

### Validation

- Quality gate: ✅ PASSED — 807 unit, 119 integration, **0 skipped**, 85.74% coverage
- Ruff: ✅ All checks passed
- OpenSpec --all: ✅ 17/17 passed
- Secret scan: ✅ Clean

### Commit

`b70128a` pushed to `origin/master`

---

## Completed Batch: Phase 11.1 — Evidence-Grounded LLM Draft Generation Planning

### What Was Done

- Created OpenSpec change `add-evidence-grounded-llm-draft` with 7 files
- Defined LLM provider abstraction, evidence-grounded prompt builder, claim guard architecture
- Defined 4 spec files: draft-generation, claim-guard, human-review, draft-evaluation
- Created 10 sub-phase task breakdown (11.2–11.10)
- No code changes — planning/spec/design only

### Files Created

- `openspec/changes/add-evidence-grounded-llm-draft/proposal.md`
- `openspec/changes/add-evidence-grounded-llm-draft/design.md`
- `openspec/changes/add-evidence-grounded-llm-draft/tasks.md`
- `openspec/changes/add-evidence-grounded-llm-draft/specs/draft-generation/spec.md`
- `openspec/changes/add-evidence-grounded-llm-draft/specs/claim-guard/spec.md`
- `openspec/changes/add-evidence-grounded-llm-draft/specs/human-review/spec.md`
- `openspec/changes/add-evidence-grounded-llm-draft/specs/draft-evaluation/spec.md`

### Validation

- openspec validate --strict: ✅
- openspec validate --all: ✅ 17/17 passed
- ruff check: ✅ Clean

### Commit

`pending`

---

## Completed Batch: Phase 11.6 — Pipeline Integration

### What Was Done

- Created `DraftGenerationResult` wrapper with draft, provider_name, model_name, citation_validation, guard_result, to_trace_dict()
- Created `generate_draft()` function wiring all Phase 11 components in sequence: (1) build prompt input, (2) call LLM provider (FakeLLMProvider by default), (3) CitationValidator (content-level [N] checks), (4) draft_citation_validator (structural ID checks), (5) claim_guard (content-level checks), (6) human review propagation (never downgrades), (7) escalation_reason on guard failure
- Added optional `provider` argument for test injection
- 33 unit tests + 14 integration tests
- No DraftReply schema changes — backward compatible

### Files Created

- `src/ticketpilot/drafting/generator.py`
- `tests/unit/test_draft_generator.py`
- `tests/integration/test_draft_generation_integration.py`

### Files Modified

- `src/ticketpilot/drafting/__init__.py` (added exports)

### Key Findings

- Option B wrapper preserves DraftReply backward compatibility
- Provider injection via constructor argument enables clean testing
- CitationValidator + draft_citation_validator run in parallel (complementary layers)
- to_trace_dict() excludes draft text and prompts — compact for audit

### Validation

- Unit tests: ✅ 33/33 passed
- Integration tests: ✅ 14/14 passed
- Ruff: ✅ Clean
- OpenSpec --all: ✅ 17/17 passed
- OpenSpec --strict: ✅ Passed

### Commit

`pending`

---

## Completed Batch: Phase 11.7 — Human Review Console Update

### What Was Done

- Extended ReviewDecision schema with 15 optional audit fields (provider_name, model_name, citation_validation_valid, valid/invalid_cited_evidence_ids, missing_citation_required, guard_passed, guard_uncited_claims, guard_forbidden_promise, guard_forbidden_details, guard_risk_not_acknowledged, human_review_forced, human_review_reasons, escalation_reason)
- Added draft_gen_to_audit_fields() converter function in console.py — pure function, no API calls, excludes prompts/draft text
- Extended build_review_decision() with optional gen_result parameter — old callers work unchanged
- Added guard status display section in Streamlit console — shows provider, citation validation (green/red), guard status (green/red), forbidden promise errors, uncited claim warnings, human review reasons, escalation reason, confidence, no-auto-send notice
- 107 review tests pass (existing + new)

### Files Modified

- `src/ticketpilot/review/schemas.py` — +15 optional audit fields
- `src/ticketpilot/review/console.py` — draft_gen_to_audit_fields() + guard display
- `tests/unit/test_review_schemas.py` — +14 TestReviewDecisionAuditFields tests
- `tests/unit/test_review_console_helpers.py` — +33 new tests
- `openspec/changes/add-evidence-grounded-llm-draft/tasks.md` — Phase 11.7 marked done

### Validation

- Review tests: ✅ 107/107 passed
- Ruff: ✅ Clean

### Commit

`pending`

---

## Completed Batch: Phase 11.8 — Offline Draft Evaluation

### What Was Done

- Created `draft_metrics.py` with 4 pure metric functions + summary aggregation
- Added `DraftEvaluationRow` and `DraftEvaluationSummary` to `evaluation/schemas.py`
- Created CLI runner `scripts/run_draft_evaluation.py` using FakeLLMProvider (no network, no API keys)
- Generated per-case rows JSON, summary JSON, and markdown report under `reports/eval/`
- 32 unit tests + 7 integration tests, all pass
- Markdown report includes scope boundaries, metric definitions, summary table, limitations, no-auto-send notice

### Files Created

- `src/ticketpilot/evaluation/draft_metrics.py`
- `src/ticketpilot/evaluation/schemas.py` (extended)
- `scripts/run_draft_evaluation.py`
- `tests/unit/test_draft_metrics.py`
- `tests/integration/test_draft_evaluation_runner.py`
- `reports/eval/phase11_draft_evaluation_*.json`
- `reports/eval/phase11_draft_evaluation_report.md`

### Key Metrics Implemented

- citation_precision_avg (None when no citations)
- evidence_coverage_avg (None when no evidence)
- unsupported_claim_rate, forbidden_promise_rate, safe_fallback_rate
- human_review_trigger_accuracy, citation_validation_pass_rate, claim_guard_pass_rate
- average_confidence

### Validation

- Unit tests: ✅ 32/32 passed
- Integration tests: ✅ 7/7 passed
- Ruff: ✅ Clean

### Commit

`7230ebe` pushed to `origin/master`

---

## Completed Batch: Phase 11.9 — Portfolio Snapshot

### What Was Done

- Created comprehensive Phase 11 portfolio snapshot: `docs/portfolio/phase11_evidence_draft_snapshot.md`
- Updated all portfolio docs to reflect Phase 11 completion (status from "进行中/in progress" to "已完成/complete")
- Added Phase 11 column to iteration history table in product_portfolio_material_pack.md
- Updated README.md/en.md with 8-layer safety architecture details
- Updated changelog with Phase 11.9 entry

### Files Created

- `docs/portfolio/phase11_evidence_draft_snapshot.md` — 10-section comprehensive Phase 11 snapshot

### Files Modified

- `README.md` — Phase 11 status + 8-layer safety architecture details
- `README.en.md` — Phase 11 status + 8-layer safety architecture details
- `docs/portfolio/product_portfolio_material_pack.md` — Iteration summary, Phase 11 column
- `docs/portfolio/project_case_study_cn.md` — Phase 11 complete status
- `docs/portfolio/project_case_study_en.md` — Phase 11 complete status
- `docs/portfolio/interview_talking_points.md` — 1-minute pitch updated
- `docs/changelog.md` — Phase 11.9 entry added
- `openspec/changes/add-evidence-grounded-llm-draft/tasks.md` — Phase 11.9 marked complete

### Validation

- Ruff: ✅ Clean
- OpenSpec --strict: ✅ Valid
- OpenSpec --all: ✅ 17/17 passed

### Commit

`a6d38dd` pushed to `origin/master`

---

## Completed Batch: Phase 11.10 — Final Validation and Archive

### What Was Done

- Ran full quality gate: ✅ 1001 unit + 140 integration (0 skipped) + coverage ≥70%
- Ran OpenSpec validation: ✅ --strict valid, --all 19/19 passed
- Ran secret scan: ✅ Clean
- Ran overclaim scan: ✅ Clean
- Archived OpenSpec change: ✅ `add-evidence-grounded-llm-draft` → `archive/2026-05-06-add-evidence-grounded-llm-draft/`
- Specs updated: claim-guard (+9), draft-generation (+10), draft-evaluation (+13), human-review (+8)
- Updated all harness docs: validation_log, engineering_log, controller_session_log, controller_next_actions, chatgpt_controller_context
- Updated changelog with Phase 11.10 entry

### Validation

- Unit tests: ✅ 1001 passed
- Integration tests: ✅ 140 passed, **0 skipped**
- Coverage: ✅ ≥70% threshold passed
- Ruff: ✅ Clean
- OpenSpec --strict: ✅ Valid
- OpenSpec --all: ✅ 19/19 passed
- Secret scan: ✅ Clean
- Overclaim scan: ✅ Clean
- Archive: ✅ Successful

### Commit

`pending`

---

## Next Batch: Phase 12 — Demo Readiness and Portfolio Delivery

Recommended scope:
- local runbook
- demo script
- screenshot/video checklist
- interview narrative
- reviewer workflow walkthrough
- no major new functionality unless explicitly planned by a new OpenSpec change

Alternative:
- Phase 12 — Real Provider Optional Experiment (only if explicitly prioritized later)