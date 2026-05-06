# TicketPilot Interview Talking Points

## 30-Second Pitch

"TicketPilot is a Chinese customer support ticket triage copilot that I built through 5 iterative phases using spec-driven development. It takes unstructured Chinese support tickets, runs them through a four-stage pipeline — intake normalization, intent classification, risk assessment, and hybrid knowledge retrieval — then optionally generates evidence-grounded draft replies with ClaimGuard validation. A human review console provides approve/edit/escalate/reject controls with a full audit trail. The system is designed with safety constraints: no auto-send, fake embeddings by default for pipeline verification, and no real LLM dependency by default. What distinguishes it is not feature count but the iteration story: each phase used evaluation to identify the next bottleneck, rather than blindly stacking capabilities."

## 1-Minute Pitch

"TicketPilot addresses unstructured Chinese customer support ticket processing. Customer service teams receive thousands of free-text tickets daily and need to triage them while assessing risk. I built a six-layer modular pipeline: intake normalizes text and extracts entities, classification determines intent across 8 categories, risk assessment flags 8 risk types, hybrid retrieval uses FTS + HNSW + RRF fusion, draft generation produces evidence-grounded replies, and a Streamlit console handles human review. Every decision is recorded in an append-only JSONL audit trail.

The project went through 5 distinct phases: data foundation (10→101 tickets), real embedding comparison (discovered bottleneck was knowledge coverage, not model quality), evaluation-driven knowledge optimization (discovered a config silent fallback bug and built Provider Identity Gate), granular evaluation (78% of 'errors' were actually measurement granularity issues, Doc-ID Recall@10=91.9%), and evidence-grounded LLM draft generation with 8-layer safety architecture (complete)."

## 3-Minute Technical Walkthrough

### Architecture

"TicketPilot uses a stage-based pipeline architecture in Python. The core 4-stage pipeline consists of intake, classification, risk assessment, and retrieval. Each stage has try/except graceful degradation — a failure in any stage produces fallback values and continues."

### Intake (Stage 1)

"Normalizes Chinese text — stripping whitespace, normalizing unicode — and extracts entities using regex patterns for Chinese order numbers, product mentions, and monetary amounts."

### Classification (Stage 2)

"Deterministic keyword matching with Chinese synonyms. 8 intent classes: REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, and OTHER."

### Risk Assessment (Stage 3)

"Chinese keyword patterns for 8 flags: 6 substantive (complaint, compensation, legal, privacy, account security, policy conflict) and 2 meta (low confidence, insufficient evidence). Severity is LOW for 0-1 flags, MEDIUM for 2, HIGH for 3+. LEGAL_RISK always produces HIGH severity."

### Retrieval (Stage 4)

"Hybrid approach: PostgreSQL full-text search with GIN index for keyword matching, plus pgvector HNSW (m=16, ef_construction=200) for vector similarity. Results fused via RRF with k=60. Dual provider architecture: FakeEmbeddingProvider (384-d deterministic hash, default) verifies pipeline mechanics; DashScope text-embedding-v4 (1024-d, opt-in) provides real Chinese semantic retrieval."

### Draft Generation (Stage 5, Optional)

"Dual provider: FakeDraftProvider (template-based) and FakeLLMProvider (evidence-constrained, deterministic). Evidence-grounded PromptBuilder converts evidence + safety rules into structured prompts. CitationValidator + ClaimGuard for integrity checking."

### Human Review (Stage 6, Optional)

"Streamlit console with four actions: APPROVE, EDIT, ESCALATE, REJECT. Append-only JSONL via ReviewStore."

### Quality Gate

"5-stage gate: Ruff (0 errors), unit tests (~856 pass, >70% coverage), integration tests (119 pass, 0 skipped), OpenSpec validation, and secret scanning."

## The Iteration Story (Key Differentiator)

### Phase 8 Lesson

"The most valuable finding was NOT that Top-1 improved 10%. It was that fake and real embeddings had IDENTICAL 41 wrong cases — all missing_doc_type. This told us the bottleneck was knowledge coverage, not embedding quality. The product judgment: don't throw better models at a knowledge gap problem."

### Phase 9 Lesson

"We added 11 targeted knowledge records. Fake eval showed regression. After digging, found `load_dotenv()` was never called — all config silently fell back to fake. The fix flipped the results. This taught me: you can't trust metrics from an unknown source. Built Provider Identity Gate to verify runtime provider identity on every evaluation run."

### Phase 10 Lesson

"Doc-type level evaluation was too coarse. We built doc-ID level golden labels (14→86 cases). Doc-ID Recall@10=91.9%, 32.5pp above doc-type. 78% of 'wrong' cases were actually evaluation granularity issues — the system found the right document type but was penalized for not matching the specific doc ID in the golden label. This taught me: check your measurement before declaring the system broken."

## Product Manager Angle

- Problem validation: Customer support ticket triage is a universal pain point for Chinese e-commerce
- Scope discipline: Deliberately MVP-scoped — fake embeddings, synthetic data, no real LLM
- Iterative delivery: 5 phases, each answering a specific product question through evaluation
- Risk-first design: Flags high-risk tickets for mandatory human review; no auto-send
- Evaluation-driven: Every phase used data to determine the next bottleneck, not hunches

