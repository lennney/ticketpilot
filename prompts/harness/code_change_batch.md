# Code Change Batch

## Context

This batch modifies source code (`src/`) or tests (`tests/`) within the scope
of an active OpenSpec change. Follow the tasks.md order. Each sub-task should
be validated independently before proceeding.

Read `AGENTS.md` and the relevant OpenSpec design/specs before starting.
Read the existing code patterns in the module you are modifying to match
conventions (import style, error handling, naming).

## Goal

Implement a specific batch from the tasks.md, with:
- Minimal changes — only what the task specifies
- Corresponding tests (unit and/or integration)
- All existing tests still pass
- No scope creep beyond the task

## Allowed Files

- `src/ticketpilot/<module>/` (within the task's scope)
- `tests/unit/` (corresponding test files)
- `tests/integration/` (if integration tests are required)
- `scripts/` (if the task specifies CLI changes)
- `docs/changelog.md`
- `openspec/changes/<change-id>/tasks.md`
- `docs/harness/` (controller context — update if status changed)

## Forbidden Files

- `data/`
- `reports/` (unless the task specifies report generation)
- `docs/portfolio/`
- `pyproject.toml` (unless the task specifies dependency changes)
- `uv.lock`
- `.env`
- `.env.local`
- Phase 7/8/9 baseline reports
- `openspec/` archived changes

## Stop Conditions

- Any test fails (unit or integration)
- Coverage drops below 70%
- Integration tests skipped > 0 (for core pipeline changes)
- Ruff lint errors
- Forbidden file modified
- Secret scan fails
- Implementation deviates from OpenSpec design without approval
- `|| true` or any failure suppression added
- Coverage threshold lowered
- `# noqa` added without justification

## Validation Commands

```bash
# Module-level tests (replace with actual test path)
uv run pytest tests/unit/test_<module>.py -v --tb=short

# Integration tests (if DB available)
uv run python -m pytest tests/integration/test_<module>.py -v --tb=short

# Ruff lint
ruff check .

# Coverage for the changed module
uv run pytest tests/unit/test_<module>.py --cov=src/ticketpilot/<module> --cov-fail-under=70

# OpenSpec scoped validation
openspec validate <change-id> --strict

# Secret scan
grep -r "sk-" src/ --include="*.py"
```

## Commit / Push Rules

Only commit and push on human approval.
- Commit message must include validation result summary
- Each test file change should be justified
- No `--no-verify` commit flag

## Final Return Format

Return:
1. Added/modified file list
2. What was implemented (linked to tasks.md task IDs)
3. Test results (pass/fail counts)
4. Coverage result
5. Ruff result
6. OpenSpec validation result
7. Whether controller context was updated
8. `git status --short`
9. Whether any stop conditions were triggered
10. Whether any forbidden files were modified
