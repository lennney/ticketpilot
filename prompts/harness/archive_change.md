# OpenSpec Archive Batch

## Context

This batch archives a completed OpenSpec change. Archive is the final step
before a phase is considered fully complete. The change must have all
tasks marked as done and all validation must pass.

Read `AGENTS.md` before starting. Verify the working tree is clean and
the change's tasks.md has all items checked.

## Goal

Archive the OpenSpec change and verify post-archive state:
1. Run full quality gate (unit + integration + coverage + ruff + secret scan)
2. Verify integration tests: 0 skipped
3. Run `openspec validate <change-id> --strict`
4. Run `openspec validate --all`
5. Verify no Phase 7/8/9 baseline reports modified
6. Archive: `openspec archive <change-id>`
7. Post-archive verify: `openspec validate --all`
8. Update changelog
9. Commit and push

## Allowed Files

- `docs/changelog.md`
- `openspec/changes/<change-id>/tasks.md`
- `docs/phase_status.md` (if updated)
- `docs/harness/` (controller context — update if status changed)

## Forbidden Files

- `src/`
- `tests/`
- `data/`
- `reports/`
- `docs/portfolio/`
- `pyproject.toml`
- `uv.lock`
- `.env`
- `.env.local`
- Phase 7/8/9 baseline reports
- Other OpenSpec changes (not being archived)

## Stop Conditions

- Working tree not clean before archive
- Integration tests skipped > 0 (unless `TICKETPILOT_SKIP_DB_TESTS=1`)
- Full quality gate fails
- `openspec validate --all` fails before or after archive
- Secret scan fails
- Any forbidden files modified

## Validation Commands

```bash
# Full quality gate
bash scripts/run_quality_gate.sh

# Pre-archive OpenSpec validation
openspec validate <change-id> --strict
openspec validate --all

# Archive
openspec archive <change-id>

# Post-archive OpenSpec validation
openspec validate --all

# Verify working tree
git status --short
git diff --stat

# Verify skipped integration = 0
uv run python -m pytest tests/integration/ --tb=short -q 2>&1 | tail -3
```

## Commit / Push Rules

Only commit and push on human approval.
- Commit message must include post-archive validation result
- Must confirm pre-archive and post-archive quality gate both pass

## Final Return Format

Return:
1. Pre-archive quality gate result
2. Post-archive OpenSpec validation result
3. Active changes count after archive (should be 0 or only other active changes)
4. Whether controller context was updated
5. `git status --short`
6. Whether any forbidden files were modified
7. Whether any stop conditions were triggered
