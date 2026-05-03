---
name: add-public-github-package
author: len
status: proposed
created: 2026-05-03
---

# Design: Public GitHub Package

## Architecture

This is a documentation-only change. No architecture modifications are made
to the TicketPilot runtime system.

## README Structure

```
README.md
├── 1. What is TicketPilot?
│   ├── Chinese customer support ticket triage Copilot
│   ├── Architecture-first, offline, deterministic demo
│   └── No auto-send, no LLM, no real embeddings
├── 2. Why not a normal RAG demo?
│   ├── No chat interface
│   ├── No real vector search quality
│   ├── No real LLM-generated replies
│   └── Deterministic, seed-data based evaluation
├── 3. Core Workflow
│   └── RawTicket → intake → classify → assess risk → retrieve → draft → review
├── 4. Feature Overview
│   ├── Intent classification (8 types)
│   ├── Risk assessment (8 flags)
│   ├── Layered retrieval (keyword + vector + RRF)
│   ├── Evidence-grounded draft generation
│   ├── Human review console
│   └── Evaluation pipeline
├── 5. Architecture Summary
│   └── Module boundaries per OpenSpec spec
├── 6. Quick Start
│   ├── Prerequisites
│   ├── Clone & setup
│   ├── Database setup
│   ├── Run pipeline
│   ├── Run review console
│   └── Run evaluation
├── 7. Documentation Map
│   ├── docs/technical/
│   ├── docs/portfolio/
│   ├── docs/demo/
│   └── prompts/
├── 8. Current Limitations
├── 9. Roadmap
└── 10. Safety Boundary
    └── No auto-send: architectural constraint
```

## Demo Guide

`docs/demo/README.md` with step-by-step instructions:
1. Prerequisites and environment setup
2. Database seeding
3. Run the full pipeline with sample tickets
4. Run the review console
5. Run the evaluation pipeline
6. Expected output examples
7. Troubleshooting

## Evaluation Verification

- `scripts/run_eval.py --prediction-mode csv` — load from CSV
- `scripts/run_eval.py --prediction-mode pipeline` — run live pipeline

Both must produce reports that clearly state:
- Small deterministic seed dataset
- Fake embeddings, no real semantic retrieval
- Not real-world performance

## Repository Hygiene

- `.gitignore`: confirm `.claude/worktrees/` excluded, add any missing
  local-only patterns
- `.env.example`: verify all required env vars documented
- No API keys, secrets, or credentials in committed files
- No `.coverage*` artifacts, no `__pycache__/`, no `.venv/`

## Release Checklist

`docs/github_release_checklist.md`:
- [ ] README complete and accurate
- [ ] Quick Start verified on clean clone
- [ ] Demo guide verified
- [ ] `.gitignore` excludes local artifacts
- [ ] No secrets committed
- [ ] Limitations documented
- [ ] No overstated claims
- [ ] No src/ or tests/ modifications
- [ ] Quality gate passes
- [ ] OpenSpec validate --all passes
