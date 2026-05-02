# TicketPilot: Limitations and Next Steps

## Purpose

This document clearly distinguishes what the system can do today (local demo readiness) versus what is missing for MVP readiness and production readiness. This is not a list of deficiencies -- it is a roadmap showing what has been deliberately deferred and what the path forward looks like.

## Current Local Demo Readiness

The system is ready for local demonstration with the following capabilities:

| Capability | Status | Details |
|-----------|--------|---------|
| End-to-end pipeline | Working | Processes RawTicket through intake, classification, risk assessment, retrieval, optional drafting, and human review |
| Hybrid retrieval | Working (mechanics) | Keyword + vector search with RRF fusion; embeddings are fake (pipeline verification only) |
| Draft generation | Working | Template-based FakeDraftProvider with citations and unsupported claim detection |
| Human review | Working | Streamlit console with Approve/Edit/Escalate/Reject actions |
| Audit trail | Working | Append-only JSONL persistence via ReviewStore |
| Quality gate | Working | 5-stage automated gate: Ruff, unit tests (325), integration tests (74), OpenSpec validation, secret scan |
| Documentation | Complete | Development trace (7 docs), technical docs (11 docs), portfolio docs (5 docs) |

**Demo environment requirements:**
- Docker Compose for PostgreSQL + pgvector
- Python 3.12+ with uv
- Streamlit for the review console UI
- All components run locally with synthetic seed data (36 documents)

## MVP Readiness Gaps

The core workflow (ticket-to-draft-to-review) is architecturally complete. The following gaps prevent declaring full MVP readiness:

### Realistic Data Pack
- Impact: Current 36-document synthetic seed (12 FAQ, 12 Policy, 12 Case) is not representative of real enterprise content. No real data has been loaded.
- Effort to close: Medium -- requires data collection, migration, and validation.

### Real Embedding Provider
- Impact: FakeEmbeddingProvider has no semantic meaning. Real retrieval quality cannot be measured or demonstrated.
- Effort to close: Low -- EmbeddingProvider interface is ready for integration.

### Real LLM Provider
- Impact: FakeDraftProvider produces template-based replies, not natural language. No connection to OpenAI, Claude, or any LLM.
- Effort to close: Low -- AbstractDraftProvider interface is ready.

### Evaluation Pipeline
- Impact: No golden-answer test sets, no precision/recall/mRR metrics, no automated quality measurement.
- Effort to close: High -- requires test set curation and metric implementation.

### Trace Persistence
- Impact: RetrievalTrace and DraftGenerationTrace are in-memory only. Historical analysis is not possible.
- Effort to close: Low -- schema is designed, DB migration needs implementation.

### Authentication and Multi-User Review
- Impact: Reviewer identity is a free-text label. No login, no roles, no permissions.
- Effort to close: Medium -- requires auth implementation and review queue.

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
- Real embedding provider (small 384-d and quality 768-d tiers)
- Intent-to-source routing (SourceRouter from design)
- BM25 or alternative keyword retrieval
- Embedding fine-tuning on support ticket data

### Pipeline and Orchestration
- LangGraph workflow orchestration
- Pipeline stage ordering as runtime configuration
- Retrieval trace persistence (DB-backed)
- Draft generation trace persistence (DB-backed)
- Non-optional draft generation integrated into pipeline

### Evaluation
- Golden-answer test sets for retrieval and generation
- Precision/recall/mRR/nDCG metrics
- Automated hallucination and citation accuracy evaluation
- Regression benchmark suite across pipeline versions
- User acceptance testing process

### UI and Review
- Production web frontend (React/Next.js replacing Streamlit)
- Authentication and multi-user workflow with roles
- Shared review queue across reviewers
- Review dashboard with analytics and filtering
- Browser automation tests (Selenium/Playwright)

### Deployment
- Production Docker configuration (multi-service, health checks)
- CI/CD pipeline (GitHub Actions or similar)
- Cloud deployment (AWS/GCP/Azure)
- Database migration automation (Alembic)
- Monitoring and alerting
- Container orchestration (Kubernetes)

### Integration
- Real customer service platform API integration
- Ticket ingestion from external systems
- Reply dispatch after human approval
- Webhook or event-driven pipeline triggers

## Decision Log: Why Items Are Deferred

### Why Fake Embeddings (Not Real)
Fake embeddings prove pipeline mechanics -- embedding generation, HNSW indexing, cosine similarity scoring, and RRF fusion -- without any external API, API key, or model download. This kept the project self-contained for MVP development. The EmbeddingProvider interface is ready for real providers when needed.

### Why No Real LLM
A real LLM requires API keys, internet access, and ongoing costs. For MVP pipeline verification, a deterministic FakeDraftProvider provides better testability (same input always produces same output). The AbstractDraftProvider interface supports future LLM integration without pipeline changes.

### Why No Evaluation Pipeline
Building a meaningful evaluation pipeline requires: (a) real or realistic data, (b) real embeddings for semantic comparison, and (c) a real LLM for draft quality assessment. Since (a) and (b) are deferred, an evaluation pipeline would currently measure only fake provider behavior -- which the 325 unit tests already cover comprehensively.

### Why No Production Deployment
Production deployment was never in scope for this project phase. The focus was on proving the architecture, establishing test discipline, and creating comprehensive documentation. The Docker Compose setup provides reproducible local development without cloud infrastructure.

## Current Status Summary

| Maturity Dimension | Status | Key Evidence |
|-------------------|--------|-------------|
| Demo readiness | ACHIEVED | End-to-end pipeline, Streamlit UI, seed data, quality gate, documentation |
| MVP readiness | PARTIAL | Core workflow complete; data, provider, and evaluation gaps remain |
| Production readiness | NOT ACHIEVED | Infrastructure, security, integration, and scalability gaps documented |
