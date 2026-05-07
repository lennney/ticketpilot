# TicketPilot Architecture

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
- Does not connect to real LLM providers by default (FakeLLMProvider only — pipeline verification)
  - Real LLM providers are opt-in via `TICKETPILOT_LLM_PROVIDER=openai_compatible` + `.env.local` API keys
- Does not use real embedding providers by default (FakeEmbeddingProvider only — pipeline verification)
  - Real embedding providers are opt-in via `.env.local` configuration
- Does not have authentication or multi-user support
- Does not have a production web server or deployment
- Does not have a production evaluation pipeline or golden-answer test sets
- Does not persist retrieval or draft traces to a database (in-memory only)

---

## Backend Workflow Layers

TicketPilot's architecture follows a stage-based pipeline pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                     RawTicket Input                          │
│              (original_text, submitted_at, customer_id)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Intake                                            │
│  - Text normalization (whitespace, encoding)                 │
│  - Entity extraction (order numbers, product info, amounts)  │
│  Output: NormalizedTicket                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Classification                                    │
│  - Rule-based intent classification (8 classes)             │
│  - Chinese keyword matching with synonyms and regex         │
│  Output: ClassificationResult                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Risk Assessment                                    │
│  - 8 risk flags (6 substantive + 2 meta)                    │
│  - Severity calculation (LOW/MEDIUM/HIGH)                   │
│  - must_human_review flagging                               │
│  Output: RiskAssessment                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Knowledge Retrieval                                │
│  - Query construction from ticket state                    │
│  - Hybrid keyword + vector search                           │
│  - RRF fusion                                              │
│  - Evidence candidate mapping                              │
│  Output: TicketOutput (with evidence_candidates + trace)    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Draft Generation (OPTIONAL)                       │
│  - generate_draft(ticket_output)                            │
│  - FakeDraftProvider (template-based, deterministic)        │
│  - CitationValidator (regex-based guardrail)               │
│  - No-evidence / high-risk safe fallback                   │
│  Output: DraftReply                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: Human Review Console                              │
│  - Streamlit single-page application                        │
│  - View ticket, risk, evidence, draft                      │
│  - Approve / Edit / Escalate / Reject actions               │
│  - Append-only JSONL persistence (ReviewStore)             │
│  - No auto-send (decision-recording only)                   │
│  Output: ReviewDecision (persisted to JSONL)                │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Intake / Normalization

**Function:** `intake_pipeline(raw_ticket)` in `src/ticketpilot/intake/pipeline.py`

Steps:
1. Text normalization — strip whitespace, normalize unicode, clean formatting
2. Entity extraction — regex patterns for Chinese order numbers, product info, monetary amounts

**Graceful degradation:** If intake fails, returns empty `NormalizedTicket` with `language="unknown"`.

### Layer 2: Classification

**Function:** `IntentClassifier().classify(text)` in `src/ticketpilot/classification/classifier.py`

Steps:
1. Rule-based keyword matching with Chinese synonyms and regex patterns
2. 8 intent classes: REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER

**Graceful degradation:** If classification fails, returns `IntentClass.OTHER` with `confidence=0.5`.

### Layer 3: Risk Assessment

**Function:** `RiskAssessor().assess(normalized_ticket, classification)` in `src/ticketpilot/risk/assessor.py`

Steps:
1. Check 6 keyword-based substantive risk rules (COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT)
2. Check INSUFFICIENT_EVIDENCE — triggered when ticket has no order numbers, no product info, and short text (1-9 characters)
3. Check LOW_CONFIDENCE — triggered when classification confidence < 0.7
4. Calculate severity: 0-1 substantive flags = LOW, 2 = MEDIUM, 3+ = HIGH; LEGAL_RISK always = HIGH
5. Set `must_human_review` — True when any risk flags are present

**Graceful degradation:** If risk assessment fails, returns `must_human_review=True` with `LOW_CONFIDENCE` flag.

### Layer 4: Retrieval (Evidence Candidates)

**Function:** `retrieve_evidence(normalized_text, intent, risk_flags)` in `src/ticketpilot/retrieval/retrieve_evidence.py`

Steps:
1. **Query construction** (`build_retrieval_query` in `src/ticketpilot/retrieval/query_builder.py`): Combines normalized text + intent terms + risk-flag terms; meta flags excluded from expansion
2. **Hybrid retrieval** (`hybrid_retrieval` in `src/ticketpilot/retrieval/pipeline.py`): Keyword search via PostgreSQL FTS + vector search via pgvector HNSW + RRF fusion with k=60
3. **Evidence mapping** (`map_fused_to_evidence`): Maps fused results to `EvidenceCandidate` with source metadata

**Empty evidence handling:** Retrieval failures degrade gracefully — empty evidence + `INSUFFICIENT_EVIDENCE` flag.

### Layer 5: Draft Generation (Optional)

**Entrypoint:** `generate_draft(ticket_output)` in `src/ticketpilot/drafting/generate.py`

