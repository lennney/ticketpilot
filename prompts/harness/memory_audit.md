# Memory Audit Template — TicketPilot AI Development Harness

*Periodic audit to keep error memory fresh, actionable, and secure.*

---

## Audit Frequency

Run this audit:
- At end of each phase (before archive)
- When error_memory.jsonl exceeds 100 entries
- When repair_playbook.md becomes too large

---

## 1. Remove Obsolete Rules

Identify entries that are no longer applicable:
- [ ] Error types that can no longer occur (e.g., deprecated tooling)
- [ ] Fixed issues that are now handled by newer code
- [ ] Rules for removed functionality

For each obsolete entry:
- Mark status: "stale"
- Or remove from file

**Target**: Keep active rules under 50 entries.

---

## 2. Merge Duplicate Errors

Identify similar errors that should be combined:
- Same root cause, different symptoms
- Errors that share the same prevention rule
- Duplicate entries from multiple occurrences

For duplicates:
- Keep the most recent entry with highest recurrence_count
- Merge prevention rules
- Update recurrence_count to total

---

## 3. Mark Resolved Recurring Issues

If an error was fully resolved and no longer occurs:
- Change status from "active" to "resolved"
- Keep in memory for historical reference
- Ensure prevention rule is in repair_playbook.md

---

## 4. Verify Active Rules Remain Actionable

For each active entry:
- Is the prevention rule still valid?
- Is the repair action still correct?
- Is the promoted_to destination appropriate?

Update any stale information.

---

## 5. Ensure No Secrets or Private Data

Search error memory for forbidden content:
- [ ] No API keys (sk-, API key patterns)
- [ ] No full chat transcripts
- [ ] No private personal content
- [ ] No raw provider responses

```bash
grep -i "sk-" reports/harness/error_memory.jsonl
grep -i "token\|secret\|key" reports/harness/error_memory.jsonl
```

If found: Remove immediately and document in audit log.

---

## 6. Ensure AGENTS.md Is Not Bloated

Check AGENTS.md:
- [ ] No raw error logs pasted in
- [ ] No verbose incident reports
- [ ] Only stable, cross-phase principles
- [ ] No more than 200 lines of rules

If bloated:
- Move detailed content to repair_playbook.md or error_log.md
- Keep AGENTS.md as high-level constitution

---

## 7. Ensure Repair Playbook Remains Actionable

Check repair_playbook.md:
- [ ] All sections have symptoms, causes, steps
- [ ] No obsolete sections for removed features
- [ ] Commands are up to date
- [ ] Stop conditions are clear

If outdated:
- Remove obsolete sections
- Update commands to match current tooling
- Ensure stop conditions are accurate

---

## 8. Review Preflight Checklist

Check preflight_checklist.md:
- [ ] All checks are still relevant
- [ ] Commands work as documented
- [ ] No missing checks for new error types

If gaps found:
- Add new preflight checks
- Document commands to run

---

## 9. Summary of Changes

After audit, record:
- Entries removed: [N]
- Entries merged: [N]
- Entries marked resolved: [N]
- Entries updated: [N]
- Secrets removed: [N]

---

## Audit Sign-Off

Date: [DATE]
Auditor: [AI AGENT]
Next audit scheduled: [DATE or "on next archive"]