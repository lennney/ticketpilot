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

`pending`

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

`pending`

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

`pending`

---

## Completed Batch: Phase 10.8 — Portfolio Snapshot

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

`pending`

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

## Next Batch: Phase 11 — Evidence-Grounded LLM Draft Generation

### Scope

1. Design LLM provider integration (Claude API or OpenAI-compatible)
2. Implement citation-enforced draft generation grounded in retrieved evidence
3. Extend citation validator for LLM-generated content
4. Add human review extensions for LLM-generated drafts
5. Extend evaluation with draft quality metrics
6. Validate: quality gate (0 skip integration tests), openspec --all, ruff, secret scan
7. All Phase 10 portfolio, reports, and archive must remain frozen

### Allowed Files

- `openspec/changes/add-evidence-grounded-llm-draft/` (new change)
- `src/ticketpilot/drafting/` (LLM provider, generator)
- `src/ticketpilot/evaluation/` (draft quality metrics)
- `tests/` (new tests for LLM draft generation)
- `docs/changelog.md`
- `docs/harness/controller_next_actions.md`

### Forbidden Files

- `reports/retrieval/` (Phase 7/8/9/10 reports frozen)
- `docs/portfolio/` (portfolio docs frozen)
- `data/eval/` (eval dataset frozen)
- `data/knowledge/` (knowledge base frozen)
- `openspec/changes/archive/` (archived changes frozen)
- `.env`, `.env.local`

### Alternative Next Phase

If retrieval optimization is prioritized over product features:
- **Phase 11 — Query Expansion Audit**: Audit 7 zero-hit cases for query-knowledge term mismatch. Documentation-only, no code changes. See Phase 10.7.5 remaining misses report.

### Validation Commands

```bash
# Full quality gate
bash scripts/run_quality_gate.sh

# OpenSpec validation
openspec validate add-evidence-grounded-llm-draft --strict
openspec validate --all

# Ruff
uv run ruff check .

# Secret scan
grep -r "sk-" data/ --include="*.csv"
```

### Stop Conditions

- Quality gate fails
- Integration tests skipped when DB is available
- Forbidden file modified
- Secret scan fails
- Phase 7/8/9/10/archive reports modified

