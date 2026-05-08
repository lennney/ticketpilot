# Integrating with Existing AGENTS.md

If your project already has an AGENTS.md file, you don't need to replace it. Instead, add a reference to the Controller Harness system.

## Option 1: Add Bootstrap Reference

Add this line to your existing AGENTS.md header:

```markdown
> **Bootstrap**: This file is loaded by `.claude/CLAUDE.md`. On new clones, see `.claude/CLAUDE.md` for harness overview. For phase execution workflow, see `docs/harness/PHASE_LOOP.md`.
```

## Option 2: Add Controller Mode Section

Add this section to your AGENTS.md (replace existing Section 11 if any):

```markdown
## 11. Controller Mode (Harness System)

For complex multi-step features, the project uses a **Controller Harness** system.

**How to enter Controller Mode:**
- Human requests a phase from `openspec/changes/{active}/tasks.md`
- Human says "start phase N" or "run controller harness"

**Controller Mode reads these files (in order):**
1. `AGENTS.md` — Core rules (this file)
2. `docs/harness/PHASE_LOOP.md` — 7-step phase execution workflow
3. `docs/harness/PROJECT_CONTEXT.md` — Current phase and state
4. `docs/harness/skills/` — Reusable patterns and error fixes

**Key rules:**
- Controller NEVER implements code directly for [CODE] tasks
- Always delegate to `backend-engineer` subagent
- Commit after: subagent success + module tests green
- Max 3 retries per phase before escalation

**Quick reference:**
- Phase execution: docs/harness/PHASE_LOOP.md
- Current state: docs/harness/PROJECT_CONTEXT.md
- Error patterns: docs/harness/skills/
- Fix procedures: reports/harness/repair_playbook.md
```

## Option 3: Merge Complete Section

If your project is new to the harness system, add the complete Section 16 from the template:

```markdown
## 16. Phase Loop Workflow

Each phase (logical unit of work from tasks.md) follows a 7-step loop. See `docs/harness/PHASE_LOOP.md` for full workflow:

| Step | Role | What it does |
|------|------|--------------|
| 1 | Planner | Create step-by-step plan with acceptance criteria |
| 2 | Requirements Analysis | Convert plan to specific requirements |
| 3 | Implementation | Execute based on requirements (via subagent) |
| 4 | Review | Verify against requirements (code-reviewer) |
| 5 | Doc Review | Verify documentation accuracy |
| 6 | Experience Consolidation | Extract learnings, update rules/playbook |
| 7 | Controller Coordination | Orchestrate handoffs, check exit criteria, commit |

**Key rules**:
- Loop back: Review/Doc fails -> back to Implementation (max 3 retries, then escalate)
- Phase done: All steps pass -> commit + push -> next phase
- Controller never implements code directly (always delegate to subagent)
```

---

## File Locations for Controller Mode

```
<project>/
├── AGENTS.md                    # Core rules (add Controller Mode section)
├── .claude/CLAUDE.md            # Bootstrap (reads AGENTS.md + harness docs)
├── docs/harness/                # Controller harness docs
│   ├── PHASE_LOOP.md            # 7-step workflow
│   ├── PROJECT_CONTEXT.md       # State tracking
│   ├── CONTROLLER_HARNESS_PRACTICE.md  # Core principles (Chinese)
│   └── skills/                  # Reusable skill entries
│       └── TEMPLATE.md          # Skill entry template
├── subagent_results/            # Phase execution artifacts
├── reports/harness/             # Error memory, repair playbook
│   ├── error_memory.jsonl       # Real-time error logging
│   └── repair_playbook.md       # Categorized repair procedures
└── openspec/changes/{active}/   # OpenSpec state anchor
    └── tasks.md                 # Task tracking
```
