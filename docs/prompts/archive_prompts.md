# Archive Prompts

## Overview

This document contains reusable prompt templates for the **Archive** phase of an OpenSpec-driven development workflow. Archive is the final step after all batches are complete, quality gate passes, and the change is fully accepted. These prompts cover documentation updates, archive readiness verification, the archive command sequence, post-archive validation, and clean working tree verification.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Final Documentation Update

### Purpose

Update changelog.md and phase_status.md to record the completion of a change or phase. These documentation updates are the permanent record of what was accomplished.

### When to Use

- After all batches of an OpenSpec change are complete and accepted
- Before running the archive command
- When a phase or stage reaches ACCEPTED status
- When updating project documentation to reflect current state

### Inputs to Provide

- **Change name**: The name of the OpenSpec change being finalized
- **Batch summaries**: What was implemented in each batch of this change
- **Test results**: Final test counts, coverage, and quality gate results
- **Deferred items**: What remains for future work
- **Phase status change**: What status to update (e.g., ACCEPTED)

### Forbidden Scope

- Do NOT make unsubstantiated claims about capabilities or readiness
- Do NOT use exaggerated language ("enterprise-grade," "production-proven")
- Do NOT omit deferred items or known limitations
- Do NOT report rounded or estimated test counts (use exact numbers)
- Do NOT reference commit SHAs that don't exist or are incorrect

### Prompt Template

```
I need to update documentation to finalize this change.

**Change**: [Change name]
**Change directory**: [openspec/changes/Change-name/]

**Batch summaries**:
- Batch 1: [description] — [N unit tests, N integration tests, coverage X%]
- Batch 2: [description] — [N unit tests, N integration tests, coverage X%]
- Batch N: [description] — [N unit tests, N integration tests, coverage X%]

**Final quality gate result**:
- Ruff: [PASS — 0 errors]
- Unit tests: [PASS — N passed, coverage X%]
- Integration tests: [PASS — N passed, 0 skipped]
- Spec validation: [PASS — N specs]
- Secret scan: [PASS — clean]

**Deferred items** still applicable:
- [Deferred item 1]
- [Deferred item 2]

Update the following:

### 1. Update Changelog (docs/changelog.md)

Add a new entry for this change following the existing format:

#### Format:
```
## YYYY-MM-DD — Batch/Phase: [Descriptive title]

### [Added/Changed/Fixed]
- [Item 1 with key detail]
- [Item 2 with key detail]

### Why
- [Rationale for the change]

### Tests
- Unit tests: [count] passed, coverage [X]%
- Integration tests: [count] passed, 0 skipped

### Evaluation
- [Summary of what the tests verify]
- [What is NOT verified (limitations)]

### Remaining risks
- [Risk 1]
- [Risk 2]
```

### 2. Update Phase Status (docs/phase_status.md)

Update the phase status document:
- Change status from "IN PROGRESS" to "ACCEPTED" (or appropriate status)
- Update summary with key metrics
- Ensure all referenced test counts match the final quality gate output

### 3. Verify Truth-in-Documentation

Apply truth-in-documentation rules to all new/modified content:
- [ ] Fake/prototype components labeled as non-production
- [ ] No claim of capabilities that don't exist
- [ ] Test counts are exact (not rounded)
- [ ] Deferred items are documented
- [ ] No aspirational language
- [ ] Commit references use actual SHAs
- [ ] Product boundary constraints are respected

### 4. Review Updated Files

- [ ] docs/changelog.md updated and consistent
- [ ] docs/phase_status.md updated and consistent
- [ ] No contradictory information between the two documents
```

### Expected Output

- Updated `docs/changelog.md` with a new entry following the established format
- Updated `docs/phase_status.md` with current acceptance status and metrics
- Truth-in-documentation rules applied to all new content
- Consistency verified between changelog and phase status

### Acceptance Checklist

- [ ] changelog.md updated with: date, description, changed items, why, test results, evaluation, risks
- [ ] phase_status.md updated with: status change, summary, key metrics
- [ ] Test counts are exact (from quality gate output, not estimated)
- [ ] Deferred items are listed where applicable
- [ ] No exaggerated or unsubstantiated claims
- [ ] Commit SHAs are used where references are needed
- [ ] Both documents agree on facts (no contradictions)

### Common Failure Modes

- **Inconsistent test counts**: changelog says "325 unit tests" but phase_status says "320." Always use the same source (final quality gate output).
- **Missing batch detail**: A change with 3 batches but the changelog only describes 1. Every batch should be summarized.
- **Aspirational language**: "Will scale to production" instead of "Proves pipeline mechanics with fake embeddings." Use present-tense, verifiable descriptions.
- **Deferred items omitted**: Only documenting what was implemented, not what was deliberately deferred. Deferred items provide important context.
- **Forgetting phase_status update**: Only updating changelog but not phase_status. Both must be updated.

