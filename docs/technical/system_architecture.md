# System Architecture

## Product Boundary

TicketPilot is a **Chinese customer support ticket triage and evidence-grounded reply Copilot**. It processes unstructured Chinese-language customer support tickets through a multi-stage pipeline (intake, classification, risk assessment, retrieval), optionally generates evidence-grounded draft replies, and provides a human review console for recording review decisions.

### What TicketPilot Does

- Accepts raw Chinese customer support tickets as input
- Normalizes and extracts entities (order numbers, product info, amounts)
- Classifies ticket intent into 8 categories (refund, return/exchange, account issue, etc.)
- Assesses risk using 8 deterministic risk flags
- Retrieves relevant knowledge from a PostgreSQL-based hybrid retrieval engine (keyword + vector search)
- Optionally generates evidence-grounded draft replies with numbered citations
- Provides a Streamlit-based human review console for Approve/Edit/Escalate/Reject actions
- Persists review decisions to append-only JSONL audit trail

### What TicketPilot Does NOT Do

- Does not auto-send replies (human review required by design)
- Does not connect to real LLM providers (FakeDraftProvider only)
- Does not use real embedding providers (FakeEmbeddingProvider only — pipeline verification)
- Does not have authentication or multi-user support
- Does not have a production web server or deployment
- Does not have an evaluation pipeline or golden-answer test sets
- Does not persist retrieval or draft traces to a database (in-memory only)

## Backend Workflow Layers

TicketPilot's architecture follows a stage-based pipeline pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                     RawTicket Input                          │
│              (original_text, submitted_at, customer_id)      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Intake                                             │
│  - Text normalization (whitespace, encoding)                 │
│  - Entity extraction (order numbers, product info, amounts)  │
│  Output: NormalizedTicket                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Classification                                     │
│  - Rule-based intent classification (8 classes)              │
│  - Chinese keyword matching with synonyms and regex          │
│  Output: ClassificationResult                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Risk Assessment                                    │
│  - 8 risk flags (6 substantive + 2 meta)                    │
│  - Severity calculation (LOW/MEDIUM/HIGH)                   │
│  - must_human_review flagging                                │
│  Output: RiskAssessment                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Knowledge Retrieval                                │
│  - Query construction from ticket state                     │
│  - Hybrid keyword + vector search                            │
│  - RRF fusion                                                │
│  - Evidence candidate mapping                                │
│  Output: TicketOutput (with evidence_candidates + trace)     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Draft Generation (OPTIONAL)                        │
│  - generate_draft(ticket_output)                             │
│  - FakeDraftProvider (template-based, deterministic)         │
│  - CitationValidator (regex-based guardrail)                 │
│  - No-evidence / high-risk safe fallback                    │
│  Output: DraftReply                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: Human Review Console                               │
│  - Streamlit single-page application                         │
│  - View ticket, risk, evidence, draft                        │
│  - Approve / Edit / Escalate / Reject actions                │
│  - Append-only JSONL persistence (ReviewStore)               │
│  - No auto-send (decision-recording only)                    │
│  Output: ReviewDecision (persisted to JSONL)                 │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Knowledge / Retrieval Components

- **PostgreSQL + pgvector**: Vector database for hybrid retrieval with HNSW index (`m=16`, `ef_construction=200`, `ef_search=100`, cosine distance)
- **Keyword search**: PostgreSQL full-text search with `simple` config and GIN index; 8-term Chinese business keyword LIKE fallback
- **FakeEmbeddingProvider**: Deterministic 384-dim pseudo-random vectors from SHA-256 hashes — PIPELINE VERIFICATION ONLY, no semantic meaning
- **RRF Fusion**: Reciprocal Rank Fusion with `k=60` combining keyword and vector rankings
- **Two-layer source architecture**: `knowledge_faq`, `knowledge_policy`, `knowledge_case` source tables + unified `knowledge_chunks` table with `source_table`/`source_id` foreign key columns
- **Parent-child chunking**: Two-level chunking (level 1: 500-1000 tokens, level 2: 100-300 tokens) with `parent_chunk_id` linkage
- **Query builder**: Constructs Chinese retrieval queries from normalized text + intent terms + risk-flag terms; meta flags excluded from expansion

### Drafting Components

- **generate_draft(ticket_output)**: Standalone composition function that wires FakeDraftProvider + CitationValidator
- **FakeDraftProvider**: Deterministic template-based Chinese reply generator; no LLM, no network, no API keys
- **CitationValidator**: Regex-based guardrail checking citation existence and claim-coverage; flags "根据", "按照", "可以", "承诺", "退款", "赔偿" keywords without citation markers
- **run_pipeline_with_draft()**: Optional entrypoint combining 4-stage pipeline with draft generation

### Review Components

- **ReviewAction enum**: APPROVE, EDIT, ESCALATE, REJECT
- **ReviewDecision Pydantic model**: Self-contained audit snapshot with 15+ fields
- **ReviewStore**: Append-only JSONL persistence (save, load_all, count)
- **determine_trigger_reasons()**: Pure function that inspects risk flags, fallback reason, and unsupported claims
- **build_review_decision()**: Pure data-transformation function converting DraftedTicketResult + action into ReviewDecision

## Optional Review Console

The Streamlit console (`src/ticketpilot/review/console.py`) is an **MVP prototype**, not a production frontend. It provides:

- RawTicket JSON input and pipeline processing
- Display of ticket info, risk assessment, evidence candidates, citations, and draft reply
- Approve/Edit/Escalate/Reject action buttons
- Review history display with total record count
- Explicit "审核控制台 — 不自动发送回复" disclaimer

The console has **no send functionality**. All four actions only persist a `ReviewDecision` to local JSONL.

## Deferred Production Concerns

The following are explicitly deferred from the MVP scope:

- Real embedding provider (small 384-d and quality 768-d tiers planned but not implemented)
- Real LLM provider (OpenAI, Claude, etc.) — AbstractDraftProvider interface ready but no implementation
- Evaluation pipeline with golden-answer test sets and automated metrics
- Realistic enterprise data pack (current seed data is synthetic: 12 FAQ, 12 Policy, 12 Case documents)
- Trace persistence (RetrievalTrace and DraftGenerationTrace are in-memory only)
- LangGraph workflow orchestration (in pyproject.toml but no code exists)
- Production deployment (Docker, cloud, CI/CD)
- Authentication / multi-user review workflow
- Auto-send / reply dispatch integration with customer service platforms
- Database-backed ReviewStore (replacing JSONL)
- Trace dashboard and observability (Langfuse, Ragas)
