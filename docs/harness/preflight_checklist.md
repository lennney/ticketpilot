# Preflight Checklist — TicketPilot AI Development Harness

*Pre-batch verification steps to catch issues before they become failures.*

---

## 1. Repository Status

- [ ] Working tree is clean (`git status --short` shows no changes)
- [ ] No uncommitted changes that might be lost
- [ ] Git branch is correct (`master` or expected feature branch)

**If not clean**: Stash or commit changes before starting batch.

---

## 2. Branch Alignment

- [ ] Current branch matches expected target (master for harness batches)
- [ ] No worktree conflicts
- [ ] Remote is up to date (`git fetch` if needed)

**If behind**: Pull or rebase before starting batch.

---

## 3. Active OpenSpec Check

- [ ] No active OpenSpec change conflicts with planned work
- [ ] Active change files are in expected state
- [ ] Archived changes are not being modified

**Command**: `openspec validate --all`

---

## 4. Provider/Env Check (without printing secrets)

- [ ] Check if real provider is needed for this batch
- [ ] If `TICKETPILOT_LLM_PROVIDER=openai_compatible`:
  - Verify `TICKETPILOT_LLM_BASE_URL` is set
  - Verify `TICKETPILOT_LLM_API_KEY` is set
- [ ] If provider not configured and needed: note this in batch plan

**Do NOT**: Echo API key values or tokens.

---

## 5. DB Readiness (if integration tests require DB)

- [ ] Docker container is running: `docker compose ps`
- [ ] If DB unavailable: set `TICKETPILOT_SKIP_DB_TESTS=1` only after confirming
- [ ] Integration tests can run if DB is required

**If DB down**: Attempt start or skip with documented reason.

---

## 6. Skipped Test Check

- [ ] Run: `uv run pytest tests/integration/ -v --tb=short 2>&1 | grep -E "skipped|passed|failed"`
- [ ] Note if any integration tests are skipped
- [ ] For archive/push: skipped count must be 0

**If skipped > 0**: Document reason and determine if fix needed.

---

## 7. Secret Diff Check

- [ ] Run: `git diff | grep -i "sk-"` to check for API keys
- [ ] Verify no .env or .env.local content in changes
- [ ] Check no Authorization headers in code

**If secret found**: Remove immediately, do not commit.

---

## 8. Overclaim Check

- [ ] Search changed files for forbidden phrases:
  - "production-ready"
  - "real-world benchmark"
  - "真实线上效果"
  - "行业 benchmark"
  - "替代人工客服"
- [ ] Ensure reports have proper scope boundary wording

**If overclaim found**: Add scope disclaimer or remove claim.

---

## 9. Forbidden File Modifications Check

- [ ] Verify no changes to `src/ticketpilot/` (if batch is docs-only)
- [ ] Verify no changes to `data/` or frozen reports
- [ ] Verify no changes to archived Phase reports

**If forbidden change**: Revert or split batch appropriately.

---

## 10. Archived Report Protection

- [ ] Verify `reports/eval/` Phase 7-11 files are not modified
- [ ] Verify `reports/retrieval/` Phase 8-10 files are not modified
- [ ] Verify `openspec/changes/archive/` is not modified

**If archive modified**: Revert immediately.

---

## 11. Phase Boundary Check

- [ ] Review the batch name and scope
- [ ] Verify no scope creep into unrelated features
- [ ] Check that task.md tasks are marked as allowed/forbidden

**If scope creep**: Re-align with batch specification.

---

## 12. Quick Health Check Commands

```bash
# 1. Repo status
git status --short

# 2. OpenSpec validation
openspec validate --all

# 3. Integration test count
uv run pytest tests/integration/ --co -q 2>&1 | tail -5

# 4. No secrets in diff
git diff | grep -i "sk-" || echo "No secrets found"

# 5. Changed files check
git diff --name-only | grep -E "^(src/|tests/|data/)" || echo "No product changes"
```

---

## When Preflight Fails

1. **Repo not clean**: Commit or stash before proceeding
2. **OpenSpec fails**: Fix validation before batch
3. **DB unavailable**: Set skip flag or start DB
4. **Skipped tests**: Document reason, assess impact
5. **Secret found**: Remove immediately
6. **Overclaim found**: Add scope disclaimer
7. **Forbidden change**: Revert immediately
8. **Archive modified**: Revert immediately

**Do NOT proceed with batch until preflight issues are resolved.**