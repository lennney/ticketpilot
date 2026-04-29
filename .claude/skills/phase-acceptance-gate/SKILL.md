---
name: phase-acceptance-gate
description: Use after every implementation batch to produce a strict acceptance report with requirement-to-evidence mapping.
---

# Phase Acceptance Gate

Every batch acceptance report must include:

## 1. Scope Check

- Intended scope
- Actual files changed
- Out-of-scope changes
- Forbidden changes detected

## 2. Requirement-to-Evidence Matrix

Each row must include:
- Requirement
- Implementation file
- Test file or command
- Evidence
- Status: PASS / GAP / FAIL

## 3. Quality Gate Evidence

Include exact results for:
- ruff
- pytest
- OpenSpec validation
- Docker config if relevant
- secret scan
- integration tests if relevant
- evaluation scripts if relevant

## 4. Skipped Test Audit

Skipped tests must be listed with:
- test name
- reason
- whether skip is acceptable
- what is needed to remove the skip

## 5. Risk Assessment

Classify remaining risks as:
- blocking
- non-blocking
- deferred by design

## 6. Final Decision

End with exactly one:
- ACCEPTED
- ACCEPTED_WITH_GAPS
- REJECTED

Rules:
- Do not mark a batch ACCEPTED if core integration tests are skipped.
- Do not mark a requirement complete without test or command evidence.
- Do not allow implementation agents to silently change requirements.
