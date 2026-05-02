# Workflow Pipeline

## Overview

The TicketPilot pipeline processes raw Chinese customer support tickets through 4 mandatory stages (intake, classification, risk assessment, retrieval) and 2 optional stages (draft generation, human review). The 4-stage pipeline is the core contract; the optional stages compose on top without modifying the default return type.

## Default Pipeline (4-Stage)

### Stage 1: Intake / Normalization

**Input:** `RawTicket` (original_text, submitted_at, customer_id)

**Function:** `intake_pipeline(raw_ticket)` in `src/ticketpilot/intake/pipeline.py`

**Steps:**
1. Text normalization — strip whitespace, normalize unicode, clean formatting
2. Entity extraction — regex patterns for Chinese order numbers (数字+数字格式), product info mentions, monetary amounts (人民币符号+数字格式)

**Graceful degradation:** If intake fails, an empty `NormalizedTicket` is returned with `language="unknown"`.

**Output:** `NormalizedTicket` (text, language, order_numbers, product_info, amount, cleaned_at)

### Stage 2: Classification

**Input:** `NormalizedTicket`

**Function:** `IntentClassifier().classify(text)` in `src/ticketpilot/classification/classifier.py`

**Steps:**
1. Rule-based keyword matching with Chinese synonyms and regex patterns
2. 8 intent classes: REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER

**Graceful degradation:** If classification fails, returns `IntentClass.OTHER` with `confidence=0.5`.

**Output:** `ClassificationResult` (intent, confidence, classified_at)

### Stage 3: Risk Assessment

**Input:** `NormalizedTicket`, `ClassificationResult`

**Function:** `RiskAssessor().assess(normalized_ticket, classification)` in `src/ticketpilot/risk/assessor.py`

**Steps:**
1. Check 6 keyword-based substantive risk rules (COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT)
2. Check INSUFFICIENT_EVIDENCE — triggered when ticket has no order numbers, no product info, and short text (1-9 characters)
3. Check LOW_CONFIDENCE — triggered when classification confidence < 0.7
4. Calculate severity: 0-1 substantive flags = LOW, 2 = MEDIUM, 3+ = HIGH; LEGAL_RISK always = HIGH
5. Set `must_human_review` — True when any risk flags are present

**Graceful degradation:** If risk assessment fails, returns `must_human_review=True` with `LOW_CONFIDENCE` flag.

**Output:** `RiskAssessment` (flags, severity, must_human_review, assessed_at)

### Stage 4: Retrieval (Evidence Candidates)

**Input:** NormalizedTicket text, ClassificationResult intent, RiskAssessment flags

**Function:** `retrieve_evidence(normalized_text, intent, risk_flags)` in `src/ticketpilot/retrieval/retrieve_evidence.py`

**Steps:**
1. **Query construction** (`build_retrieval_query` in `src/ticketpilot/retrieval/query_builder.py`):
   - Combines normalized ticket text + intent-derived Chinese business terms + risk-flag-derived terms
   - Meta flags (LOW_CONFIDENCE, INSUFFICIENT_EVIDENCE) are excluded from query expansion
   - Terms are deduplicated preserving insertion order
2. **Hybrid retrieval** (`hybrid_retrieval` in `src/ticketpilot/retrieval/pipeline.py`):
   - Keyword search via PostgreSQL FTS (`to_tsvector('simple', content)`) with GIN index
   - Vector search via pgvector HNSW (cosine distance, ef_search=100)
   - RRF fusion with k=60 combining both rankers
3. **Evidence mapping** (`map_fused_to_evidence` in `src/ticketpilot/retrieval/evidence_mapper.py`):
   - Maps FusedResult to EvidenceCandidate, adding source_table and rank information

**Empty evidence handling:** If no candidates are returned (or retrieval fails), `RiskFlag.INSUFFICIENT_EVIDENCE` is added to risk flags and `must_human_review` is set to True via the `_with_added_risk_flag()` helper (immutable flag addition).

**Graceful degradation:** Stage 4 is isolated in its own try/except. Retrieval failures never break the pipeline — empty evidence and `INSUFFICIENT_EVIDENCE` flag are returned instead.

**Output:** `TicketOutput` with `evidence_candidates: list[EvidenceCandidate]` and `retrieval_trace: RetrievalTrace | None`

## Optional Draft / Review Workflow

### Stage 5: Draft Generation (Optional)

**Entrypoint:** `generate_draft(ticket_output)` in `src/ticketpilot/drafting/generate.py` or `run_pipeline_with_draft(raw_ticket)` in `src/ticketpilot/drafting/pipeline.py`

**Behavior:**
- `generate_draft()` is a standalone composition function — takes `TicketOutput`, returns `DraftReply`
- `run_pipeline_with_draft()` composes `intake_risk_pipeline()` + `generate_draft()` — takes `RawTicket`, returns `DraftedTicketResult`
- Default `intake_risk_pipeline()` is unchanged — `TicketOutput` return type preserved

**Safety paths:**
- **No evidence**: Safe fallback message with no policy promises, confidence=0.0, no citations
- **High risk**: Draft generated but `must_human_review=True`, confidence capped at 0.5
- **Unsupported claims detected**: `must_human_review=True`, `unsupported_claims` populated
- **Exception**: Safe fallback draft returned (never crashes), `fallback_reason="generation_error"`

### Stage 6: Human Review (Optional)

**Interface:** Streamlit single-page application (`src/ticketpilot/review/console.py`)

**Actions:**
- **APPROVE**: Accept the draft as-is, record approval
- **EDIT**: Modify the draft text, store both original and edited versions
- **ESCALATE**: Flag for senior review, capture escalation reason
- **REJECT**: Reject the draft, capture rejection reason

**Review decision persistence:** Each action appends a `ReviewDecision` record to the `ReviewStore` (append-only JSONL). No action sends the draft anywhere — the console is a decision-recording interface, not a reply-sending interface.

### Pipeline Orchestration

```
RawTicket
    │
    ▼
intake_pipeline()  ──── Stage 1: Intake (normalize + extract entities)
    │
    ▼
classify()         ──── Stage 2: Classification (rule-based, 8 intents)
    │
    ▼
assess()           ──── Stage 3: Risk Assessment (8 risk flags)
    │
    ▼
retrieve_evidence()──── Stage 4: Retrieval (hybrid keyword + vector, RRF)
    │
    ▼
TicketOutput       ──── Core pipeline output (mandatory)
    │
    ├── (optional) generate_draft(ticket_output)  ──── DraftReply
    │
    └── (optional) run_pipeline_with_draft(raw_ticket)
                      └── compose(Stage 1-4, generate_draft)
                          └── DraftedTicketResult
                               │
                               └── Streamlit Review Console
                                    └── ReviewDecision → ReviewStore (JSONL)
```

## Pipeline Integrity Guarantees

1. **Mandatory stages are always processed**: Intake, classification, and risk assessment all have graceful degradation paths. The pipeline never crashes.
2. **Stage 4 is isolated**: Retrieval failures degrade gracefully — empty evidence + `INSUFFICIENT_EVIDENCE` flag.
3. **Immutable flag handling**: The `_with_added_risk_flag()` helper creates a new `RiskAssessment` with the added flag, never mutating the original `flags` set.
4. **No auto-send**: The pipeline produces outputs (TicketOutput, DraftReply) and records decisions (ReviewDecision) but never dispatches replies.
5. **Backward compatible composition**: Optional stages do not change the default `TicketOutput` return type. Existing consumers are unaffected.
