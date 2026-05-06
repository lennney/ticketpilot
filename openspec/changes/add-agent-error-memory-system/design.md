# Design: Agent Error Memory and Repair Learning System

## Architecture

```
Error Memory Layer
├── error_memory.jsonl       # Structured error log (append-only)
├── repair_playbook.md       # Categorized repair procedures
├── agent_learning_rules.md   # Pre-batch rules
├── preflight_checklist.md   # Pre-batch verification
├── post_failure_reflection.md  # Failure analysis template
└── memory_audit.md          # Periodic audit template
```

## Error Memory Schema

Each entry in `error_memory.jsonl` contains:
- `id`: UUID for the entry
- `date`: ISO timestamp of when error occurred
- `phase`: Phase identifier (e.g., "Phase 10.7.5")
- `batch`: Batch name if applicable
- `error_type`: Category (e.g., "encoding", "validation", "secret", "coverage")
- `symptom`: What was observed
- `root_cause`: Why it happened
- `failed_command`: Exact command that failed
- `repair_action`: What was done to fix
- `validation_after_fix`: How repair was verified
- `prevention_rule`: Rule to prevent recurrence
- `recurrence_count`: Number of times this error type occurred
- `severity`: low / medium / high
- `promoted_to`: Where the lesson was promoted (playbook, rules, AGENTS.md, etc.)
- `related_files`: Files involved
- `commit_hash`: Git commit where error was observed
- `status`: active / resolved / stale

## Learning Rules

Rules promote lessons based on recurrence and severity:
1. **Same error twice** → update repair_playbook
2. **Preventable by test** → add or propose regression test
3. **Cross-phase impact** → promote to AGENTS.md only after confirmation or clear high-risk evidence
4. **Harness process improvement** → promote to preflight_checklist or agent_learning_rules

## Secret/Privacy Constraints

Error memory explicitly excludes:
- API keys, tokens, Authorization headers
- Full chat transcripts
- Raw provider responses
- Private or emotional conversation content

## No Chat Transcript Storage

The error memory does not store full conversation transcripts. Only:
- Error type and symptom
- Failed command
- Repair action
- Prevention rule

This keeps memory concise and auditable.

## Stale Memory Audit

Periodic audit of error memory:
- Remove obsolete rules (no longer applicable)
- Merge duplicate errors
- Mark resolved recurring issues
- Keep active rules under control (< 100 entries target)
- Ensure no secrets or private data
- Ensure AGENTS.md is not bloated
- Ensure repair_playbook remains actionable