## AI Application Engineering Angle

- Spec-driven development: proposal → design → spec → tasks → quality gate → archive
- Provider pattern: AbstractDraftProvider, LLMProvider, EmbeddingProvider — all switchable
- Graceful degradation: Pipeline stages never crash — failures produce fallback values
- Provider Identity Gate: Runtime verification prevents silent provider fallback
- Human-in-the-loop: Four action types, self-contained audit snapshots

## Risk/Control Angle

- No auto-send: Records decisions, never sends replies
- Human review mandatory for all risk scenarios
- Append-only audit trail for compliance
- ClaimGuard: Forbidden promise detection, statement validation
- Graceful failure: retrieval failure produces INSUFFICIENT_EVIDENCE flag

## What I Personally Contributed

- Full 6-layer pipeline architecture design and implementation
- Intake normalization with Chinese entity extraction
- Rule-based intent classification (8 classes) and risk assessment (8 flags)
- Hybrid retrieval engine with keyword + vector search and RRF fusion
- Dual embedding provider architecture (Fake 384-d / Real 1024-d) with comparison evaluation
- Wrong-case taxonomy (8 failure categories) and evaluation-driven knowledge optimization
- Provider Identity Gate — runtime provider verification
- Doc-ID granular evaluation pipeline (Doc-ID Recall@10=91.9%)
- Streamlit human review console with 4-action review model
- OpenSpec spec-driven development workflow and quality gate
- 5-phase iteration planning: each phase driven by evaluation findings

## What I Learned

- Evaluation-driven iteration: each phase answers a specific product question
- Provider Identity Gate: don't trust metrics from an unknown source
- Measurement granularity matters: doc-type evaluation was hiding 78% of real performance
- Bottleneck identification: distinguishing between model quality, knowledge coverage, and measurement issues
- Chinese NLP challenges: PostgreSQL FTS simple config does not tokenize Chinese
- Spec-driven development discipline catches design issues early

## Likely Interviewer Questions and Answer Bullets

### Q: Why is this not just a normal RAG demo?

"This is not just RAG because RAG is only one layer (Stage 4) of a six-layer system. What distinguishes TicketPilot: (1) full pipeline including intake, classification, risk assessment, retrieval, drafting, and human review; (2) human-in-the-loop with audit trail; (3) safety architecture — no auto-send, mandatory review for risk; (4) 5-phase iteration driven by evaluation findings; (5) Provider Identity Gate for metric integrity."

### Q: Why human-in-the-loop?

"Three reasons: (1) Compliance — automated reply sending has regulatory implications. Human review is a safety gate. (2) Quality control — even real LLMs can produce inappropriate replies. (3) Audit trail — every decision is a self-contained snapshot. The decision-recording-only approach is deliberate."

### Q: What did Phase 8 teach you?

"That the bottleneck was knowledge coverage, not embedding quality. Fake and real embeddings had identical 41 wrong cases. Top-1 improved 10% but the fundamental limitation was the same. This taught me to always ask: is this a model problem or a data problem?"

### Q: What is Provider Identity Gate?

"A runtime check that records which provider actually generated each evaluation result. I discovered in Phase 9 that `python-dotenv` was installed but never called — all `.env.local` config was silently ignored, and we'd been making iteration decisions based on fake provider metrics. The gate prevents this by logging the actual provider identity with every evaluation run."

### Q: What was Phase 10's most important finding?

"That doc-type level evaluation was hiding 78% of the system's real performance. Doc-ID Recall@10 jumped from 59.4% to 91.9% when we refined the measurement. The system wasn't failing — the measurement was too coarse. This taught me to validate measurement methodology before making system-level judgments."

### Q: How do you evaluate this system?

"Multiple layers: 7 pipeline metrics (intent accuracy, severity accuracy, risk flag F1, evidence recall, etc.), retrieval comparison mode (Fake vs Real embedding), and doc-ID granular evaluation (Recall@10=91.9%). CSV mode loads pre-computed predictions; Pipeline mode runs the full pipeline; comparison mode evaluates embedding quality. No-auto-send=100% is an architectural constraint."

### Q: What would you improve next?

"Phase 11 completion — real LLM provider integration and offline draft evaluation metrics. Then back to Phase 10's findings: 7 zero-hit cases for query expansion, 32 partial-hit cases for RRF tuning."

### Q: What does this project say about your product sense?

"It shows I design with iteration in mind. Each phase started with a clear question, used evaluation to get an answer, and used that answer to decide what to do next. Phase 8 answered 'is the bottleneck model quality or data coverage?' Phase 9 answered 'can we trust our metrics?' Phase 10 answered 'is our measurement correct?' These are product judgment questions, not just engineering tasks."

### Q: How do you prevent the system from making things up?

"Three layers: (1) Risk assessment gates — high-risk signals force human review. (2) ClaimGuard — detects uncited claims, forbidden promises (refund amounts, legal liability, account changes), and risk-aware escalation. (3) Architectural — the system never auto-sends anything. All outputs are draft suggestions requiring human approval."
