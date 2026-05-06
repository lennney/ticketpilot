# Post-Failure Reflection Template — TicketPilot AI Development Harness

*Complete this template after any failed validation. Forces structured analysis.*

---

## 1. What Failed?

Describe the failure in one sentence.
- What command or operation failed?
- What was the expected outcome?

---

## 2. What Exact Command Failed?

Copy the exact command that failed.
```
[PASTE COMMAND HERE]
```

---

## 3. What Did the Error Message Say?

Copy the exact error message.
```
[PASTE ERROR MESSAGE HERE]
```

---

## 4. What Was the Root Cause?

Identify why this failure occurred.
- Was it a new issue or recurring?
- What code or configuration change caused it?
- What assumptions were wrong?

---

## 5. Was This Repeated?

Check error_memory.jsonl for same error type.
- Search for similar entries
- Note recurrence_count
- Determine if this is first occurrence or repeat

---

## 6. What Repair Was Applied?

Describe exactly what was done to fix the issue.
- Which file was modified?
- What was the change?
- Why does this fix the problem?

---

## 7. How Was the Repair Validated?

Describe how you verified the fix.
- Which command confirmed success?
- What test was run?
- What is the new state?

---

## 8. What Prevention Rule Should Be Added?

Identify what rule or check would prevent this in future batches.
- Update repair_playbook.md?
- Add to agent_learning_rules.md?
- Add preflight check?
- Add regression test?

---

## 9. Should This Become a Regression Test?

Determine if a test would catch this error in the future.
- Can this error be tested automatically?
- What would the test assert?
- Is test maintenance worth the benefit?

If yes: Add test proposal to error_memory entry.

---

## 10. Where Should This Lesson Be Promoted?

Choose the appropriate destination:
- `error_memory.jsonl` — record for future reference
- `repair_playbook.md` — categorize for common issues
- `preflight_checklist.md` — add pre-batch check
- `agent_learning_rules.md` — add stable rule (high bar)
- `AGENTS.md` — promote only after confirmation or clear high-risk evidence
- Stay only in error_log.md — one-off issue, not systemic

---

## 11. What Should the Next Batch Check Before Starting?

List specific things the next batch should verify:
1. [CHECK 1]
2. [CHECK 2]
3. [CHECK 3]

---

## 12. Open Questions / Known Unknowns

If there are aspects you don't fully understand:
- [QUESTION 1]
- [QUESTION 2]

Document these to avoid repeating the same investigation.

---

## Summary for Batch Report

After completing this reflection, summarize:
- Error type: [TYPE]
- Severity: low / medium / high
- Recurrence: first / repeat
- Fix verified: yes / no
- Prevention: [SHORT RULE]
- Promotion: [DESTINATION] or [NONE]