---

## 2. OpenSpec Archive Readiness

### Purpose

Verify that an OpenSpec change is ready for archive by checking all prerequisites: complete tasks, passing quality gate, updated documentation, and reviewed by all required roles.

### When to Use

- Before running `openspec archive` or equivalent archive command
- After all implementation batches are complete
- When final quality gate passes but archive has not yet been run
- Before committing the archive

### Inputs to Provide

- **Change directory**: The OpenSpec change directory
- **Tasks file**: tasks.md for the change
- **Quality gate output**: Most recent full quality gate run
- **Reviewer sign-offs**: Evidence of approval from all roles

### Forbidden Scope

- Do NOT proceed to archive if quality gate failed
- Do NOT proceed if tasks are incomplete
- Do NOT proceed if documentation is not updated
- Do NOT proceed if the working tree has unexpected dirty files
- Do NOT skip any prerequisite check

### Prompt Template

```
I need to verify archive readiness for an OpenSpec change.

**Change**: [Change name]
**Change directory**: [openspec/changes/Change-name/]

Archive readiness checklist:

### Blocking Checks (ALL MUST PASS)
- [ ] All tasks in tasks.md are marked [x] (complete)
  - [ ] Task evidence verified: each completed task has implementation
- [ ] Quality gate passes (most recent run):
  - [ ] Ruff: 0 errors
  - [ ] Unit tests: all pass, coverage >= [threshold]%
  - [ ] Integration tests: all pass, 0 skipped
  - [ ] Spec validation: all pass
  - [ ] Secret scan: clean
- [ ] docs/changelog.md updated with change summary
- [ ] docs/phase_status.md updated with acceptance status
- [ ] openspec validate --all passes
- [ ] All reviewer sign-offs obtained:
  - [ ] Project Director
  - [ ] System Architect
  - [ ] QA Evaluator
  - [ ] Phase Supervisor

### Non-Blocking Checks (SHOULD pass)
- [ ] git status --short shows no unexpected files
- [ ] All change-related files are committed
- [ ] No deferred items from the change are unaddressed (unless explicitly deferred)
- [ ] Archive command is available: `openspec archive --help` (or equivalent)

### Summary
- **READY FOR ARCHIVE**: All blocking checks pass
- **NOT READY**: [list specific blocking failures]

If NOT READY, provide remediation steps for each failure.
```

### Expected Output

- A structured readiness report with blocking and non-blocking checks
- Overall READY FOR ARCHIVE or NOT READY status
- If NOT READY: specific blocking failures with remediation steps
- Guidance on next steps after readiness is confirmed

### Acceptance Checklist

- [ ] All tasks are marked complete
- [ ] Quality gate passes
- [ ] changelog.md is updated
- [ ] phase_status.md is updated
- [ ] openspec validate --all passes
- [ ] All four reviewer roles have approved
- [ ] git status shows clean or expected-only changes
- [ ] Archive command is verified available

### Common Failure Modes

- **Assuming readiness without checking**: "Everything should be done" without running through the checklist. Each check must be explicitly verified.
- **Outdated quality gate**: The quality gate passed last week, but new changes since then may have broken it. Run the quality gate fresh.
- **Missing reviewer sign-off**: One role didn't formally approve. Get explicit sign-off from each role before proceeding.
- **Phase status mismatch**: phase_status still shows "IN PROGRESS" when the change is complete. Update before archive.
- **Uncommitted change-related files**: Documentation or other files that were modified but not yet committed. Stage and commit before archive.

---

## 3. Archive Command Sequence

### Purpose

Execute the archive command sequence to formally archive the OpenSpec change, moving it from the active changes directory to the archive.

### When to Use

- When archive readiness has been verified
- After final quality gate passes and documentation is updated
- As the final step before the archive commit

### Inputs to Provide

- **Change name**: The name of the change to archive
- **Archive command**: The command to run (e.g., `openspec archive <change-name>`)
- **Post-archive verification steps**: How to confirm the archive succeeded

### Forbidden Scope

- Do NOT run the archive command without verifying readiness first
- Do NOT skip post-archive validation
- Do NOT modify archived files after archive
- Do NOT use a different archive command than the project standard

### Prompt Template

```
I need to execute the archive command sequence for this change.

**Change**: [Change name]
**Archive command**: `openspec archive [Change-name]`

**Pre-flight checks confirmed** (run archive-readiness first):
- [ ] All tasks complete
- [ ] Quality gate passes
- [ ] Documentation updated
- [ ] All reviewer approvals obtained

Execute the following sequence:

### Step 1: Run openspec validate --all (final check)
```bash
openspec validate --all
```
- Must return: ALL SPECS PASSED
- If any spec fails: stop, fix the issue, re-validate
- If OpenSpec CLI is not available: note the warning and proceed

### Step 2: Run the Archive Command
```bash
openspec archive [Change-name]
```
Expected result:
- Change directory moves from `openspec/changes/[Change-name]/` to archive location
- No error output
- If the command fails: investigate and resolve before proceeding

### Step 3: Verify Archive
```bash
# Check the change is no longer in active changes
ls openspec/changes/[Change-name]/ 2>&1 || echo "Directory moved (expected)"

