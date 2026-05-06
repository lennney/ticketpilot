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

## Next Batch: Phase 10.8/10.9 — Portfolio Snapshot + Final Validation and Archive

### Scope

1. Create compact portfolio snapshot from delta report (Phase 10.8)
2. Include: methodology, key metrics (Doc-ID Recall@10: 91.9%, thesis confirmed), roadmap
3. Update portfolio product case onepager if needed
4. Run full quality gate: unit tests + integration tests + coverage + ruff + secret scan
5. Verify integration tests: 0 skipped
6. Run `openspec validate add-hybrid-retrieval-ranking-diagnosis --strict`
7. Run `openspec validate --all`
8. Verify no Phase 7/8/9 baseline reports modified
9. Archive change
10. Commit and push

### Allowed Files

- `reports/retrieval/phase10_portfolio_snapshot.md` (new)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`
- `docs/harness/controller_next_actions.md`

### Forbidden Files

- `src/` (no code changes)
- `data/`
- `reports/retrieval/phase7_*`, `phase8_*`, `phase9_*` (baselines)
- `reports/retrieval/phase10_p0_*` (P0 subset reports)
- `reports/retrieval/phase10_full_doc_level_*`, `phase10_full_real_doc_level_*` (Phase 10.7 reports preserved)
- `reports/eval/`
- `.env`, `.env.local`

### Validation Commands

```bash
# Full quality gate
bash scripts/run_quality_gate.sh

# With integration tests skipped (no DB)
TICKETPILOT_SKIP_DB_TESTS=1 bash scripts/run_quality_gate.sh

# OpenSpec validation
openspec validate add-hybrid-retrieval-ranking-diagnosis --strict
openspec validate --all

# Ruff
uv run ruff check .

# Secret scan
grep -r "sk-" data/ --include="*.csv"
```

### Stop Conditions

- Integration tests fail (must be 0 skip if DB available)
- Forbidden file modified
- Secret scan fails
- OpenSpec validation fails
- Phase 7/8/9 baseline reports modified
- Quality gate fails (if modifying code)

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
