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

## Next Batch: Phase 11.2 — Draft Schema and Deterministic Provider

### Scope

1. Implement LLM provider interface (abstract base class + FakeLLMProvider)
2. Extend DraftReply schema with provider_id, guard_results, escalation_reason
3. Add provider configuration module (env-based, same pattern as embedding provider)
4. Add unit tests for provider interface and fake provider
5. No real LLM API integration in this sub-phase
6. All Phase 10 portfolio, reports, and archive must remain frozen

### Allowed Files

- `src/ticketpilot/drafting/llm_provider.py` (new)
- `src/ticketpilot/drafting/provider_config.py` (new)
- `src/ticketpilot/drafting/schemas.py` (extend DraftReply)
- `tests/unit/test_llm_provider.py` (new)
- `tests/unit/test_drafting_schemas.py` (extend)
- `openspec/changes/add-evidence-grounded-llm-draft/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

### Forbidden Files

- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (Phase 7/8/9/10 reports frozen)
- `docs/portfolio/` (portfolio docs frozen)
- `openspec/changes/archive/` (archived changes frozen)
- `.env`, `.env.local`

### Validation Commands

```bash
# Module tests
uv run pytest tests/unit/test_llm_provider.py tests/unit/test_drafting_schemas.py -v --tb=short

# OpenSpec validation
openspec validate add-evidence-grounded-llm-draft --strict
openspec validate --all

# Ruff
uv run ruff check .
```

### Stop Conditions

- Real LLM API called
- Retrieval algorithm modified
- Knowledge data or golden labels modified
- Forbidden file modified
- Phase 7/8/9/10/archive reports modified

