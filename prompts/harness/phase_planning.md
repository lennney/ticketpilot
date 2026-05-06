# Phase Planning Batch

## Context

A new OpenSpec change is being created. This batch produces the planning
artifacts: proposal, design, tasks, and spec deltas. No implementation,
no data changes, no runtime code changes.

Read `AGENTS.md` and `docs/technical/ai_development_harness.md` before
starting. Review prior phase changelog entries for context.

## Goal

Create a complete OpenSpec change directory with:
- `openspec/changes/<change-id>/proposal.md` — problem, goal, non-goals, scope,
  success criteria, risks, validation plan
- `openspec/changes/<change-id>/design.md` — architecture constraints, data flow,
  safety constraints, file manifest
- `openspec/changes/<change-id>/tasks.md` — phased task breakdown with checkboxes
- `openspec/changes/<change-id>/specs/<spec-name>/spec.md` — spec deltas
  using `## ADDED` / `## MODIFIED` / `## REMOVED` / `## RENAMED Requirements` headers
- `docs/changelog.md` — planning entry

## Allowed Files

- `openspec/changes/<change-id>/`
- `docs/changelog.md`
- `.claude/CLAUDE.md` (minor updates only)
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

## Stop Conditions

- Working tree is not clean (uncommitted changes from prior work)
- Forbidden file modified
- `openspec validate <change-id> --strict` fails
- Planning attempts to include implementation or data changes

## Validation Commands

```bash
# Scoped OpenSpec validation
openspec validate <change-id> --strict

# Verify no forbidden files
git diff --stat
```

Do NOT run `ruff` or `pytest` — no code or test files are modified
in a planning batch.

## Commit / Push Rules

Only commit and push on human approval. Include:
- Commit message with phase context
- Reference to the OpenSpec change ID
- No implementation changes

## Final Return Format

Return:
1. Added/modified file list
2. Proposal summary (problem, goal, non-goals)
3. Design summary (architecture constraints, data flow)
4. Task summary (how many phases, what each covers)
5. OpenSpec validation result
6. Whether controller context was updated
7. `git status --short`
8. Whether any forbidden files were modified
