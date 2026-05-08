# Controller Harness - Bootstrap

## Controller Harness System

This project uses a **Controller Harness** — an AI orchestration system for managing development phases. When Claude Code starts, it can operate in two modes:

### Mode 1: Direct Development (Default)
Standard code changes, tests, and documentation.

### Mode 2: Controller Mode (Long-running phases)
For complex multi-step features. Follows `docs/harness/PHASE_LOOP.md` Controller rules.

**How to enter Controller Mode:**
- Human requests a phase implementation from `tasks.md`
- Human says "start phase N" or "run controller harness"

**Controller Mode reads these files (in order):**
1. `AGENTS.md` — Core rules
2. `docs/harness/PHASE_LOOP.md` — 7-step phase execution workflow
3. `docs/harness/PROJECT_CONTEXT.md` — Current phase and state
4. `docs/harness/skills/` — Reusable patterns and error fixes

**Controller Mode rules:**
- Never implement code directly — always delegate to subagent
- Use subagent types: `backend-engineer` (code), `code-reviewer` (review)
- Commit after: subagent success + module tests green
- Escalate immediately: quality gate fails, coverage drops, 3 retries exhausted

**Quick reference for Controller Mode:**
```
Phase execution: docs/harness/PHASE_LOOP.md
Current state: docs/harness/PROJECT_CONTEXT.md
Error patterns: docs/harness/skills/
Fix procedures: reports/harness/repair_playbook.md
Handoff outputs: subagent_results/
```

---

## 7-Step Phase Loop

| Step | Name | Role | What it does |
|------|------|------|--------------|
| 1 | PLANNER | project-director subagent | Create step-by-step plan with acceptance criteria |
| 2 | REQUIREMENTS | general-purpose subagent | Convert plan to requirements with field definitions |
| 3 | IMPLEMENTATION | backend-engineer subagent | Execute (never Controller for [CODE]) |
| 4 | REVIEW | code-reviewer subagent | Verify against requirements |
| 5 | DOC REVIEW | Controller | Verify documentation accuracy |
| 6 | EXPERIENCE | general-purpose subagent | Extract learnings, codify patterns |
| 7 | COORDINATION | Controller | Commit+push OR Fix Phase OR escalate |

**Fix Phase** (on failure): F1-Issue → F2-Root Cause → F3-Skill Codify → F4-Fix Plan → F5-Retry
**Max retries**: 3 per phase, then escalate.

## Task Type Markers

All tasks in tasks.md MUST have a type marker:

| Marker | Meaning | Who Executes |
|--------|---------|--------------|
| [CODE] | Code implementation | backend-engineer subagent |
| [DOC] | Documentation-only | Controller (self) |
| [DATA] | Data files | subagent or Controller |
| [TEST] | Adding/updating tests | backend-engineer subagent |
| [AUTO] | Automated verification | Controller (self) |

Unmarked = assume [CODE] (delegate).
