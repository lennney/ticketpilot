# Data Change Batch

## Context

This batch modifies knowledge data (FAQ/Policy/Case seed files) or evaluation
data (tickets, golden expectations). No source code or test logic changes.

Read `AGENTS.md` before starting. Read the relevant seed file schemas and
existing record formats before writing new data.

## Goal

Add or modify data records following:
- Existing JSON schema for seed files (UUIDs, field names, doc_types)
- Existing CSV schema for evaluation files (column names, value ranges)
- Phase 9 traceability pattern (gap ID references, wrong case mapping)
- Synthetic data only — no real customer data

## Allowed Files

- `data/knowledge/faq_seed.json`
- `data/knowledge/policy_seed.json`
- `data/knowledge/case_seed.json`
- `data/eval/tickets_eval.csv`
- `data/eval/golden_expectations.csv`
- `data/eval/sample_predictions.csv`
- `docs/changelog.md`
- `openspec/changes/<change-id>/tasks.md`
- `reports/retrieval/` (phase-namespaced summaries only)

## Forbidden Files

- `src/`
- `tests/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`
- Phase 7/8/9 baseline reports

## Stop Conditions

- Real customer data or API keys in data files
- UUID collision with existing records
- Schema violation (wrong field names, types, or values)
- Secret scan fails
- Data file becomes invalid JSON or CSV
- Forbidden file modified

## Validation Commands

```bash
# Validate JSON syntax for seed files
uv run python -c "import json; json.load(open('data/knowledge/faq_seed.json'))"
uv run python -c "import json; json.load(open('data/knowledge/policy_seed.json'))"
uv run python -c "import json; json.load(open('data/knowledge/case_seed.json'))"

# Run seed data schema tests
uv run pytest tests/unit/test_seed_data.py -v --tb=short

# Run knowledge schema tests
uv run pytest tests/unit/test_knowledge_schema.py -v --tb=short

# OpenSpec scoped validation
openspec validate <change-id> --strict

# Ruff lint
ruff check .

# Secret scan
grep -r "sk-" data/ --include="*.json" --include="*.csv"
```

## Commit / Push Rules

Only commit and push on human approval.
- Commit message must list which records were added/modified
- Must include validation summary
- Must confirm all data is synthetic, no real customer data

## Final Return Format

Return:
1. Added/modified file list
2. Records added/modified and their purpose (gap IDs, case mappings)
3. Schema validation results
4. Secret scan result
5. OpenSpec validation result
6. `git status --short`
7. Whether any forbidden files were modified