Safety paths:
- **No evidence**: Safe fallback message with no policy promises, confidence=0.0, no citations
- **High risk**: Draft generated but `must_human_review=True`, confidence capped at 0.5
- **Unsupported claims detected**: `must_human_review=True`, `unsupported_claims` populated
- **Exception**: Safe fallback draft returned (never crashes)

### Layer 6: Human Review (Optional)

**Interface:** Streamlit single-page application (`src/ticketpilot/review/console.py`)

Actions: APPROVE / EDIT / ESCALATE / REJECT. Each action appends `ReviewDecision` to JSONL. No action sends the draft anywhere.

---

## Components

### Knowledge / Retrieval Components

- **PostgreSQL + pgvector**: Vector database for hybrid retrieval with HNSW index (`m=16`, `ef_construction=200`, `ef_search=100`, cosine distance)
- **Keyword search**: PostgreSQL full-text search with `simple` config and GIN index; 8-term Chinese business keyword LIKE fallback
- **FakeEmbeddingProvider**: Deterministic 384-dim pseudo-random vectors from SHA-256 hashes — PIPELINE VERIFICATION ONLY, no semantic meaning
- **RRF Fusion**: Reciprocal Rank Fusion with `k=60` combining keyword and vector rankings
- **Two-layer source architecture**: `knowledge_faq`, `knowledge_policy`, `knowledge_case` source tables + unified `knowledge_chunks` table
- **Parent-child chunking**: Two-level chunking (level 1: 500-1000 tokens, level 2: 100-300 tokens) with `parent_chunk_id` linkage
- **Query builder**: Constructs Chinese retrieval queries from normalized text + intent terms + risk-flag terms; meta flags excluded from expansion

### Drafting Components

- **generate_draft(ticket_output)**: Standalone composition function that wires LLM provider + CitationValidator
- **FakeLLMProvider**: Deterministic template-based Chinese reply generator; no LLM, no network, no API keys
- **OpenAICompatibleProvider**: Real LLM provider via OpenAI-compatible API endpoint; opt-in via `TICKETPILOT_LLM_PROVIDER=openai_compatible` + `.env.local` API keys; human review always required
- **CitationValidator**: Regex-based guardrail checking citation existence and claim-coverage
- **run_pipeline_with_draft()**: Optional entrypoint combining 4-stage pipeline with draft generation

### Review Components

- **ReviewAction enum**: APPROVE, EDIT, ESCALATE, REJECT
- **ReviewDecision Pydantic model**: Self-contained audit snapshot with 15+ fields
- **ReviewStore**: Append-only JSONL persistence (save, load_all, count)
- **determine_trigger_reasons()**: Pure function that inspects risk flags, fallback reason, and unsupported claims
- **build_review_decision()**: Pure data-transformation function converting DraftedTicketResult + action into ReviewDecision

### Chat Components (Phase 15+)

- **Chat module** (`src/ticketpilot/chat/`): Streamlit-based multi-turn chat interface for ticket triage sessions
- **ChatDisplay** schema: Maps `TicketOutput` to chat UI display with risk badge, evidence panel, and AI draft
- **ticket_output_to_chat_display()**: Adapter function wiring pipeline output to `ChatDisplay`
- **ChatSession** / **ChatState**: Multi-turn session management with conversation history
- **EvidenceDisplayItem**: Structured evidence display with chunk_id, content snippet, source type, and relevance score
- Risk decision matrix: severity × evidence × guard → `human_review_required` in chat context
- Phase 15.4+ connects risk escalation display, evidence/draft panels, and human review queue
- **Boundary**: High-risk outputs require human review — TicketPilot never sends customer replies automatically

---

## Pipeline Integrity Guarantees

1. **Mandatory stages are always processed**: Intake, classification, and risk assessment all have graceful degradation paths. The pipeline never crashes.
2. **Stage 4 is isolated**: Retrieval failures degrade gracefully — empty evidence + `INSUFFICIENT_EVIDENCE` flag.
3. **Immutable flag handling**: The `_with_added_risk_flag()` helper creates a new `RiskAssessment` with the added flag, never mutating the original `flags` set.
4. **No auto-send**: The pipeline produces outputs (TicketOutput, DraftReply) and records decisions (ReviewDecision) but never dispatches replies.
5. **Backward compatible composition**: Optional stages do not change the default `TicketOutput` return type. Existing consumers are unaffected.

---

## Deferred Production Concerns

The following are explicitly deferred from MVP scope:

- Evaluation pipeline with golden-answer test sets and automated metrics
- Realistic enterprise data pack (current seed data is synthetic)
- Trace persistence (RetrievalTrace and DraftGenerationTrace are in-memory only)
- LangGraph workflow orchestration (in pyproject.toml but no code exists)
- Production deployment (Docker, cloud, CI/CD)
- Authentication / multi-user review workflow
- Auto-send / reply dispatch integration
- Database-backed ReviewStore (replacing JSONL)
- Chat module trace dashboard and observability (Langfuse, Ragas)