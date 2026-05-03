---
name: add-public-github-package
author: len
status: proposed
created: 2026-05-03
---

# Specification: Public GitHub Package

## Overview

| Field | Value |
|---|---|
| Change ID | add-public-github-package |
| Type | documentation |
| Status | proposed |
| Target | README.md, docs/demo/, .gitignore, .env.example |

## ADDED Requirements

### Requirement: Public-facing README

The README SHALL contain 10 sections.

#### Scenario: README structure verification
- Given a visitor reads the README
- When they scan the table of contents
- Then all 10 sections must be present and populated
- And the "Why not a normal RAG demo?" section MUST explicitly state:
  - No chat interface
  - No real vector search quality
  - No real LLM-generated replies
  - Deterministic, seed-data based evaluation only
- And the "Safety Boundary" section MUST state no auto-send

### Requirement: Demo Guide

The change SHALL create `docs/demo/README.md` with step-by-step instructions.

#### Scenario: Demo guide runs without errors
- Given a clean clone of the repository
- When following the demo guide step by step
- Then each command must succeed without errors
- And the expected output must match the described output

### Requirement: Release Checklist

The change SHALL create `docs/github_release_checklist.md`.

#### Scenario: Release checklist covers all requirements
- Given the release checklist
- When reviewing each item
- Then it MUST cover: README completeness, Quick Start, demo guide, gitignore hygiene, secrets scan, limitations, claims review, quality gate, and OpenSpec validation

### Requirement: Repository Hygiene

`.gitignore` MUST exclude `.claude/worktrees/` and all local-only artifacts.
No secrets or API keys SHALL exist in committed files.
No overstated claims SHALL exist in committed documentation.

#### Scenario: Hygiene scan passes
- Given the repository root
- When running `git status --short`
- Then no local-only artifacts appear as untracked (except allowed patterns)
- And when scanning for API key patterns, no matches found
- And when reviewing docs for "production-ready" or "enterprise-grade", no such claims exist for TicketPilot

### Requirement: Quality Gate

All validation checks MUST pass before archive.

#### Scenario: Quality gate passes
- Given the repository at the final state
- When running `./scripts/run_quality_gate.sh`
- Then it exits with code 0
- And all unit tests pass
- And all integration tests pass with 0 skipped
- And coverage meets the threshold

### Requirement: No Source Code Changes

No runtime code changes SHALL be made.

#### Scenario: No source code modified
- Given the final commit set
- When checking `git diff HEAD~1 -- src/ tests/`
- Then no files changed in `src/` or `tests/`
