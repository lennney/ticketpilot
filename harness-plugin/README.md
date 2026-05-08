# Controller Harness Plugin for OpenSpec

A reusable AI orchestration system that provides a 7-step phase execution workflow with subagent delegation and skill codification.

## Overview

The Controller Harness is a workflow system designed for managing complex multi-step development phases. It provides:

- **7-Step Phase Loop**: Planner -> Requirements -> Implementation -> Review -> Doc Review -> Experience -> Coordination
- **Subagent Delegation**: Role-based task execution (backend-engineer, code-reviewer, etc.)
- **Fix Phase Workflow**: Systematic failure handling with max 3 retries
- **Skill Codification**: Pattern-based learning from errors
- **Context Management**: Project state tracking, handoff protocols, compression recovery

## Installation

### Option 1: Global Installation (Recommended)

```bash
# Clone or copy the harness-plugin directory
git clone https://github.com/len/ticketpilot.git

# Run installer
cd harness-plugin
./scripts/install.sh --global
```

This installs to `~/.claude/skills/controller-harness/`.

### Option 2: Project-Level Installation

```bash
cd your-project
git clone https://github.com/len/ticketpilot.git harness-plugin-temp
cp -r harness-plugin-temp/harness-plugin .claude/skills/
rm -rf harness-plugin-temp
```

### Option 3: OpenSpec Plugin Install (Future)

```bash
openspec plugin install controller-harness
```

## Components

### 1. Phase Loop (docs/PHASE_LOOP.md)

The core 7-step workflow:

```
[1] PLANNER          -> Create step-by-step plan
[2] REQUIREMENTS     -> Convert to specific requirements  
[3] IMPLEMENTATION   -> Execute (delegate to subagent for [CODE])
[4] REVIEW           -> Verify against requirements
[5] DOC REVIEW       -> Verify documentation
[6] EXPERIENCE       -> Extract learnings, codify skills
[7] COORDINATION     -> Commit+push or Fix Phase
```

### 2. Subagent Delegation System

| Task Type | Who Executes | Controller Role |
|-----------|--------------|-----------------|
| [CODE] | backend-engineer subagent | Orchestrate + review |
| [DOC] | Controller (self) | Execute directly |
| [DATA/TEST] | Dispatch appropriately | Orchestrate |

### 3. Fix Phase Workflow

When Review or Doc Review fails:

```
F1: Issue Documentation -> F2: Root Cause Analysis 
  -> F3: Skill Codification -> F4: Fix Plan -> F5: Retry Decision
```

Max 3 retries before escalation.

### 4. Skill System

Skills are reusable pattern entries in `skills/`:

- Template: `skills/TEMPLATE.md`
- Created skills: `skills/skill_*.md`
- Pattern types: error_fix, best_practice, anti_pattern

## File Structure

```
harness-plugin/
├── openspec-plugin.json      # Plugin manifest
├── README.md                  # This file
├── scripts/
│   └── install.sh            # Installation script
├── docs/
│   ├── PHASE_LOOP.md          # 7-step workflow definition
│   ├── PROJECT_CONTEXT.md      # State tracking template
│   └── CONTROLLER_HARNESS_PRACTICE.md  # Core principles
├── skills/
│   ├── TEMPLATE.md            # Skill entry template
│   ├── skill_workflow_phase_loop.md
│   ├── skill_workflow_subagent_delegation.md
│   ├── skill_requirements_pm_style.md
│   └── ... (additional skills)
└── templates/
    └── claude.md              # Bootstrap CLAUDE.md
```

## Usage

### 1. Enter Controller Mode

Say "start phase N" or "run controller harness" to enter Controller Mode.

### 2. Execute a Phase

1. Read `openspec/changes/{active}/tasks.md` for the current task
2. Follow the 7-step phase loop
3. Delegate [CODE] tasks to `backend-engineer` subagent
4. Review results with `code-reviewer` subagent
5. On failure: enter Fix Phase before retry
6. Commit after all steps pass

### 3. Create Skills from Errors

When discovering patterns:
1. Check `skills/` for existing entries
2. Create new entry using `skills/TEMPLATE.md`
3. Update `repair_playbook.md`

## Requirements

- OpenSpec CLI (https://github.com/openspecio/openspec)
- Claude Code or compatible AI assistant

## License

MIT
