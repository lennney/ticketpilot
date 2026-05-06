# TicketPilot: Limitations and Next Steps

## Purpose

This document clearly distinguishes what the system can do today (local demo readiness) versus what is missing for MVP readiness and production readiness. This is not a list of deficiencies — it is a roadmap showing what has been deliberately deferred and what the path forward looks like.

## Current Local Demo Readiness

The system is ready for local demonstration with the following capabilities:

| Capability | Status | Details |
|-----------|--------|---------|
| End-to-end pipeline | Working | Processes RawTicket through intake, classification, risk assessment, retrieval, optional drafting, and human review |
| Hybrid retrieval | Working (mechanics) | Keyword + vector search with RRF fusion; dual provider (Fake 384-d default, Real 1024-d opt-in) |
| Real embedding comparison | Working | DashScope text-embedding-v4 comparison with offline metrics (Top-1 31.7%→42.6%, MRR 0.4114→0.4913) |
| Evaluation-driven knowledge opt. | Working | Wrong-case taxonomy (8 categories), targeted knowledge addition, P0 hit audit |
| Granular retrieval evaluation | Working | Doc-ID level evaluation, Recall@10=91.9%, metric granularity analysis |
| Draft generation | Working | Template-based FakeDraftProvider + evidence-constrained FakeLLMProvider with citations |
| Claim validation | Working | CitationValidator + ClaimGuard (forbidden promise detection, risk-aware checks) |
| Provider Identity Gate | Working | Runtime verification of active embedding provider on every eval run |
| Human review | Working | Streamlit console with Approve/Edit/Escalate/Reject actions |
| Audit trail | Working | Append-only JSONL persistence via ReviewStore |
| Quality gate | Working | 5-stage automated gate: Ruff, unit tests (~856), integration tests (119), OpenSpec validation, secret scan |
| Documentation | Complete | Technical docs (15+), portfolio docs (8), phase snapshots (4), changelog |

**Demo environment requirements:**
- Docker Compose for PostgreSQL + pgvector
- Python 3.11+ with uv
- Streamlit for the review console UI
- All components run locally with synthetic seed data (106 documents)

## MVP Readiness Gaps

### Realistic Data Pack
- Impact: Current 106-document synthetic seed (FAQ=41, Policy=34, Case=31) is not representative of real enterprise content. No real data has been loaded.
- Effort to close: Medium — requires data collection, migration, and validation.

### Real LLM Provider
- Impact: FakeLLMProvider produces deterministic template-like output. No connection to OpenAI, Claude, or any LLM API.
- Effort to close: Low — LLMProvider interface is ready, OpenAI compatible provider implementation pending (Phase 11).

### Draft Evaluation Metrics
- Impact: Current evaluation covers classification, risk, and evidence recall but not draft quality (citation precision, hallucination rate, etc.).
- Effort to close: Medium — schemas designed, metric implementation pending (Phase 11).

### Expanded Evaluation Dataset
- Impact: 101 synthetic tickets are insufficient for statistical significance.
- Effort to close: Medium — requires data collection and annotation.

### Trace Persistence
- Impact: RetrievalTrace and generation traces are in-memory only.
- Effort to close: Low — schema is designed, DB migration needs implementation.

### Authentication and Multi-User Review
- Impact: Reviewer identity is a free-text label. No login, no roles, no permissions.
- Effort to close: Medium — requires auth implementation and review queue.

## Production Readiness Gaps

The following items are explicitly out of scope for the current project stage:

