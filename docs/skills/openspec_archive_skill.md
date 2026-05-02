# OpenSpec Archive Skill

## Purpose

Finalize a completed OpenSpec change by running final validation, updating documentation, archiving the change directory, and verifying a clean working tree. This is the last step in the spec-driven development lifecycle and ensures every change leaves a traceable, reviewable record.

## When to Use

- After all batches of an OpenSpec change have been implemented and quality-gated
- Before moving to the next OpenSpec change
- When a change has been fully accepted and its spec requirements are met
- Do NOT archive a change that has incomplete batches, unresolved quality gate failures, or dirty working tree state

## Required Inputs

- Completed and accepted OpenSpec change with all tasks marked done in `tasks.md`
- Quality gate passing (ruff, unit tests, integration tests with 0 skips, OpenSpec validate, secret scan)
- `docs/changelog.md` updated with all batch summaries for the change
- `docs/phase_status.md` updated with current acceptance status
- Promoted specs in `openspec/specs/` up to date

## Allowed Scope

- Running `openspec validate --all` (final validation)
- Updating `docs/changelog.md` (adding final changelog entry)
- Updating `docs/phase_status.md` (marking stage as ACCEPTED)
- Running `openspec archive <change-name>` to archive the change
- Verifying `git status --short` shows clean working tree
- Committing the archived change with a descriptive message

## Forbidden Scope

- Do NOT archive a change with failed or skipped quality gate
- Do NOT archive a change with incomplete tasks
- Do NOT archive a change with dirty working tree (uncommitted changes unrelated to the change)
- Do NOT archive a change that has not been validated with `openspec validate --all`
- Do NOT delete or modify archived change directories after archive
- Do NOT skip changelog or phase_status updates

## Step-by-Step Procedure

1. **Verify all tasks are complete**
   - Open `openspec/changes/<change-name>/tasks.md`
   - Confirm every task is marked `[x]`
   - No remaining `[ ]` tasks for any phase

2. **Run final quality gate**
   - `bash scripts/run_quality_gate.sh`
   - Must exit 0: Ruff clean, all unit tests pass (>=70% coverage), integration tests pass with 0 skips, OpenSpec validate passes, secret scan clean
   - If it fails, fix the issue before proceeding

3. **Run full OpenSpec validation**
   - `openspec validate --all`
   - All specs must pass
   - If any fail, determine whether the spec or implementation needs fixing

4. **Update changelog**
   - Add a changelog entry in `docs/changelog.md` summarizing the change: what was implemented, why, test/evaluation results, and remaining risks
   - Use the format from existing entries: date, change name, Changed/Why/Tests/Evaluation/Remaining risks sections

5. **Update phase status**
   - Update `docs/phase_status.md` with the acceptance result for the stage(s) completed by this change
   - Mark as ACCEPTED with summary of what was implemented and key metrics

6. **Archive the change**
   - `openspec archive <change-name>`
   - This moves the change from `openspec/changes/<change-name>/` to the archive location
   - Verify the move was successful

7. **Check git status**
   - `git status --short`
   - Should show no dirty files (all changes from the change are committed)
   - If there are uncommitted files: stage, commit, then re-check

8. **Commit the archive**
   - `git add <updated files>`
   - `git commit -m "chore: archive <change-name> OpenSpec change"`
   - Verify with `git status --short`

## Acceptance Checklist

- [ ] All tasks in tasks.md are marked complete
- [ ] `bash scripts/run_quality_gate.sh` exits 0
- [ ] `openspec validate --all` passes
- [ ] `docs/changelog.md` updated with change summary
- [ ] `docs/phase_status.md` updated with acceptance status
- [ ] `openspec archive <change-name>` completed successfully
- [ ] `git status --short` shows clean working tree
- [ ] Final commit made with message `chore: archive <change-name> OpenSpec change`
- [ ] No `|| true` used in quality gate
- [ ] No coverage threshold lowered

## Common Failure Modes

- **Archiving before quality gate passes**: The archive is permanent. If you archive a change with a failing quality gate, the record shows incomplete work. Always run the quality gate last.
- **Forgetting to update changelog.md**: The changelog is the primary navigation for understanding what changed and why. An archived change without a changelog entry is effectively invisible.
- **Forgetting to update phase_status.md**: The phase status document tracks overall project progress. Without updates, it becomes stale and untrustworthy.
- **Dirty working tree after archive**: If `git status` shows unexpected dirty files after archive, the change had side effects that were not committed. Investigate and commit or revert before proceeding.
- **Spec drift during implementation**: If `openspec validate --all` fails at archive time because the spec and implementation diverged during implementation, it indicates a process failure. Fix the spec or the code, whichever is wrong.
- **Archive commit not made**: The `openspec archive` command moves files but does not create a git commit. Always commit the archive explicitly.

## Reusable Claude Code Prompt Template

```
I have completed all batches for the OpenSpec change `<change-name>`.

Finalize and archive the change following this procedure:

1. Verify all tasks in `openspec/changes/<change-name>/tasks.md` are marked complete
2. Run `bash scripts/run_quality_gate.sh` -- confirm exit 0
3. Run `openspec validate --all` -- confirm all pass
4. Update `docs/changelog.md` with a summary of the change
5. Update `docs/phase_status.md` with the new stage status
6. Run `openspec archive <change-name>`
7. Check `git status --short` for clean state
8. Commit with message: `chore: archive <change-name> OpenSpec change`

Critical rules:
- Do NOT archive if quality gate fails
- Do NOT archive if OpenSpec validate fails
- Do NOT skip changelog or phase_status updates
- Do NOT leave dirty files after archive
- Do NOT use `|| true`
```

## TicketPilot Example

The `add-human-review-console` OpenSpec change was archived with this procedure:

1. **Tasks verified**: All 3 batches (schema + store, Streamlit console, integration tests + docs) marked complete in `tasks.md`

2. **Final quality gate**: Passed with 325 unit tests (80.25% coverage), 74 integration tests (0 skipped), Ruff clean, OpenSpec validate 11/11, secret scan clean

3. **OpenSpec validate --all**: All 11 specs passed

4. **Changelog updated**: Added entries for Batches 1, 2, and 3 under "2026-05-02" with full Changed/Why/Tests/Evaluation/Remaining risks sections

5. **Phase status updated**: Stage 1D marked as ACCEPTED with full summary

6. **Archive command**: `openspec archive add-human-review-console`

7. **Git status**: Clean -- no unexpected dirty files

8. **Commit**: `git commit -m "chore: archive human review console OpenSpec change"` (commit `def4afa`)

The archive ensured every design decision, task, and test result was permanently recorded and traceable.
