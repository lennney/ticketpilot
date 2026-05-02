# TicketPilot Interview Talking Points

## 30-Second Pitch

"TicketPilot is a Chinese customer support ticket triage copilot that I built from scratch using spec-driven development. It takes unstructured Chinese support tickets, runs them through a four-stage pipeline -- intake normalization, intent classification, risk assessment, and hybrid knowledge retrieval -- then optionally generates evidence-grounded draft replies. A human review console provides approve/edit/escalate/reject controls with a full audit trail. The system is designed with safety constraints: no auto-send, fake embeddings for pipeline verification only, and no real LLM dependency. It is a functional MVP with clear documentation of what is and is not production-ready."

## 1-Minute Pitch

"TicketPilot addresses the problem of unstructured Chinese customer support tickets. Customer service teams receive thousands of free-text tickets daily -- refund requests, complaints, account issues -- and need to triage them quickly while assessing risk. I built a six-layer modular pipeline: Stage 1 normalizes text and extracts entities, Stage 2 classifies intent into 8 categories using rule-based keyword matching, Stage 3 assesses risk across 8 flags, Stage 4 performs hybrid retrieval using PostgreSQL full-text search and pgvector HNSW with RRF fusion, Stage 5 optionally generates evidence-grounded draft replies using a deterministic FakeDraftProvider, and Stage 6 provides a Streamlit human review console. Every decision is recorded in an append-only JSONL audit trail. The system never sends replies automatically -- that is an explicit architectural constraint."

## 3-Minute Technical Walkthrough

### Architecture

"TicketPilot uses a stage-based pipeline architecture in Python. The core 4-stage pipeline is in src/ticketpilot/pipeline.py and consists of intake, classification, risk assessment, and retrieval. Each stage has try/except graceful degradation -- a failure in any stage produces fallback values and continues."

### Intake (Stage 1)

"The intake module normalizes Chinese text -- stripping whitespace, normalizing unicode -- and extracts entities using regex patterns for Chinese order numbers, product mentions, and monetary amounts."

### Classification (Stage 2)

"Classification uses deterministic keyword matching with Chinese synonyms and regex patterns. There are 8 intent classes: REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, and OTHER."

### Risk Assessment (Stage 3)

"Risk assessment uses Chinese keyword patterns for 8 flags: 6 substantive (complaint, compensation, legal, privacy, account security, policy conflict) and 2 meta (low confidence, insufficient evidence). Severity is LOW for 0-1 flags, MEDIUM for 2, HIGH for 3+. LEGAL_RISK always produces HIGH severity."

### Retrieval (Stage 4)

"Retrieval uses a hybrid approach: PostgreSQL full-text search with a simple config and GIN index for keyword matching, plus pgvector HNSW (m=16, ef_construction=200) for vector similarity. Results are fused via RRF with k=60. The knowledge base has a two-layer architecture: three source tables with type-specific columns, plus a unified knowledge_chunks table for single-query retrieval. Parent-child chunking provides both precise passage matching and full context."

"The FakeEmbeddingProvider generates deterministic 384-dim pseudo-random vectors from SHA-256 hashes. This proves pipeline mechanics but has no semantic meaning."

### Draft Generation (Stage 5, Optional)

"Draft generation uses an AbstractDraftProvider interface with a single FakeDraftProvider implementation -- template-based, deterministic, no LLM calls. The CitationValidator performs regex-based unsupported claim detection. Safety paths: no-evidence produces a safe generic message, high-risk caps confidence at 0.5 and sets must_human_review."

### Human Review (Stage 6, Optional)

"The Streamlit console provides four actions: APPROVE, EDIT, ESCALATE, REJECT. Each action records a ReviewDecision with a full audit snapshot. Persistence is append-only JSONL via ReviewStore."

### Quality Gate

"The project maintains a strict quality gate script with 5 stages: Ruff linting (0 errors), unit tests (325 pass, minimum 70% coverage), integration tests (74 pass, 0 skipped), OpenSpec validation, and secret scanning."

## Product Manager Angle

- Problem validation: Customer support ticket triage is a universal pain point for Chinese e-commerce platforms
- Scope discipline: The project deliberately scoped to MVP -- fake embeddings, seed data, no real LLM
- Iterative delivery: 6 OpenSpec changes delivered incrementally with quality gates
- Risk-first design: Flags high-risk tickets for mandatory human review; no auto-send by design
- Demonstrable progress: End-to-end pipeline works with Streamlit UI

