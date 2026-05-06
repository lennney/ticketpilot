# Evaluation Rerun Batch

## Context

This batch runs the pipeline-backed evaluation on the current knowledge base
and eval dataset. No code changes, no data changes — only evaluation execution
and report generation.

Read the prior phase evaluation report for comparison context. Verify the
database is available with current seed data and embeddings.

## Goal

Run evaluation and produce:
- Retrieval rows export (if retrieval comparison mode)
- Evaluation metrics report
- Before-vs-after comparison (if comparing two runs)
- Wrong-case analysis
- Phase-specific report documents

## Allowed Files

- `reports/retrieval/` (new phase-namespaced reports)
- `reports/eval/` (new reports)
- `docs/changelog.md`
- `openspec/changes/<change-id>/tasks.md`
- `docs/harness/` (controller context — update if status changed)

## Forbidden Files

- `src/`
- `tests/`
- `data/`
- `docs/portfolio/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`
- Phase 7/8/9 baseline reports (`reports/retrieval/wrong_cases.md`,
  `reports/retrieval/fake_vs_real_comparison.*`, `reports/retrieval/phase9_*`)

## Stop Conditions

- Database not available
- Seed data empty or stale
- Prior phase report accidentally overwritten
- Evaluation script fails
- Any source code, test, or data file modified as side effect
- Secret scan fails

## Validation Commands

```bash
# Check DB availability and seed data
uv run python -c "
from ticketpilot.retrieval.db.seeding import get_chunk_count
print(f'Chunks: {get_chunk_count()}')
"

# Run retrieval comparison export
uv run python scripts/run_retrieval_comparison.py export \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --out-rows reports/retrieval/phase10_retrieval_rows.json

# Run evaluation pipeline
uv run python scripts/run_eval.py \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --predictions data/eval/sample_predictions.csv \
    --out-json reports/eval/phase10_report.json \
    --out-md reports/eval/phase10_report.md

# Verify no baseline reports overwritten
git diff --name-only

# Ruff lint (report scripts may be new)
ruff check .

# Secret scan
grep -r "sk-" reports/ --include="*.json" --include="*.md"
```

## Commit / Push Rules

Only commit and push on human approval.
- Report-only changes use `reports:` or `docs:` prefix
- Must confirm no baseline reports were overwritten
- Must confirm provider identity is declared in reports

## Final Return Format

Return:
1. Generated report files
2. Key metrics summary (hit rates, MRR, wrong-case count)
3. Any warnings or anomalies
4. Whether baseline reports remain unmodified
5. Whether controller context was updated
6. `git status --short`
7. Whether any forbidden files were modified