# Check the change exists in archive
ls openspec/changes/archive/ | grep [Change-name] || echo "Not found in archive"
```

### Step 4: Check Promoted Specs (if applicable)
If the change has promoted specs:
```bash
ls openspec/specs/[component]/ | grep [spec-name]
```
Verify promoted specs exist at the expected paths.

### Step 5: Run openspec validate --all (post-archive)
```bash
openspec validate --all
```
- All specs must still pass after archive

### Step 6: Check git status
```bash
git status --short
```
- Should show: archived files, updated docs, and promoted specs
- Should NOT show: unexpected dirty files

### Summary
- Archive command: [SUCCESS / FAILED]
- Post-archive validate: [PASS / FAIL]
- Git status: [CLEAN / DIRTY]
- Ready for archive commit: [YES / NO]
```

### Expected Output

- Archive command executed successfully
- Post-archive validation confirms the archive was successful
- openspec validate --all passes post-archive
- git status shows expected changed files
- Clear summary of archive success or failure

### Acceptance Checklist

- [ ] Pre-flight checks confirmed before archive
- [ ] openspec validate --all passes before archive
- [ ] Archive command executes without error
- [ ] Change directory is moved from active changes to archive
- [ ] openspec validate --all passes after archive
- [ ] git status shows expected files only
- [ ] Promoted specs (if applicable) are in place

### Common Failure Modes

- **Archive command not found**: The `openspec` CLI is not installed. Install it before proceeding, or document the workaround.
- **Archive command fails**: The command may fail if the change directory has unexpected structure. Investigate the error before retrying.
- **Forgotten pre-flight**: Running archive without verifying readiness first. Always run readiness checks before the archive command.
- **Post-archive validation skipped**: Assuming the archive worked without verifying. Always run validate and git status after archive.
- **Archive moves but files remain**: The archive command partially succeeded, leaving some files behind. Check both the active changes directory AND the archive.

---

## 4. Post-Archive Validation

### Purpose

Validate that the archive was successful and the system is in a consistent state after archiving. This catches any issues introduced by the archive process itself.

### When to Use

- Immediately after running the archive command
- Before making the archive commit
- When the archive command produced warnings or unexpected output
- When validating that all archived specs are findable

### Inputs to Provide

- **Change name**: The name of the archived change
- **Archive output**: Output from the archive command
- **Validation commands**: Commands to run for post-archive checks

### Forbidden Scope

- Do NOT commit the archive without post-archive validation
- Do NOT skip any validation check
- Do NOT ignore warnings from the archive command

### Prompt Template

```
I need to validate the archive was successful for this change.

**Change**: [Change name]
**Archive command output**:
```
[paste archive command output]
```

Run the following validation checks:

### Check 1: Change Directory Moved
```bash
# Active changes should NOT contain the archived change
if [ -d "openspec/changes/[Change-name]" ]; then
  echo "WARNING: Change still in active changes"
else
  echo "OK: Change removed from active changes"
fi
```

### Check 2: Change Exists in Archive
```bash
# Archived change SHOULD exist in archive
if ls openspec/changes/archive/ | grep -q "[Change-name]"; then
  echo "OK: Change found in archive"
else
  echo "WARNING: Change not found in archive"
fi
```

### Check 3: Validates After Archive
```bash
openspec validate --all
```
Expected: ALL SPECS PASSED

### Check 4: Promoted Specs Present (if applicable)
```bash
# List promoted specs
ls -la openspec/specs/ 2>/dev/null
```
Verify that any specs promoted during this change exist.

### Check 5: No Corrupted Files
```bash
# Quick integrity check on archived files
openspec validate openspec/changes/archive/[Change-name]/specs 2>/dev/null || echo "Warning: could not validate archived specs"
```

### Check 6: Git Status
```bash
git status --short
```
Expected: shows only the files that should be committed (archive changes, doc updates)

### Results Summary
- Change removed from active: [YES/NO]
- Change found in archive: [YES/NO]
- openspec validate --all: [PASS/FAIL]
- Promoted specs present: [YES/NO/NA]
- No corrupted files: [YES/NO/WARNING]
- Git status clean: [YES/NO]
- **Overall: PASS / FAIL**
```

### Expected Output

- Results for each validation check
- Overall PASS or FAIL status
- If FAIL: specific checks that failed, with remediation steps
- Clear go/no-go for making the archive commit

### Acceptance Checklist

