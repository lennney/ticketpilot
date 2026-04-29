# TicketPilot AI-Assisted Development Workflow

TicketPilot uses a spec-driven, multi-agent-assisted development workflow.

The goal is not to let AI freely generate the whole project. The goal is to make AI-assisted development traceable, reviewable, testable, and recoverable.

## Layer 1: Planning Brain

Used for:
- product scope
- architecture decisions
- OpenSpec change design
- phase planning
- acceptance criteria
- risk analysis

Output:
- proposal
- design
- tasks
- acceptance criteria
- implementation prompts

Planning should not directly write production code.

## Layer 2: Implementation Body

Used for:
- narrow code changes
- tests
- scripts
- migrations
- documentation updates

Rules:
- implement only one batch at a time
- respect allowed/forbidden file scope
- do not weaken tests
- do not change product requirements
- update changelog after meaningful changes

## Layer 3: Supervision

Used after every batch.

The supervisor checks:
- whether implementation matches OpenSpec
- whether all acceptance criteria are covered
- whether tests prove the claims
- whether any skipped tests are acceptable
- whether documentation and changelog are updated
- whether the phase should be ACCEPTED, ACCEPTED_WITH_GAPS, or REJECTED

The supervisor is read-only by default.

## Layer 4: Quality Gate

Every batch should run:
- ruff
- pytest
- OpenSpec validation
- Docker config validation if relevant
- secret scan
- integration tests if relevant
- evaluation scripts if relevant

A skipped integration test is not equivalent to a passed test.

## Decision Rule

A batch can only be fully accepted when:
1. scope matches the spec
2. quality gate passes
3. tests cover the critical behavior
4. skipped tests are either zero or explicitly justified
5. changelog is updated
6. remaining risks are documented
