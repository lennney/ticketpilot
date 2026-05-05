# Documentation-Only Batch

## Context

This batch produces documentation, reports, or analysis without modifying
any source code, tests, data, or configuration files. Documentation includes
technical docs, audit reports, design notes, portfolio snapshots, and
development trace entries.

Read `AGENTS.md` before starting. Verify the working tree is clean or
confirm you are working on top of the current batch.

## Goal

Produce documentation or analysis output following existing project
conventions and phase naming.

## Allowed Files

- `docs/technical/`
- `docs/data/`
- `docs/demo/`
- `docs/development_trace/`
- `reports/retrieval/` (phase-namespaced: `phase10_*`, `phase11_*`, etc.)
- `reports/eval/`
- `docs/changelog.md`
- `.claude/CLAUDE.md` (minor updates)

## Forbidden Files

- `src/`
- `tests/`
- `data/knowledge/`
- `data/eval/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`
- Phase 7/8/9 baseline reports (`reports/retrieval/wrong_cases.md`,
  `reports/retrieval/fake_vs_real_comparison.*`,
  `reports/retrieval/phase9_*`)

## Stop Conditions

- Any source code, test, or data file modified
- Phase 7/8/9 baseline report modified
- Portfolio document claims production readiness
- Missing required boundary wording (see AGENTS.md §10)

## Validation Commands

```bash
# OpenSpec validation if an active change exists
openspec validate <change-id> --strict

# Ruff lint (docs may include Python snippets)
ruff check .

# Verify no forbidden files
git diff --stat
```

Do NOT run `pytest`, `coverage`, or integration tests — no code changes.

## Commit / Push Rules

Only commit and push on human approval.
- Docs-only change commit messages use `docs:` prefix
- No runtime behavior claims in commit messages

## Final Return Format

Return:
1. Added/modified file list
2. Key findings or content summary (2-3 sentences)
3. Whether boundary wording was verified
4. Validation results
5. `git status --short`
6. Whether any forbidden files were modified