- [ ] Change directory is no longer in active changes
- [ ] Change directory is found in archive
- [ ] openspec validate --all passes post-archive
- [ ] Promoted specs (if applicable) exist at expected paths
- [ ] No corrupted or incomplete files in the archive
- [ ] git status shows expected files only

### Common Failure Modes

- **Archive moved but validation fails**: The archive command succeeded but the remaining specs don't validate. This may indicate a spec dependency issue. Investigate before committing.
- **Partial archive**: Some files were moved but others remain in the active directory. Check both locations.
- **Spec validation regression**: A spec that passed before archive now fails because the archive removed a dependency. Check spec interdependencies.
- **Promoted specs missing**: Specs that should have been promoted to `openspec/specs/` are not there. Manual promotion may be needed.
- **Unexpected dirty files**: Files outside the expected archive/doc scope are modified. Investigate before committing.

---

## 5. Clean Working Tree Verification

### Purpose

Verify that the working tree is clean after archiving — no untracked files, no uncommitted changes, and no unexpected modifications. This confirms the archive process completed without side effects.

### When to Use

- After making the archive commit
- Before starting a new change or batch
- When switching contexts between changes
- When investigating potential side effects of the archive process

### Inputs to Provide

- **Git status output**: Current state of the working tree
- **Expected files**: Files that should be staged or modified
- **Archive change summary**: What files the archive process should have affected

### Forbidden Scope

- Do NOT start a new change with a dirty working tree
- Do NOT ignore unexpected files (even "small" ones)
- Do NOT use `git add -A` to hide unexpected files in the commit
- Do NOT proceed to the next task without resolving unexpected state

### Prompt Template

```
I need to verify a clean working tree after archiving.

**Change**: [Change name]
**Archive commit message**: `[type]: [description]`

**Files expected to be modified by this archive**:
- [Expected file 1] — [reason]
- [Expected file 2] — [reason]
- [Expected file 3] — [reason]

**Git status output**:
```
[paste git status --short output]
```

Verification process:

### Step 1: Check git status

- If OUTPUT IS EMPTY: Tree is clean. Archive commit already made. Proceed.
- If OUTPUT SHOWS UNTRACKED FILES: Verify they are expected from the archive process.

### Step 2: Categorize Each Entry
For each line in git status:
```
[Status code] [file path]
```

Classify each:
- **Expected from archive**: changelog.md, phase_status.md, archived change files, promoted specs
- **Expected from pre-archive work**: Any implementation files that were intentionally not committed yet
- **Unexpected**: Files that should not be modified, or files not related to the current change

### Step 3: Verify Expected Files
- Are all expected files present in git status?
- Are there more files than expected? (potential side effects)

### Step 4: Resolve Unexpected Files
For each unexpected file:
- Is it a build artifact? Add to .gitignore.
- Is it a generated file? Determine if it should be committed or ignored.
- Is it a leftover from a previous change? Clean it up.
- Is it a side effect of the archive? Investigate and fix.

### Step 5: Final State
- Work in progress (WIP) files: [count]
- Unexpected files: [count]
- **Clean tree**: [YES if no WIP and no unexpected files; NO otherwise]

**Result**: CLEAN / HAS WIP / UNEXPECTED FILES

If NOT CLEAN: provide remediation steps for each unexpected file.
```

### Expected Output

- A categorization of all files in git status
- Clean tree: YES/NO with rationale
- If NOT CLEAN: specific files that need attention and remediation steps
- Guidance on whether to commit, ignore, or clean up each file

### Acceptance Checklist

- [ ] git status --short is empty (fully clean) or shows only expected files
- [ ] All expected archive files are committed
- [ ] No unexpected files are present
- [ ] No build artifacts, generated files, or leftover files are untracked
- [ ] Working tree is ready for the next change or batch

### Common Failure Modes

- **Untracked build artifacts**: Files generated by pytest (`.coverage`, `__pycache__`, `.pytest_cache`) are untracked. These should be in .gitignore.
- **Leftover files from previous work**: A feature branch left behind files that were never committed. Clean these up before starting new work.
- **Modified but uncommitted archive files**: The archive process modified files (changelog, phase_status) but didn't commit them. Stage and commit.
- **IDE or editor files**: `.vscode/`, `.idea/`, or other editor-specific files that should be in .gitignore.
- **Assuming empty git status**: "Looks clean" is not a substitute for running `git status --short`. Always run the command explicitly.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Final Documentation Update | Update changelog and phase status | Pre-archive, phase completion |
| OpenSpec Archive Readiness | Verify all prerequisites for archive | Before archive command |
| Archive Command Sequence | Execute the archive command | After readiness verification |
| Post-Archive Validation | Validate archive success | After archive command, before commit |
| Clean Working Tree Verification | Verify clean tree after archive commit | Post-archive commit, pre-next-task |
