# TicketPilot Development Trace

## Purpose

This directory documents the full development history of TicketPilot, a Chinese customer support ticket triage and evidence-grounded reply Copilot. Each stage document captures the design context, implementation scope, test results, risks, and deferred items for one OpenSpec change.

The intended audience is developers, architects, and reviewers who need to understand what was built, why decisions were made, and what remains to be done.

## Project Status

### Readiness Levels

| Dimension | Status | Evidence |
|-----------|--------|----------|
| **Demo readiness** | Achieved | End-to-end pipeline processes raw tickets through intake, classification, risk assessment, retrieval, optional draft generation, and human review console. All stages work with fake embeddings and seed data. |
| **MVP readiness** | Partial | Core workflow (ticket-to-draft-to-review) is complete. MVP gaps: fake embeddings prove pipeline mechanics, not real semantic retrieval; seed data is synthetic, not real enterprise data; no real LLM provider; no evaluation pipeline; no production deployment. |
| **Production readiness** | Not achieved | See [Deferred Items](#deferred-items-across-all-stages) below. |

### Stage Overview

| Stage | Name | Status | Change |
|-------|------|--------|--------|
| 0 | Project Origin | Complete | `91f388f` — project initialization |
| 1A | Ticket Intake + Risk Triage | ACCEPTED | `add-ticket-intake-risk-triage` |
| 1B | Knowledge Layer + Hybrid Retrieval | ACCEPTED | `add-layered-knowledge-retrieval-foundation` |
| — | Pipeline Integration (retrieval connected) | ACCEPTED | `connect-retrieval-to-intake-risk-pipeline` |
| — | Quality Gate Hardening | ACCEPTED | `close-project-audit-blockers` |
| 1C | Evidence-Grounded Draft Generation | ACCEPTED | `add-evidence-draft-generation` |
| 1D | Human Review Console | ACCEPTED | `add-human-review-console` |

### Key Constraints

- **Fake embeddings** — The `FakeEmbeddingProvider` generates deterministic pseudo-random vectors from SHA-256 hashes. This proves pipeline mechanics (vector generation, HNSW indexing, cosine similarity scoring) but produces **no semantic retrieval quality**. Real retrieval quality requires a real embedding provider (see deferred items).
- **Seed data** — The knowledge base contains 12 FAQ, 12 Policy, and 12 Case synthetic documents. This is sufficient for demo and integration testing but is **not real enterprise data**.
- **No auto-send** — The system never automatically dispatches replies. All outputs require human review before any hypothetical downstream use. The review console explicitly displays "审核控制台 — 不自动发送回复" and has no send functionality.
- **High-risk / unsupported / no-evidence outputs require human review** — The pipeline sets `must_human_review=True` for any ticket that triggers risk flags, has unsupported claims in the draft, or lacks sufficient evidence.

## Stage Documents

- [00 — Project Origin](00_project_origin.md): Project initialization, toolchain setup, development workflow
- [01 — Intake + Risk Triage](01_intake_risk_triage.md): Stage 1A — ticket normalization, intent classification, risk assessment
- [02 — Layered Retrieval Foundation](02_layered_retrieval_foundation.md): Stage 1B — knowledge schema, hybrid retrieval engine
- [03 — Connect Retrieval to Pipeline](03_connect_retrieval_to_pipeline.md): Wiring retrieval as Stage 4 of the intake-risk pipeline
- [04 — Quality Gate Hardening](04_quality_gate_hardening.md): Audit remediation, quality gate fixes, two-layer schema
- [05 — Evidence Draft Generation](05_evidence_draft_generation.md): Stage 1C — drafting schemas, fake provider, citation validator
- [06 — Human Review Console](06_human_review_console.md): Stage 1D — review schemas, JSONL store, Streamlit console

## Timeline

See [timeline.md](timeline.md) for the chronological evolution.

## Deferred Items (Across All Stages)

The following are explicitly deferred from MVP scope and apply to the entire project:

- **Evaluation pipeline** — No golden-answer test sets, no automated evaluation of retrieval or generation quality. The 5-layer evaluation taxonomy is documented in `docs/evaluation_plan.md` but no evaluation scripts exist.
- **Realistic data pack** — Current seed data is synthetic. No real enterprise FAQ, policy, or case documents have been loaded.
- **Real embedding provider** — Only `FakeEmbeddingProvider` (384-dim, SHA-256 seeded) is implemented. Real providers (OpenAI text-embedding-3-small/large) are planned but not integrated.
- **Real LLM provider** — `FakeDraftProvider` (deterministic, template-based) is the only draft generation provider. No OpenAI, Anthropic, or other LLM is connected.
- **Trace persistence** — `RetrievalTrace` and `DraftGenerationTrace` are in-memory only. No database-backed trace storage exists.
- **LangGraph workflow** — LangGraph is in `pyproject.toml` dependencies but no workflow orchestration code exists.
- **Production deployment** — No Docker production configuration, no CI/CD, no cloud deployment. Only `docker-compose.yml` for local PostgreSQL + pgvector.
- **Authentication / multi-user** — Reviewer identity is a free-text label. No login, no roles, no permissions.
- **Auto-send / reply dispatch** — The system records review decisions to local JSONL only. No integration with customer service platforms.
