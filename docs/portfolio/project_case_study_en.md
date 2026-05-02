# TicketPilot: AI-Powered Customer Support Ticket Triage Copilot

## Project Overview

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply copilot. Built from scratch using OpenSpec spec-driven development across 6 change cycles, it demonstrates a complete AI-assisted workflow for processing unstructured Chinese-language support tickets.

**Status:** MVP (functional demo, not production-ready)

**Core technical objectives:**
- Structured processing of Chinese support tickets (normalization, intent classification, risk assessment)
- Hybrid retrieval (keyword + vector) over a knowledge base of FAQ, policy, and case documents
- Optional evidence-grounded draft reply generation
- Human-in-the-loop review console for safe decision recording

## Business Problem

Customer support teams receive large volumes of unstructured Chinese-language tickets. Without automated assistance, agents must manually normalize text, classify intent, assess risk, search knowledge bases, and write replies. This process is slow, inconsistent, and error-prone.

## System Architecture

### Six-Layer Pipeline

| Layer | Function | Mandatory |
|-------|----------|-----------|
| 1. Intake | Text normalization, entity extraction | Yes |
| 2. Classification | Rule-based 8-class intent classification | Yes |
| 3. Risk Assessment | 8 risk flags with severity calculation | Yes |
| 4. Retrieval | Hybrid keyword + vector search with RRF fusion | Yes |
| 5. Draft Generation | Evidence-grounded reply using templates | Optional |
| 6. Human Review | Streamlit console for approve/edit/escalate/reject | Optional |

### Core Modules

| Module | Description |
|--------|-------------|
| Intake | Text cleaning, regex entity extraction |
| Classification | Keyword-dictionary intent classifier (8 classes) |
| Risk | 8 risk flags, severity calculation, human-review trigger |
| Retrieval | Hybrid engine: PostgreSQL FTS + pgvector HNSW + RRF |
| Drafting | Abstract provider + FakeDraftProvider + CitationValidator |
| Review | ReviewDecision audit model + JSONL persistence |
| Pipeline | 4-stage orchestration with per-stage try/except degradation |

### Tech Stack

Python 3.12+, uv, PostgreSQL 16 + pgvector, Pydantic, Streamlit, Docker Compose, OpenSpec

## AI Workflow Design

### Hybrid Retrieval Strategy

Combines keyword search (PostgreSQL FTS with simple config and GIN index) and vector search (pgvector HNSW with m=16, ef_construction=200, cosine distance), fused via RRF (k=60). The FakeEmbeddingProvider generates 384-dim pseudo-random vectors from SHA-256 hash seeds for pipeline verification only -- no semantic meaning.

### Draft Generation

Optional workflow with AbstractDraftProvider interface and deterministic FakeDraftProvider (no LLM, no network, no API keys). Regex-based CitationValidator for claim integrity. Safety fallbacks for no-evidence and high-risk scenarios.

## Human-in-the-Loop

Review triggers (high risk, unsupported claims, insufficient evidence) set must_human_review=True. Four actions: APPROVE, EDIT, ESCALATE, REJECT. Append-only JSONL audit trail. No auto-send by design.

## Quality Gate

Ruff (0 errors), unit tests (325 pass, coverage 80.25%), integration tests (74 pass, 0 skipped), OpenSpec validation (all pass), secret scan (clean).

## Limitations

- Fake embeddings: pipeline verification only, no semantic meaning
- Seed data: 36 synthetic documents, not real enterprise data
- No real LLM: template-based FakeDraftProvider only
- No evaluation pipeline
- Traces are in-memory only
- No authentication or multi-user support
- No production deployment

## Next Steps

Near-term: realistic data pack, real embedding provider, real LLM, evaluation pipeline.
Medium-term: LangGraph workflow, trace persistence, auth/multi-user.
Long-term: production deployment, customer system integration.
