# Controller Next Actions — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Each entry defines scope, validation, and stop conditions for the next batch.*

---

## Next Batch: Phase 10.7.5 — Full-Dataset Real Pipeline Doc-Level Evaluation

### Scope

1. Run real pipeline export (openai_compatible / text-embedding-v4 / 1024-d) on 86 labeled cases
2. Measure full-dataset doc_id Recall@K, MRR, and wrong-case reclassification
3. Compare P0 subset results (Phase 10.5.1) with full 86-case results
4. Determine whether metric granularity thesis holds across all domains
5. Output full-dataset doc-level metrics and wrong-case recheck report
6. Validate: openspec --strict, ruff, tests (0 skip)

### Allowed Files

- `reports/retrieval/phase10_full_doc_level_real_rows.json` (new)
- `reports/retrieval/phase10_full_doc_level_real_eval_metrics.json` (new)
- `reports/retrieval/phase10_full_doc_level_real_evaluation.md` (new)
- `reports/retrieval/phase10_full_doc_level_real_wrong_case_recheck.md` (new)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`
- `docs/harness/controller_next_actions.md`

### Forbidden Files

- `src/` (no code changes unless bugfix)
- `data/knowledge/`
- `data/eval/golden_expectations.csv` (labels already complete)
- `data/eval/tickets_eval.csv`
- `reports/retrieval/phase7_*`, `phase8_*`, `phase9_*` (baselines)
- `reports/retrieval/phase10_p0_*` (P0 subset reports preserved)
- `reports/eval/`
- `.env`, `.env.local`

### Validation Commands

```bash
# Full evaluation suite
uv run pytest tests/unit/test_retrieval_metrics.py tests/unit/test_evaluation*.py -v --tb=short

# OpenSpec scoped validation
openspec validate add-hybrid-retrieval-ranking-diagnosis --strict

# Ruff
uv run ruff check .

# Secret scan
grep -r "sk-" data/ --include="*.csv"

# Full quality gate
bash scripts/run_quality_gate.sh
```

### Stop Conditions

- Integration tests skipped (must be 0 for pipeline changes)
- Real pipeline export fails (provider unavailable, API key missing)
- Forbidden file modified
- Secret scan fails
- OpenSpec validation fails

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
