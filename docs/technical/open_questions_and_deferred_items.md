# Open Questions and Deferred Items

This document lists all known gaps, deferred features, and open questions for the TicketPilot MVP. Items are organized by area. None of these items are implemented.

## Realistic Data Pack

**Status:** Deferred

The current knowledge base contains 36 synthetic documents (12 FAQ, 12 Policy, 12 Case). This is sufficient for demo and integration testing but is not representative of real enterprise data.

**Open questions:**
- What is the source of real FAQ/policy/case data?
- How will sensitive/customer data be anonymized?
- What is the expected scale (documents, chunks, users)?
- Who will curate and maintain the knowledge base?

**Dependencies:** Requires subject matter experts and access to real customer service knowledge artifacts.

## Evaluation Pipeline

**Status:** Deferred

No automated evaluation scripts exist. The 5-layer evaluation taxonomy is documented in `docs/evaluation_plan.md` (classification, retrieval, evidence, risk gate, human review) but no code implements it.

**What's missing:**
- Golden-answer test sets for retrieval precision/recall/mRR
- Draft quality evaluation (citation accuracy, hallucination rate, appropriateness)
- Regression benchmark suite across pipeline versions
- Automated risk assessment accuracy measurement
- End-to-end pipeline evaluation harness

**Open questions:**
- Should evaluation use Ragas, Langfuse, or a custom framework?
- What are the target metrics and thresholds?
- How are golden test sets created and maintained?
- How are evaluation results tracked over time?

## Real Embedding Provider

**Status:** Deferred

Current: `FakeEmbeddingProvider` (384-dim, SHA-256 seeded, PIPELINE VERIFICATION ONLY — no semantic meaning).

**Planned tiers:**
- Small: 384-d real embedding model (e.g., text-embedding-3-small or equivalent open model)
- Quality: 768-d real embedding model (e.g., text-embedding-3-large or equivalent open model)

**Open questions:**
- Which embedding provider? OpenAI, local model, or open-weight model?
- How are embeddings updated when documents change?
- What is the cost/latency budget?
- How is embedding quality validated?

**Dependencies:** Requires API keys or local model deployment, integration testing, and evaluation pipeline.

## Real LLM Provider

**Status:** Deferred

Current: `FakeDraftProvider` (deterministic, template-based, no LLM calls).

The `AbstractDraftProvider` interface is ready for integration, but no real LLM provider has been implemented.

**Open questions:**
- Which LLM provider? OpenAI, Anthropic, or open model?
- What is the prompt strategy for draft generation?
- How is cost controlled (token usage, caching, batching)?
- How are latency requirements balanced against quality?
- How does the real provider handle Chinese language specifically?
- What fallback behavior exists when the LLM API is unavailable?

## Trace Persistence

**Status:** Deferred

Both `RetrievalTrace` and `DraftGenerationTrace` are in-memory only. The `retrieval_traces` DB table migration was explicitly deferred.

**What's missing:**
- Database-backed retrieval trace storage
- Database-backed draft generation trace storage
- Trace query and analysis interface
- Trace retention policy

**Open questions:**
- What is the trace retention period?
- Who queries traces and for what purpose (debugging, auditing, analytics)?
- Should traces be stored in PostgreSQL or a time-series database?

## LangGraph Workflow

**Status:** Deferred

LangGraph is declared in `pyproject.toml` dependencies but no workflow orchestration code exists. The current pipeline is a simple sequential function composition.

**Potential LangGraph benefits:**
- Explicit state graph of pipeline stages
- Parallel execution where possible
- Built-in tracing and debugging
- Conditional branching and loops
- Human-in-the-loop checkpointing

**Open questions:**
- Does the MVP pipeline complexity justify LangGraph?
- Would the added abstraction make the pipeline harder to understand and debug?
- What is the migration path from function composition to LangGraph?

## Production Deployment

**Status:** Deferred

No production deployment configuration exists. Current setup:
- `docker-compose.yml` for local PostgreSQL + pgvector only
- No Docker production configuration (multi-stage builds, reverse proxy, etc.)
- No CI/CD pipeline
- No cloud deployment scripts
- No monitoring or alerting

**What's missing:**
- Production Dockerfile and docker-compose.yml
- Reverse proxy (nginx/traefik) configuration
- CI/CD pipeline (GitHub Actions, etc.)
- Cloud deployment (AWS, GCP, Azure, or VPS)
- Monitoring and alerting (health checks, error tracking, performance metrics)
- Backup and disaster recovery procedures

## Auth / Multi-User Review

**Status:** Deferred

The review console has no authentication or multi-user support:
- Reviewer identity is a free-text `reviewer_label` field
- No login, no roles, no permissions
- ReviewStore is a local JSONL file — no shared queue
- No assignment, prioritization, or workload management

**What's missing:**
- User authentication (login/password, SSO, or OAuth)
- Role-based access control (viewer, reviewer, admin)
- Shared review queue with ticket assignment
- Review workload dashboards
- Escalation workflows (auto-assign to senior reviewers)
- Audit logging of who accessed which ticket when

## Real Customer Service Integration

**Status:** Deferred

TicketPilot has no integration with customer service platforms (Zendesk, Freshdesk, Intercom, custom CRM, etc.). The system currently:
- Accepts tickets via manual JSON paste in the review console
- Records review decisions to local JSONL
- Never dispatches replies anywhere

**What's missing:**
- API endpoints for programmatic ticket submission (FastAPI planned but not implemented)
- Integration adapters for customer service platforms
- Reply dispatch mechanism (requires auto-send design and safety review)
- Webhook or polling-based ticket ingestion
- Platform-specific formatting and compliance requirements

## Other Deferred Items

- **`map_intent_to_doc_types`**: Intent-to-doc-type filtering for retrieval was designed but not implemented. See design.md.
- **`RetrievalTrace` naming collision**: Duplicate `RetrievalTrace` name exists in the retrieval module. Deferred cleanup.
- **`enable_retrieval` flag**: Design.md feature to disable retrieval was simplified out.
- **Evidence scoring threshold tuning**: RRF scores have no absolute meaning; tuning deferred until evaluation data exists.
- **SourceRouter**: Intent-to-source routing was documented in earlier design drafts but not implemented.
- **Persistent migration 004**: Separate source refs migration not created (folded into migration 003).
- **`test_embedding_dimension_validation` cleanup**: Inline DB import in vector retrieval test deferred.
- **BusinessDomain/IntentClass enum duplication**: Deferred from audit remediation.
- **Bulk operations**: No batch ticket processing or bulk review actions.
- **Multi-turn conversation**: No support for conversational or threaded ticket responses.
- **Configurable/locale-aware fallback messages**: Fallback text is hardcoded Chinese.
