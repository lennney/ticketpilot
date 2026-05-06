# Agent Learning Rules — TicketPilot AI Development Harness

*Rules to read before every harness batch. These are stable, cross-phase principles.*

---

## Non-Negotiable Rules

### Never treat skipped integration tests as pass
Integration tests skipped > 0 cannot be counted as a passing quality gate for archive or push. If DB is unavailable, use `TICKETPILOT_SKIP_DB_TESTS=1` only after confirming DB check was attempted.

### Never use `|| true` to hide failure
Every command that fails must be visible. Hiding failures with `|| true` prevents proper error diagnosis and leads to undetected regressions.

### Never lower coverage threshold to pass
The 70% minimum coverage threshold is enforced. If coverage drops, add tests or remove dead code — do not lower the bar.

### Never commit .env/.env.local/API keys
The `.env` and `.env.local` files are gitignored. API keys, tokens, and Authorization headers must never appear in source code, tests, or commit messages.

---

## Error Response Rules

### When the same error occurs twice, update repair_playbook
If an error type appears in error_memory.jsonl and occurs again, add or update the repair procedure in `reports/harness/repair_playbook.md`.

### When an error can be prevented by a test, add or propose a regression test
If an error reveals a missing test case, add a unit or integration test to prevent regression. Document the test proposal in the error memory entry.

### When a rule affects all future batches, promote to AGENTS.md
Only after confirmation or clear high-risk evidence should a rule be promoted from repair_playbook or learning rules to AGENTS.md. AGENTS.md is the constitution — it should remain concise and stable.

### When a systemic issue is discovered, update preflight_checklist
If an error reveals a missing pre-flight check, add it to `docs/harness/preflight_checklist.md`.

---

## Memory Discipline Rules

### Keep memory concise and auditable
Error memory entries should be actionable, not verbose. Focus on: what failed, why, how it was fixed, what to do next time.

### Do not store full chat transcripts
Error memory does not include full conversation content. Only store: error type, symptom, failed command, repair action, prevention rule.

### Do not store private or emotional conversation content
Never store personal information, emotional content, or sensitive business discussions in any harness documentation.

### Do not store raw provider responses
If a provider (LLM, embedding) returns sensitive data, do not store the full response in error logs or reports.

---

## Python Environment Rules

### Always use `uv run python` instead of bare `python3`
On Windows/WSL, bare `python3` may resolve to Windows Python which defaults to GBK encoding. `uv run python` ensures consistent behavior.

### Always specify encoding='utf-8' for file I/O
JSON files, text files, and configuration files should always be opened with `encoding='utf-8'` to avoid GBK/UTF-8 conflicts.

---

## Validation Rules

### Run preflight_checklist.md before each batch
Before starting a harness batch, verify:
- Repository status is clean
- Branch is correct
- No forbidden file modifications
- No pending archived report changes

### Run post_failure_reflection.md after any failed validation
When a batch fails validation, complete the post-failure reflection to:
- Identify root cause
- Determine recurrence
- Update error memory
- Decide promotion (playbook, rules, AGENTS.md)

---

## Commit Discipline Rules

### Do not bloat AGENTS.md with raw logs
AGENTS.md should contain stable principles, not raw error logs or verbose incident reports. Use error_memory.jsonl for detailed tracking.

### Verify OpenSpec tasks complete before archive
Before running `openspec archive`, verify all tasks in tasks.md are marked done. Archive fails if incomplete tasks are detected.

### Re-export data after label expansion
When golden labels or evaluation data is expanded, re-run any export/generation scripts to ensure reports reflect current state.

---

## CSV/Defensive Coding Rules

### Use defensive CSV cell access
When reading CSV with csv.DictReader, empty cells return None, not "". Always use:
```python
(r.get("field") or "").strip()
```
Never:
```python
r.get("field", "").strip()  # fails if cell is None
```

---

## When in Doubt

- Prefer failing clearly over succeeding silently
- Check repair_playbook.md before diagnosing new errors
- Update error_memory.jsonl after any non-trivial failure
- Ask: "Would this rule prevent a future incident?" before adding to AGENTS.md