| Gap | Category | Notes |
|-----|----------|-------|
| Production deployment | Infrastructure | No Docker production config, no CI/CD, no cloud deployment |
| Real customer service integration | API | No connection to ticketing systems or reply-sending API |
| Auto-send after approval | Feature | System records decisions only; auto-send is architecturally deferred |
| Auth / multi-user review | Security | Reviewer identity is free-text; no shared queue |
| Database-backed ReviewStore | Persistence | JSONL is local-only; shared DB needed for multi-user |
| LangGraph workflow orchestration | Architecture | In pyproject.toml dependencies but no code exists |
| Observability (Langfuse, Ragas) | Monitoring | No trace dashboard or performance monitoring |
| Scalability | Performance | No load testing, connection pooling tuning, or caching |
| Security hardening | Security | No secret management beyond .env.example |

## Deferred Items (Comprehensive List)

### Data and Knowledge
- Realistic enterprise FAQ, policy, and case data pack
- Embedding fine-tuning on support ticket data
- BM25 or alternative keyword retrieval

### Pipeline and Orchestration
- LangGraph workflow orchestration
- Pipeline stage ordering as runtime configuration
- Retrieval trace persistence (DB-backed)
- Draft generation trace persistence (DB-backed)

### Evaluation
- LLM-based draft quality evaluation (citation accuracy, hallucination rate)
- Regression benchmark suite across pipeline versions
- User acceptance testing process

### UI and Review
- Production web frontend (React/Next.js replacing Streamlit)
- Authentication and multi-user workflow with roles
- Shared review queue across reviewers
- Review dashboard with analytics and filtering

### Deployment
- Production Docker configuration (multi-service, health checks)
- CI/CD pipeline (GitHub Actions or similar)
- Cloud deployment (AWS/GCP/Azure)
- Database migration automation (Alembic)
- Monitoring and alerting

### Integration
- Real customer service platform API integration
- Ticket ingestion from external systems
- Reply dispatch after human approval

## Decision Log: Why Items Are Deferred

### Why Fake Embeddings as Default
Fake embeddings prove pipeline mechanics — embedding generation, HNSW indexing, cosine similarity scoring, and RRF fusion — without any external API, API key, or model download. Real embeddings (DashScope text-embedding-v4) are available via opt-in through `.env.local`. Phase 8 confirmed that real embeddings improve ranking but the primary bottleneck was knowledge coverage, not embedding quality.

### Why No Real LLM (Default)
A real LLM requires API keys, internet access, and ongoing costs. For MVP pipeline verification, deterministic providers provide better testability (same input always produces same output). The LLMProvider interface is ready for future integration. Phase 11 is implementing the integration architecture.

### Why Synthetic Data
Real enterprise customer data cannot be used in a public demo without complex compliance and anonymization. Synthetic data covers the same business scenarios and proves the pipeline mechanics. The data construction follows a 4-stage process: public reference → AI-assisted extraction → manual rewriting → manual golden labeling.

### Why No Production Deployment
Production deployment was never in scope for this project phase. The focus was on proving the architecture, establishing evaluation-driven iteration, and creating comprehensive documentation.

## Current Status Summary

| Maturity Dimension | Status | Key Evidence |
|-------------------|--------|-------------|
| Demo readiness | ACHIEVED | End-to-end pipeline, Streamlit UI, seed data, quality gate, documentation |
| MVP readiness | PARTIAL | Core workflow complete; data, provider, and evaluation gaps remain |
| Production readiness | NOT ACHIEVED | Infrastructure, security, integration, and scalability gaps documented |

## Key Evaluation Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Intent accuracy | 53.5% | Pipeline mode, reflects rule-based components |
| Severity accuracy | 54.5% | Pipeline mode |
| Risk flag F1 | 29.8% | Pipeline mode |
| Evidence doc type recall | 43.2% | Pipeline mode |
| Fallback correctness | 90.1% | Pipeline mode |
| No-auto-send compliance | 100.0% | Architectural constraint |
| Doc-ID Recall@10 | **91.9%** | Phase 10 granular evaluation (86 cases) |
| Fake vs Real Top-1 | 31.7% → 42.6% | Phase 8 retrieval comparison |
| MRR improvement | 0.4114 → 0.4913 | Phase 8 retrieval comparison |
