---
name: add-public-github-package
author: len
status: proposed
created: 2026-05-03
---

# Proposal: Prepare TicketPilot for Public GitHub Portfolio Presentation

## Summary

TicketPilot is a Chinese customer support ticket triage Copilot — an offline,
deterministic, architecture-first demo system. All core pipelines are complete
and archived (intake/risk triage, layered retrieval, evidence-grounded
drafting, human review console, evaluation pipeline). The system now needs a
public-facing GitHub package so that portfolio readers and reviewers can
understand, run, and evaluate the project without needing prior context.

This change is documentation and packaging only — no runtime behavior changes.

## Motivation

The current repository is developer-internal: README is sparse, no Quick
Start guide exists, demo instructions are scattered across skill docs, and
`.gitignore` excludes are incomplete. A public portfolio requires:

- A clear, structured README that tells the story (architecture-first, no
  auto-send, evaluation-backed)
- Quick Start that works from `git clone` to running the pipeline
- Demo guide with sample inputs and expected outputs
- Safety boundary documentation (no auto-send, seed data, fake embeddings)
- Repository hygiene (.gitignore, .env.example, license)

## Scope

- README.md rewrite
- docs/demo/ guide
- docs/github_release_checklist.md
- .env.example alignment
- .gitignore audit and finalization
- docs/changelog.md update
- OpenSpec change documentation

## Non-Goals

- No src/ modifications
- No tests/ modifications
- No runtime behavior changes
- No real embedding provider
- No real LLM provider
- No production readiness claims
- No enterprise data claims
- No auto-send feature

## Risks

1. Overclaiming capability in README — mitigated by mandatory limitations
   section and safety boundary documentation
2. Quick Start fails on clean clone — mitigated by CI-style verification
   before commit
3. Outdated architecture diagrams — mitigated by using text-based
   descriptions instead of binary diagrams that rot