## AI Application Engineering Angle

- Spec-driven development: Every non-trivial change followed proposal -> design -> spec -> tasks -> quality gate -> archive
- Provider pattern: AbstractDraftProvider and EmbeddingProvider interfaces allow easy swap of implementations
- Graceful degradation: Pipeline stages never crash -- failures produce fallback values
- Human-in-the-loop: Four action types, self-contained audit snapshots, append-only persistence
- Immutable state: Risk flags are never mutated in place

## Risk/Control Angle

- No auto-send: The system records decisions, never sends replies
- Human review mandatory for all risk scenarios
- Append-only audit trail for compliance
- Graceful failure mode: retrieval failure produces INSUFFICIENT_EVIDENCE flag
- Current limitations: no authentication, no multi-user workflow

## What I Personally Contributed

- Designed and implemented the full 6-layer pipeline architecture
- Built intake normalization with Chinese entity extraction
- Implemented rule-based intent classification (8 classes) and risk assessment (8 flags)
- Designed hybrid retrieval engine with keyword + vector search and RRF fusion
- Implemented FakeEmbeddingProvider for pipeline verification
- Designed optional draft generation workflow with provider pattern
- Built Streamlit human review console with 4-action review model
- Established OpenSpec spec-driven development workflow and quality gate
- Wrote comprehensive development trace and technical documentation
- Enforced documentation truthfulness standards (no exaggerated claims)

## What I Learned

- Spec-driven development discipline: Writing specs before code catches design issues early
- Pipeline architecture for AI systems: Every stage needs graceful degradation
- Fake providers enable full end-to-end testing without external dependencies
- Documentation truthfulness matters: Labeling limitations builds trust
- Batch implementation pattern: Schema -> implementation -> tests -> docs -> quality gate
- Chinese NLP challenges: PostgreSQL FTS with simple config does not tokenize Chinese

## Likely Interviewer Questions and Answer Bullets

### Q: Why is this not just a normal RAG demo?

"This is not just RAG because RAG is only one layer (Stage 4) of a six-layer system. What distinguishes TicketPilot: (1) the full pipeline including intake, classification, risk assessment, retrieval, optional drafting, and human review; (2) human-in-the-loop with four action types and append-only audit trail; (3) safety architecture -- no auto-send, mandatory review for risk, graceful degradation; (4) spec-driven development process with quality gates; (5) deliberately constrained scope with clear documentation of MVP gaps."

### Q: Why human-in-the-loop?

"Three reasons: (1) Compliance -- automated reply sending has regulatory implications, especially for refunds, compensation, and legal matters. Human review is a safety gate. (2) Quality control -- even real LLMs can produce inappropriate replies. (3) Audit trail -- every decision is a self-contained snapshot for traceability. The decision-recording-only approach is deliberate."

### Q: Why fake embedding now?

"Fake embeddings prove pipeline mechanics without external dependencies. They verify that embedding generation, HNSW indexing, cosine similarity scoring, and RRF fusion all work correctly. The provider is deterministic for reproducible tests. The tradeoff is explicit: no semantic meaning, so retrieval quality cannot be evaluated. This is acceptable because (1) the interface supports straightforward replacement, (2) real evaluation needs both a real provider and an evaluation pipeline, and (3) pipeline mechanics are identical regardless of provider."

### Q: What is still missing for MVP?

"The core workflow (ticket-to-draft-to-review) is complete. Gaps: realistic enterprise data pack (36 synthetic docs), real embedding provider (fake has no semantic meaning), real LLM provider (template replies only), evaluation pipeline (no golden-answer pairs or quality metrics), trace persistence (in-memory only), authentication and multi-user workflow (free-text label only)."

### Q: How do you evaluate this system?

"Current evaluation is process-oriented: 325 unit tests, 74 integration tests, 8 golden cases for smoke testing, automated quality gate. This verifies that each component works and the pipeline runs end-to-end. What is missing: retrieval precision/recall/mRR metrics, draft quality evaluation, hallucination rate, regression benchmarks. The evaluation pipeline is the single biggest gap."

### Q: What would you improve next?

"Build the evaluation pipeline first -- it is the critical enabler. Without it, you cannot measure whether any change improves the system. Then: realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph orchestration, authentication and multi-user review."
