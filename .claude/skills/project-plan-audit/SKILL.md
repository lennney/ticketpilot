---
name: project-plan-audit
description: Use when auditing TicketPilot project plans, modules, tests, OpenSpec changes, and phase status before continuing development.
---

# Project Plan Audit Skill

The audit must include:

## 1. Scope Alignment

Check whether the project still follows the TicketPilot MVP scope:
- ticket normalization
- intent classification
- risk gate
- FAQ / Policy / Case layered retrieval
- hybrid retrieval (keyword + vector + RRF)
- evidence-grounded draft reply
- human review
- trace
- evaluation

Mark any generic chatbot, unnecessary multi-agent product feature, or over-engineered component as scope drift.

## 2. Requirement-to-Evidence Matrix

For each major requirement, map:
- requirement
- OpenSpec source
- implementation file
- test file / test command
- status: PASS / GAP / FAIL
- notes

## 3. Module Boundary Review

For each module, check:
- purpose
- input
- output
- dependency
- test coverage
- whether it is too broad or too coupled

## 4. Test Coverage Review

Review:
- unit tests
- integration tests
- skipped tests
- smoke tests
- evaluation cases
- missing negative cases

Rule: A skipped integration test is NOT a pass. It is a GAP.

Rule: Fake embedding proves pipeline wiring only, not semantic retrieval quality.

## 5. Phase Status Accuracy

Check:
- docs/phase_status.md
- docs/changelog.md
- README.md
- docs/technical_decisions.md

Ensure status claims are not overstated.

## 6. Risk Register

Classify issues:
- BLOCKING
- HIGH
- MEDIUM
- LOW
- DEFERRED

## 7. Minimal Fix Plan

Produce a prioritized fix plan:
- Fix now
- Fix before next feature
- Defer safely
- Remove / simplify

Do not recommend broad rewrites unless absolutely necessary.
Do not propose new features during audit.

## 8. Final Decision

Output one of:
- CONTINUE — all clear to proceed with next phase
- CONTINUE_WITH_GAPS — proceed but track gaps explicitly
- HOLD_NEW_FEATURES — blockers must be resolved first
