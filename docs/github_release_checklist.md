# GitHub Release Checklist

> Pre-publication checklist for TicketPilot portfolio release.
> Run through all items before pushing to a public GitHub repository.

---

## 1. Repository Hygiene

- [ ] `.gitignore` covers: `__pycache__/`, `*.pyc`, `.coverage*`, `.pytest_cache/`, `.claude/`, `.venv/`, `*.egg-info/`, `.ruff_cache/`, `dist/`, `build/`
- [ ] No local artifact files tracked by git (`.coverage.*`, worktrees, temp files)
- [ ] No large binary files committed (model files, datasets >10MB)
- [ ] `git status` shows clean working tree (or only intended uncommitted changes)

**Commands:**
```bash
git status
git check-ignore -v .coverage.xyz123  # verify coverage files are ignored
```

---

## 2. No Secrets or Credentials

- [ ] No API keys, tokens, passwords in committed files
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded credentials in source code
- [ ] `git ls-files | xargs grep -l 'sk-[A-Za-z0-9]\{20,\}'` returns empty (OpenAI keys etc.)

**Commands:**
```bash
# Check for common secret patterns in tracked files
git grep -n 'password\|secret\|api_key\|API_KEY' -- ':!.env.example' ':!*.md'
```

---

## 3. .env.example

- [ ] `.env.example` exists and is tracked
- [ ] All required environment variables documented
- [ ] Placeholder values used (not real credentials)
- [ ] Optional/commented-out variables clearly marked
- [ ] Matches actual code usage (check `os.getenv()` calls in source)

---

## 4. README

- [ ] `README.md` (Chinese) is complete: what, workflow, features, architecture, quick start, docs map, limitations, roadmap, safety boundary
- [ ] `README.en.md` (English) is a synchronized translation
- [ ] No overstated or production-level claims
- [ ] Links to demo guide (`docs/demo/README.md`) and release checklist
- [ ] Links to technical docs and portfolio materials
- [ ] English README links back to Chinese as primary

---

## 5. Demo Guide

- [ ] `docs/demo/README.md` complete with 3 demo lines (A: normal, B: high-risk, C: evaluation)
- [ ] `docs/demo/sample_tickets.md` covers 7 ticket types
- [ ] All Python code snippets are runnable (tested)
- [ ] Demo guide explicitly states: local demo only, seed data only, fake embedding limitation, no auto-send
- [ ] "Do not claim" list included

---

## 6. Quality Gate

- [ ] Ruff passes (no lint errors)
- [ ] All unit tests pass
- [ ] All integration tests pass (no skips)
- [ ] Coverage ≥ 70%
- [ ] OpenSpec validation passes (no active changes unarchived)

**Command:**
```bash
./scripts/run_quality_gate.sh
```

---

## 7. OpenSpec Active Changes

- [ ] All active OpenSpec changes are complete and archived
- [ ] `openspec/ validate` passes with zero active changes
- [ ] No unarchived feature branches or in-progress work

**Command:**
```bash
uv run openspec validate 2>&1 | tail -20
```

---

## 8. Limitations and Roadmap

- [ ] README limitations section is honest and complete (seed data, fake embeddings, no LLM, no auto-send, MVP console)
- [ ] README roadmap reflects realistic future directions, not promises
- [ ] No claims of production readiness, enterprise performance, or semantic retrieval quality
- [ ] Safety boundary section (no auto-send) is prominently displayed

---

## 9. Screenshots / GIFs

- [ ] Streamlit console screenshot(s) captured
- [ ] Streamlit console screenshot(s) tracked in git (e.g., `docs/demo/screenshots/`)
- [ ] Screenshots show: ticket list, evidence candidates, draft reply, review actions (Approve/Edit/Escalate/Reject)
- [ ] GIF (optional): end-to-end pipeline run or evaluation report

**Note:** Add screenshots after running the demo guide on your local machine.

---

## 10. Final Pre-Push Commands

Run these in order before pushing:

```bash
# 1. Final git status check
git status

# 2. Final quality gate
./scripts/run_quality_gate.sh

# 3. Scan for secrets (basic check)
git grep -n 'password\|secret\|api_key\|API_KEY' -- ':!.env.example' ':!*.md' || echo "No secrets found"

# 4. Check for overstated claims
git grep -in 'production-ready\|enterprise\|semantic\|real-world performance' -- '*.md' || echo "No overstated claims"

# 5. Verify demo guide accuracy
uv run python -c "
from ticketpilot.pipeline import run_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(original_text='我要退款，订单号：123456', submitted_at=datetime.utcnow())
result = run_pipeline(ticket)
assert result.classification.intent.value == 'refund'
print('Demo guide smoke test: OK')
"

# 6. Verify eval CLI works
uv run python scripts/run_eval.py --help > /dev/null 2>&1 && echo "Eval CLI: OK"

# 7. Verify streamlit console imports
uv run python -c "import streamlit; print('Streamlit import: OK')"

# 8. Verify both READMEs are consistent
echo "README.md lines: $(wc -l < README.md)"
echo "README.en.md lines: $(wc -l < README.en.md)"
```

---

## Quick Reference

| Area | Key File(s) | Status |
|------|-------------|--------|
| Repo hygiene | `.gitignore` | □ |
| Secrets | — | □ |
| Environment | `.env.example` | □ |
| Main docs | `README.md`, `README.en.md` | □ |
| Demo guide | `docs/demo/README.md`, `docs/demo/sample_tickets.md` | □ |
| Code quality | `scripts/run_quality_gate.sh` | □ |
| Spec tracking | `openspec/` | □ |
| Limitations | `README.md §8` | □ |
| Screenshots | `docs/demo/screenshots/` | □ |

---

> *One final check: if this repo were public right now, would you be comfortable with any visitor reading every file? If not, fix it before pushing.*
