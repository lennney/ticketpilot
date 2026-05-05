# Post-Failure Repair Batch

## Context

A validation or quality gate check failed. This batch diagnoses the root
cause and applies a minimal fix. The goal is to restore the working state
without introducing new features, refactoring, or scope creep.

Read `AGENTS.md` before starting. Read the failure output carefully.
Identify the root cause, not just the symptom.

## Goal

1. Reproduce the failure
2. Identify root cause (not just symptom)
3. Apply minimal fix (no refactoring, no feature additions)
4. Verify fix passes the failing check
5. Verify no regressions in other checks

## Allowed Files

- Whatever is needed to fix the specific failure, but:
  - Minimal changes only
  - No feature additions
  - No refactoring beyond the fix

## Forbidden Files

- `data/` (unless data corruption caused the failure)
- `reports/` (unless report generation logic is wrong)
- `docs/portfolio/`
- Phase 7/8/9 baseline reports (always forbidden)

## Stop Conditions

- `|| true` or any failure suppression added
- Coverage threshold lowered
- `# noqa` added without justification
- Integration skip count increases
- Fix introduces new features or refactoring beyond the bug
- Root cause not identified before applying fix
- Forbidden file modified

## Validation Commands

```bash
# Reproduce the specific failure
<the failing command from the quality gate output>

# Run module-level tests for affected modules
uv run pytest tests/unit/test_<affected_module>.py -v --tb=short

# Run full quality gate after fix
bash scripts/run_quality_gate.sh

# OpenSpec scoped validation
openspec validate <change-id> --strict

# Secret scan
grep -r "sk-" src/ --include="*.py"

# Verify fix is minimal
git diff --stat
```

## Commit / Push Rules

Only commit and push on human approval.
- Commit message must specify root cause and fix
- Must include: "Before: <symptom>. Root cause: <cause>. Fix: <fix>."
- Must confirm quality gate passes after fix

## Final Return Format

Return:
1. Root cause description
2. Fix applied (files changed and what changed)
3. Verification that the failing check now passes
4. Quality gate result (if applicable)
5. `git status --short`
6. Whether any forbidden files were modified
7. Whether any stop conditions were triggered
