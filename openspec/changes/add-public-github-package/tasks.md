---
name: add-public-github-package
author: len
status: proposed
created: 2026-05-03
---

# Tasks: Public GitHub Package

## Phase 1: Repository Hygiene and Foundation

- [ ] 1.1 Audit `.gitignore` for local artifacts (`.coverage*`, `.claude/worktrees/`, `.pytest_cache/`)
- [ ] 1.2 Audit `.env.example` and ensure all required env vars documented
- [ ] 1.3 Verify no API keys, secrets, or credentials in committed files
- [ ] 1.4 Verify no overstated claims in existing docs
- [ ] 1.5 Create `openspec/changes/add-public-github-package/` structure

## Phase 2: README Rewrite

- [ ] 2.1 Write "What is TicketPilot?" and "Why not a normal RAG demo" sections
- [ ] 2.2 Write core workflow and feature overview
- [ ] 2.3 Write architecture summary
- [ ] 2.4 Write Quick Start instructions
- [ ] 2.5 Write documentation map
- [ ] 2.6 Write limitations, roadmap, and safety boundary sections
- [ ] 2.7 Review README for overclaiming and technical accuracy

## Phase 3: Demo Guide

- [ ] 3.1 Create `docs/demo/README.md` with step-by-step demo instructions
- [ ] 3.2 Add sample ticket inputs and expected outputs
- [ ] 3.3 Add troubleshooting section
- [ ] 3.4 Add screenshot/GIF placeholder instructions

## Phase 4: Release Checklist

- [ ] 4.1 Create `docs/github_release_checklist.md`
- [ ] 4.2 Verify each checklist item on current state

## Phase 5: Final Validation

- [ ] 5.1 Run full quality gate (Ruff, unit tests, integration tests, coverage, OpenSpec)
- [ ] 5.2 Verify Quick Start from clean clone
- [ ] 5.3 Verify demo guide accuracy
- [ ] 5.4 Verify no secrets or local artifacts committed
- [ ] 5.5 Verify no overstated claims

## Phase 6: Archive

- [ ] 6.1 Commit all changes
- [ ] 6.2 Archive OpenSpec change
- [ ] 6.3 Post-archive validation
