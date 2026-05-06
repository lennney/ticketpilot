# Controller Next Actions — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Each entry defines scope, validation, and stop conditions for the next batch.*

---

## Next Batch: Phase 10.5 — Recommendation Report + Doc-Level Labels

### Scope

1. Aggregate Phase 10.4 bottleneck distribution into recommendation report
2. Add `expected_relevant_doc_ids` to `golden_expectations.csv` for P0-related cases (14 cases, 16 record-case pairs)
3. Run evaluation with doc-level metrics to verify P0 impact
4. Update portfolio delta if appropriate

### Allowed Files

- `docs/harness/chatgpt_controller_context.md`
- `docs/harness/controller_decision_log.md`
- `docs/harness/controller_session_log.md`
- `docs/harness/controller_next_actions.md`
- `data/eval/golden_expectations.csv` (add doc-level labels only)
- `reports/retrieval/phase10_recommendation.md` (new)
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

# Seed/schema tests (if golden format changes)
uv run pytest tests/unit/test_seed_data.py -v --tb=short

# OpenSpec scoped validation
openspec validate add-hybrid-retrieval-ranking-diagnosis --strict

# Ruff
uv run ruff check .

# Secret scan (new doc-level labels may reference UUIDs, not secrets)
grep -r "sk-" data/ --include="*.csv"
```

### Commit Rules

- Commit message must specify which cases got doc-level labels
- Must include validation summary
- Must confirm all data is synthetic, no real customer data
- Only commit and push on human approval

### Stop Conditions

- Golden expectations CSV becomes invalid
- Doc-level labels reference non-existent records
- Real customer data or API keys in data files
- Forbidden file modified
- Secret scan fails
- OpenSpec validation fails

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
