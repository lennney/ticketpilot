# Tasks: Agent Error Memory and Repair Learning System (Phase 12B)

## Phase Structure

Phase 12B is a harness/process improvement batch. Not a product runtime feature.

---

### Task 1 — OpenSpec Change Creation

**Scope**: Create OpenSpec change for error memory system.

**Allowed files**:
- `openspec/changes/add-agent-error-memory-system/` (all files)

**Forbidden files**:
- `src/ticketpilot/` (no product changes)
- `tests/` (no test changes)
- `data/` (no data changes)
- `reports/eval/` (frozen)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
openspec validate add-agent-error-memory-system --strict
openspec validate --all
uv run ruff check .
```

---

### Task 2 — Error Memory File

**Scope**: Create structured error memory JSONL.

**Allowed files**:
- `reports/harness/error_memory.jsonl` (new)

**Forbidden files**:
- Any product code
- Any frozen reports
- Full chat transcripts

**Content**: Derived from existing error_log.md entries only. No fake history.

---

### Task 3 — Repair Playbook

**Scope**: Create categorized repair procedures.

**Allowed files**:
- `reports/harness/repair_playbook.md` (new)

**Content**: Categories from existing errors and common harness issues.

---

### Task 4 — Active Learning Rules

**Scope**: Create pre-batch learning rules.

**Allowed files**:
- `docs/harness/agent_learning_rules.md` (new)

**Forbidden files**:
- Raw logs in AGENTS.md

---

### Task 5 — Preflight Checklist

**Scope**: Create pre-batch verification steps.

**Allowed files**:
- `docs/harness/preflight_checklist.md` (new)

---

### Task 6 — Post-Failure Reflection Template

**Scope**: Create failure analysis template.

**Allowed files**:
- `prompts/harness/post_failure_reflection.md` (new)

---

### Task 7 — Memory Audit Template

**Scope**: Create periodic audit template.

**Allowed files**:
- `prompts/harness/memory_audit.md` (new)

---

### Task 8 — AGENTS.md Update

**Scope**: Minimal update to reference learning system.

**Allowed files**:
- `AGENTS.md` (append only)

**Forbidden**:
- Do not add raw logs
- Do not bloat with detailed error entries

---

### Task 9 — Documentation and Logs

**Scope**: Update harness documentation and logs.

**Allowed files**:
- `docs/harness/chatgpt_controller_context.md`
- `docs/harness/controller_next_actions.md`
- `docs/harness/controller_session_log.md`
- `reports/harness/engineering_log.md`
- `reports/harness/validation_log.md`
- `reports/harness/error_log.md` (append if errors occur)
- `docs/changelog.md`

---

### Task 10 — Validation and Archive

**Scope**: Validate and archive OpenSpec change.

**Allowed files**:
- `openspec/` (standard archive workflow)

**Validation**:
```bash
openspec validate add-agent-error-memory-system --strict
openspec validate --all
uv run ruff check .
openspec archive add-agent-error-memory-system
```