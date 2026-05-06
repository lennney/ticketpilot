# Controller Next Actions — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Each entry defines scope, validation, and stop conditions for the next batch.*

---

## Next Batch: Phase 10.7 — Expand Doc-Level Golden Labels

### Scope

1. Label remaining 87 cases with `expected_relevant_doc_ids`
2. Verify CSV validity and backward compatibility
3. Run full-dataset doc-level evaluation
4. Generate updated wrong-case reclassification
5. Validate: openspec --strict, ruff, integration tests (0 skip required)

### Allowed Files

- `docs/harness/chatgpt_controller_context.md`
- `docs/harness/controller_decision_log.md`
- `docs/harness/controller_session_log.md`
- `docs/harness/controller_next_actions.md`
- `data/eval/golden_expectations.csv` (add doc-level labels only)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`

### Forbidden Files

- `src/`
- `tests/`
- `data/knowledge/`
- `data/eval/tickets_eval.csv`
- `data/eval/sample_predictions.csv`
- `reports/retrieval/phase7_*`, `phase8_*`, `phase9_*` (baselines)
- `reports/eval/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`

### Validation Commands

```bash
# Golden CSV validity
uv run python -c "import csv; csv.DictReader(open('data/eval/golden_expectations.csv', encoding='utf-8'))"

# Full evaluation suite
uv run pytest tests/unit/test_retrieval_metrics.py tests/unit/test_evaluation*.py -v --tb=short

# OpenSpec scoped validation
openspec validate add-hybrid-retrieval-ranking-diagnosis --strict

# Ruff
uv run ruff check .

# Secret scan
grep -r "sk-" data/ --include="*.csv"

# Full quality gate (required for data changes affecting evaluation path)
bash scripts/run_quality_gate.sh
```

### Commit Rules

- Commit message must specify case count of newly labeled docs
- Only commit and push on human approval

### Stop Conditions

- Integration tests skipped (must be 0 for data changes)
- Golden expectations CSV becomes invalid
- Doc-level labels reference non-existent records
- Real customer data or API keys in data files
- Forbidden file modified
- Secret scan fails
- OpenSpec validation fails

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

## Completed Batch: Phase 10.5.1 — Real Pipeline Doc-Level Evaluation

### What Was Done

- Exported real pipeline retrieval rows with openai_compatible / text-embedding-v4 / 1024-d provider
- Ran doc-level evaluation on 14 P0-labeled cases using real fused results
- Key finding: **10/14 (71.4%) P0 cases are doc_id-correct at top-10** → substantially confirms the metric granularity thesis
- 11/41 doc-type wrong cases reclassified as metric granularity (doc_id found but doc_type mismatched)
- 4 P0 cases with genuine misses: case_acco_006, case_comp_001, case_comp_002, case_refu_013 (partial)
- Generated 5 reports: rows JSON, metrics JSON, evaluation MD, wrong-case recheck MD
- Fixed `cand.id` → `cand.chunk_id` bug in export mode

### Validation

- Ruff: ✅ Clean
- test_retrieval_metrics + test_evaluation*: 143/143 ✅
- openspec validate --strict: ✅

### Commit

`aeb4ff5` pushed to `origin/master`

---

## Completed Batch: Phase 10.5 — Doc-Level Golden Labels

### What Was Done

- Created label plan: 14 P0 cases (16 record-case pairs) with confirmed doc_ids from Phase 9.4.1 seed data
- Added `expected_relevant_doc_ids` column to `golden_expectations.csv` for 14 P0 cases
- Added `p0_added_record_hit_rate` metric and `WrongCaseDocIdRecheck` to retrieval_metrics.py
- Added 8 new tests for doc_id metrics (40 total, all passing)
- Created `scripts/run_p0_doc_level_eval.py` for P0 doc-level evaluation
- Generated P0 doc-level eval reports (.json + .md)

### Files Created

- `reports/retrieval/phase10_doc_level_golden_label_plan.md`
- `scripts/run_p0_doc_level_eval.py`
- `reports/retrieval/phase10_p0_doc_level_eval.json`
- `reports/retrieval/phase10_p0_doc_level_eval.md`

### Files Modified

- `data/eval/golden_expectations.csv` (added column + 14 cases populated)
- `src/ticketpilot/evaluation/retrieval_metrics.py` (p0_added_record_hit_rate, WrongCaseDocIdRecheck, recheck function)
- `src/ticketpilot/evaluation/retrieval_comparison.py` (report builders)
- `tests/unit/test_retrieval_metrics.py` (8 new tests)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`
- `docs/harness/controller_next_actions.md`

### Validation

- test_retrieval_metrics: 40/40 ✅ All passed
- ruff check: ✅ All passed (0 errors)
- CSV parseable: ✅ DictReader accepts new column

### Key Findings

- Mock-mode P0 eval shows 0% doc_id hit rate (expected — mock uses random IDs)
- Real doc_id evaluation requires pipeline export mode with real embeddings
- 75% of "wrong" cases thesis: doc_id labels now in place to measure this

---

## Completed Batch: Phase 10.3/10.4 — P0 Trace Export + Bottleneck Classification

### What Was Done

- Created P0 layered trace export script and report
- Ran real provider pipeline for 14 P0-related cases
- Classified 16 record-case pairs using 8-category taxonomy
- Found: vector 93.8%, keyword 31.2%, fused top-10 75.0%
- Found: 75% of "wrong" cases = metric granularity problem

### Files Created

- `scripts/export_p0_layered_trace.py`
- `reports/retrieval/phase10_p0_layered_trace_export.md`
- `reports/retrieval/phase10_p0_bottleneck_classification.md`
- `reports/retrieval/phase10_ranking_diagnosis_summary.md`
- `reports/retrieval/phase10_p0_layered_traces.json`

### Files Modified

- `scripts/run_retrieval_comparison.py` (full trace serialization)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`

### Validation

- openspec --strict: ✅ Passed
- ruff check: ✅ Passed
- test_retrieval_metrics: 32/32 ✅ Passed
- No core pipeline changes → no quality gate needed

### Commit

`5206a1c` pushed to `origin/master`
