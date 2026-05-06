# TicketPilot: AI-Powered Customer Support Ticket Triage Copilot

## Project Overview

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply copilot. Built from scratch using OpenSpec spec-driven development across 5 major iteration phases, it demonstrates a complete AI-assisted workflow for processing unstructured Chinese-language support tickets.

**Status:** MVP (functional demo, not production-ready)

**Core technical objectives:**
- Structured processing of Chinese support tickets (normalization, intent classification, risk assessment)
- Hybrid retrieval (keyword + vector) over a knowledge base of FAQ, policy, and case documents
- Optional evidence-grounded draft reply generation (template / LLM-constrained)
- Human-in-the-loop review console for safe decision recording
- Evaluation-driven iteration to identify the next bottleneck rather than blind feature stacking

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
| 5. Draft Generation | Evidence-grounded draft via template / LLM provider | Optional |
| 6. Human Review | Streamlit console for approve/edit/escalate/reject | Optional |

### Core Modules

| Module | Description |
|--------|-------------|
| Intake | Text cleaning, regex entity extraction |
| Classification | Keyword-dictionary intent classifier (8 classes) |
| Risk | 8 risk flags, severity calculation, human-review trigger |
| Retrieval | Hybrid engine: PostgreSQL FTS + pgvector HNSW + RRF; dual provider (Fake 384-d / Real 1024-d) |
| Drafting | Abstract provider pattern + FakeDraftProvider/FakeLLMProvider + PromptBuilder + ClaimGuard |
| Review | ReviewDecision audit model + JSONL persistence |
| Pipeline | 4-stage orchestration with per-stage try/except degradation |

### Tech Stack

Python 3.11+, uv, PostgreSQL 16 + pgvector, Pydantic, Streamlit, Docker Compose, DashScope text-embedding-v4 (opt-in), OpenSpec

## Project Iteration History

### Phase 7: MVP Data Foundation & Evaluation (Complete)

- Eval dataset: 10 → **101 synthetic tickets** (all 8 intents, 8 risk flags)
- Knowledge base: 36 → **95 records** (FAQ=40, Policy=30, Case=25)
- Offline evaluation pipeline (CSV + Pipeline modes, 7 metrics)
- 3 demo scenarios + limitation documentation

### Phase 8: Real Retrieval Upgrade (Complete)

- DashScope text-embedding-v4 (1024-d) integration; Fake as default, real opt-in
- Fake 384-d vs Real 1024-d comparison on fixed dataset
  - Top-1 hit rate: 31.7% → 42.6% (+10.9%)
  - MRR: 0.4114 → 0.4913 (+0.0799)
- **Key finding**: All 41 wrong cases identical between fake and real, all missing_doc_type
- **Product judgment**: Bottleneck is knowledge coverage, not embedding quality

### Phase 9: Evaluation-Driven Knowledge Optimization (Complete)

- 41 wrong cases → 8 failure categories → 24 knowledge gaps
- Targeted addition of **11 P0 records** (total 95→106)
- **Key finding**: `load_dotenv()` never called; all evaluations silently fell back to fake provider
- Built **Provider Identity Gate** to prevent metrics from unknown sources
- Post-fix: P0 hit rate 75.0%, Top-1 +2.0%

### Phase 10: Ranking Diagnosis & Granular Evaluation (Complete)

- Doc-level golden labels: 14 → **86 evaluation cases**
- Evaluation unit refined from doc_type to doc_id
- **Doc-ID Recall@10 = 91.9%**, 32.5pp above doc-type metric
- **Core finding**: 78% of "wrong" cases were actually evaluation granularity issues, not retrieval failures

### Phase 11: Evidence-Grounded LLM Draft (Complete)

- LLM provider abstraction + FakeLLMProvider deterministic implementation (no API dependency)
- Evidence-grounded prompt builder (evidence constraints + safety rules + output format spec)
- DraftCitationValidationResult and validate_draft_citations()
- ClaimGuard (5 checks: citation coverage, uncited claims, forbidden promises, evidence sufficiency, risk-aware)
- DraftGenerationResult + generate_draft() wiring all components
- Human review console update (15 audit fields + guard status display)
- Offline draft evaluation metrics (8 deterministic metrics, citation precision=100%, claim guard pass rate=0%)
- 8-layer safety architecture: prompt constraint → citation validation → ClaimGuard → risk-aware → human review propagation → no-auto-send → fake default → provider identity

### Iteration Logic

```
Phase 7: Build data foundation + evaluation
  → Phase 8: Real embeddings → bottleneck is knowledge coverage
    → Phase 9: Knowledge optimization → discovered config silent fallback
      → Phase 10: Granular evaluation → 78% "errors" were granularity issues
        → Phase 11: Complete evidence-grounded draft with 8-layer safety (complete)
```

## AI Workflow Design

### Hybrid Retrieval Strategy

Combines keyword search (PostgreSQL FTS with GIN index) and vector search (pgvector HNSW, m=16, ef_construction=200), fused via RRF (k=60). Dual provider architecture: FakeEmbeddingProvider (384-d, default) for pipeline verification, DashScope text-embedding-v4 (1024-d, opt-in) for real semantic retrieval.

### Draft Generation

Optional workflow with dual providers. Evidence-grounded prompt builder constrains output to retrieved evidence. CitationValidator + ClaimGuard for integrity checking.

## Human-in-the-Loop

Review triggers (high risk, unsupported claims, insufficient evidence, guard failure) set must_human_review=True. Four actions: APPROVE, EDIT, ESCALATE, REJECT. Append-only JSONL audit trail. No auto-send by design.

## Quality Gate

Ruff (0 errors), unit tests (~856 pass, coverage >70%), integration tests (119 pass, 0 skipped), OpenSpec validation, secret scan.

## Limitations

- Local demo / portfolio prototype
- Synthetic data only (101 tickets, 106 knowledge records)
- Fake embeddings by default (real opt-in via env)
- No real LLM by default (FakeLLMProvider for pipeline verification)
- No auto-send (architectural constraint)
- Offline evaluation only
- Streamlit MVP UI, no auth/multi-user

## Next Steps

| Direction | Priority |
|-----------|----------|
| Phase 11 completion (LLM provider + ClaimGuard + draft eval) | ✅ Complete |
| Retrieval ranking optimization (query expansion / RRF tuning) | P0 |
| Realistic data pack | P1 |
| LangGraph workflow orchestration | P2 |
