# Controller Next Actions — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Each entry defines scope, validation, and stop conditions for the next batch.*

---

## Next Batch: Phase 10.6 — Recommendation Report

### Scope

1. Aggregate Phase 10.4 bottleneck distribution + Phase 10.5 doc-level label results
2. Produce recommendation report with actionable next steps
3. Update portfolio delta if appropriate

### Allowed Files

- `docs/harness/chatgpt_controller_context.md`
- `docs/harness/controller_decision_log.md`
- `docs/harness/controller_session_log.md`
- `docs/harness/controller_next_actions.md`
- `reports/retrieval/phase10_recommendation.md` (new)
- `docs/changelog.md`
- `openspec/changes/add-hybrid-retrieval-ranking-diagnosis/tasks.md`

### Forbidden Files

- `src/`
- `tests/`
- `data/`
- `reports/retrieval/phase7_*`, `phase8_*`, `phase9_*` (baselines)
- `reports/eval/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`

### Validation Commands

```bash
# OpenSpec scoped validation
openspec validate add-hybrid-retrieval-ranking-diagnosis --strict

# Ruff
uv run ruff check .

# Verify no forbidden files
git diff --stat
```

### Commit Rules

- Only commit and push on human approval
- No runtime changes

### Stop Conditions

- Forbidden file modified
- OpenSpec validation fails

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
