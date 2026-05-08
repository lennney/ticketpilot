# CLAUDE.md Bootstrap for Controller Harness

This file provides the minimal bootstrap needed to activate the Controller Harness system.

## Quick Start

1. **Copy harness docs** to your project:
   ```bash
   cp -r harness-plugin/docs/harness <your-project>/docs/
   cp harness-plugin/skills/TEMPLATE.md <your-project>/docs/harness/skills/
   ```

2. **Copy bootstrap CLAUDE.md** template:
   ```bash
   cp harness-plugin/templates/claude.md <your-project>/.claude/CLAUDE.md
   ```

3. **Or run installer** (if supported):
   ```bash
   ./harness-plugin/scripts/install.sh --local
   ```

## File Organization

When installed, the harness creates:

```
<project>/
├── .claude/
│   └── CLAUDE.md              # Bootstrap (reads harness docs)
├── docs/harness/
│   ├── PHASE_LOOP.md          # 7-step workflow
│   ├── PROJECT_CONTEXT.md     # State tracking
│   ├── CONTROLLER_HARNESS_PRACTICE.md  # Core principles
│   └── skills/
│       ├── TEMPLATE.md        # Skill entry template
│       └── skill_*.md          # Reusable skills
├── subagent_results/          # Phase execution artifacts
├── reports/harness/          # Error memory, repair playbook
└── AGENTS.md                 # Core rules (create from template)
```

## Handoff Protocol

Each role transition follows a structured handoff:

| From | To | Output Location |
|------|----|-----------------|
| Planner | Requirements | `subagent_results/{phase}_plan.md` |
| Requirements | Implementation | `subagent_results/{phase}_requirements.md` |
| Implementation | Review | `subagent_results/{phase}_result.md` |
| Review | Controller | `subagent_results/{phase}_review.md` |

## Error Memory Format

When errors occur, log to `reports/harness/error_memory.jsonl`:

```json
{"timestamp":"2026-05-08T12:00:00Z","phase":"15.4","severity":"P1","type":"class_collision","symptom":"class name conflict","root_cause":"naming collision","fix_applied":"renamed to RetrievalTraceV2","resolved":false}
```

## Skills Codification

1. Error detected → check `docs/harness/skills/` for existing
2. If new pattern → create entry using TEMPLATE.md
3. If known pattern → update with new learning
4. Update `reports/harness/repair_playbook.md`
