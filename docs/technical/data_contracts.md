# Data Contracts

All data contracts are implemented as Pydantic models. This document lists the input/output boundaries for each pipeline stage, including both required models and optional types.

## Input Boundary

### RawTicket

The sole input to the pipeline. Represents an unprocessed customer support ticket.

**Source:** `src/ticketpilot/schema/ticket.py`

| Field | Type | Description |
|-------|------|-------------|
| `original_text` | `str` | Raw Chinese ticket text |
| `submitted_at` | `datetime` | Timestamp when the ticket was submitted |
| `customer_id` | `str \| None` | Optional customer identifier |

**Input boundary:** All pipelines start from `RawTicket`. There is no other entry point.

## Pipeline Internal Types

### NormalizedTicket

Output of Stage 1 (Intake). A cleaned and entity-enriched version of the raw ticket.

**Source:** `src/ticketpilot/schema/ticket.py`

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Normalized, cleaned text |
| `language` | `str` | Detected language (currently always "zh") |
| `order_numbers` | `list[str]` | Extracted order numbers (default: []) |
| `product_info` | `str \| None` | Extracted product mentions |
| `amount` | `float \| None` | Extracted monetary amount |
| `cleaned_at` | `datetime` | Timestamp of normalization |

### ClassificationResult

Output of Stage 2 (Classification).

**Source:** `src/ticketpilot/schema/ticket.py`

| Field | Type | Description |
|-------|------|-------------|
| `intent` | `IntentClass` | One of 8 intent values (see IntentClass enum) |
| `confidence` | `float` | Classification confidence (0.0 to 1.0) |
| `classified_at` | `datetime` | Timestamp of classification |

**IntentClass enum:** REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER

### RiskAssessment

Output of Stage 3 (Risk Assessment).

**Source:** `src/ticketpilot/schema/ticket.py`

| Field | Type | Description |
|-------|------|-------------|
| `flags` | `set[RiskFlag]` | Set of triggered risk flags (empty set = no flags) |
| `severity` | `RiskSeverity` | Computed severity: LOW, MEDIUM, or HIGH |
| `must_human_review` | `bool` | True when any risk flags are present or INSUFFICIENT_EVIDENCE or unsupported claims |
| `assessed_at` | `datetime` | Timestamp of assessment |

**RiskFlag enum:** COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT, INSUFFICIENT_EVIDENCE, LOW_CONFIDENCE

**RiskSeverity enum:** LOW, MEDIUM, HIGH

### EvidenceCandidate

Part of Stage 4 output. An evidence candidate retrieved from the knowledge base.

**Source:** `src/ticketpilot/schema/evidence.py`

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `UUID` | Knowledge chunk identifier |
| `doc_id` | `UUID` | Source document identifier |
| `doc_type` | `DocType` | Document type: FAQ, POLICY, or CASE |
| `source_id` | `UUID` | Identifier in the source table |
| `source_table` | `str` | Source table name (knowledge_faq, knowledge_policy, or knowledge_case) |
| `content` | `str` | Chunk text content |
| `score` | `float` | RRF fusion score |
| `rank` | `int` | Rank position (1-based, ge=1) |
| `title` | `str \| None` | Optional chunk title |

### RetrievalTrace

Part of Stage 4 output. Contains the full retrieval trace.

**Source:** `src/ticketpilot/retrieval/traces.py`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | The retrieval query used |
| `top_k` | `int` | Maximum results requested |
| `keyword_total` | `int` | Total keyword results |
| `vector_total` | `int` | Total vector results |
| `fused_results` | `list[FusedResult]` | Fused result list (full RRF detail) |
| `retrieved_at` | `datetime` | Timestamp of retrieval |

## Output Boundary

### TicketOutput

The default output of the 4-stage pipeline. Contains all processing results.

**Source:** `src/ticketpilot/schema/ticket.py`

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | `str` | Unique identifier (UUID4) |
| `raw_ticket` | `RawTicket` | Original input (preserved) |
| `normalized_ticket` | `NormalizedTicket` | Stage 1 output |
| `classification` | `ClassificationResult` | Stage 2 output |
| `risk_assessment` | `RiskAssessment` | Stage 3 output |
| `output_at` | `datetime` | Pipeline completion timestamp |
| `evidence_candidates` | `list[EvidenceCandidate]` | Stage 4 output (default: []) |
| `retrieval_trace` | `RetrievalTrace \| None` | Stage 4 trace (default: None) |

**Output boundary:** `TicketOutput` is the default return type. It is never modified by optional stages.

## Optional Draft / Review Types

### Citation

A single evidence reference used in a draft reply.

**Source:** `src/ticketpilot/drafting/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `UUID` | Knowledge chunk identifier |
| `doc_id` | `UUID` | Source document identifier |
| `doc_type` | `DocType` | Document type |
| `source_table` | `str` | Source table name |
| `source_id` | `UUID` | Identifier in source table |
| `evidence_excerpt` | `str` | Text excerpt (max 200 chars) |
| `claim_supported` | `bool` | Whether the claim is backed by this citation |

### DraftReply

Output of the optional draft generation stage.

**Source:** `src/ticketpilot/drafting/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | `str` | Associated ticket ID |
| `draft_text` | `str` | Generated draft reply text |
| `citations` | `list[Citation]` | Citations referenced in the draft |
| `evidence_used` | `list[Citation]` | Evidence actually used in generating the draft |
| `unsupported_claims` | `list[str]` | Claims flagged as unsupported by CitationValidator |
| `missing_information` | `list[str]` | Information gaps noted during generation |
| `confidence` | `float` | Generation confidence (0.0 to 1.0) |
| `must_human_review` | `bool` | True when high-risk, unsupported claims, or no evidence |
| `fallback_reason` | `str \| None` | Reason for fallback: "no_evidence", "generation_error", or None |
| `generation_trace` | `dict \| None` | Optional generation metadata |

### DraftedTicketResult

Wrapper combining `TicketOutput` + `DraftReply`, returned by the optional `run_pipeline_with_draft()` entrypoint.

**Source:** `src/ticketpilot/drafting/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `ticket_output` | `TicketOutput` | The standard pipeline output (unchanged) |
| `draft_reply` | `DraftReply` | The generated draft reply |

### DraftGenerationTrace

Full trace of the draft generation stage for audit and debugging.

**Source:** `src/ticketpilot/drafting/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | `str` | Associated ticket ID |
| `evidence_used` | `list[Citation]` | Citations used in generation |
| `evidence_count` | `int` | Number of evidence items used |
| `total_evidence_available` | `int` | Total evidence candidates at input |
| `confidence_score` | `float` | Generation confidence (0.0 to 1.0) |
| `unsupported_claims` | `list[str]` | Claims flagged as unsupported |
| `human_review_required` | `bool` | Whether human review is required |
| `fallback_reason` | `str \| None` | Reason for fallback if any |
| `created_at` | `datetime` | Generation timestamp |

### ReviewDecision

Record of a human review action. Persisted to JSONL via ReviewStore.

**Source:** `src/ticketpilot/review/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `review_id` | `str` | Unique review identifier (UUID4) |
| `ticket_id` | `str` | Associated ticket ID |
| `ticket_text` | `str` | Snapshot of the normalized ticket text |
| `action` | `ReviewAction` | APPROVE, EDIT, ESCALATE, or REJECT |
| `edited_text` | `str \| None` | Edited draft text (for EDIT action) |
| `decision_reason` | `str` | Reason for escalation or rejection |
| `original_draft_text` | `str` | The original draft as generated |
| `confidence` | `float` | Draft confidence at review time |
| `had_unsupported_claims` | `bool` | Whether the draft had unsupported claims |
| `was_high_risk` | `bool` | Whether the ticket was high risk |
| `intent` | `str` | Intent classification at review time |
| `risk_flags` | `list[str]` | Risk flags at review time |
| `citations_summary` | `list[dict]` | Citation summary (chunk_id, doc_type) |
| `evidence_used_count` | `int` | Number of evidence items used |
| `review_trigger_reasons` | `list[str]` | Why human review was triggered (e.g., "high_risk", "no_evidence") |
| `reviewer_label` | `str` | Free-text reviewer identifier (MVP-only, no auth) |
| `reviewed_at` | `datetime` | Timestamp of review action |

### ReviewStore JSONL Record

Each line in the `reviews.jsonl` file is a JSON-serialized `ReviewDecision` model. The format is append-only — lines are never modified or deleted after writing.

**Example line:**
```json
{
  "review_id": "a1b2c3d4-...",
  "ticket_id": "e5f6g7h8-...",
  "ticket_text": "我要退款，订单号是 12345",
  "action": "approve",
  "edited_text": null,
  "decision_reason": "",
  "original_draft_text": "您好，感谢您的来信...",
  "confidence": 0.85,
  "had_unsupported_claims": false,
  "was_high_risk": false,
  "intent": "refund",
  "risk_flags": ["compensation_risk"],
  "citations_summary": [{"chunk_id": "...", "doc_type": "policy"}],
  "evidence_used_count": 2,
  "review_trigger_reasons": [],
  "reviewer_label": "",
  "reviewed_at": "2026-05-02T12:00:00"
}
```

## Clear Input/Output Boundaries

| Layer | Input Type | Output Type | Persistence |
|-------|-----------|-------------|-------------|
| Pipeline (mandatory) | `RawTicket` | `TicketOutput` | In-memory only |
| Draft (optional) | `TicketOutput` | `DraftReply` | In-memory only |
| Full workflow (optional) | `RawTicket` | `DraftedTicketResult` (`TicketOutput` + `DraftReply`) | In-memory |
| Human review (optional) | `DraftedTicketResult` | `ReviewDecision` | Append-only JSONL via `ReviewStore` |

The `TicketOutput` return type is never modified by optional stages. `DraftedTicketResult` is a narrow wrapper that preserves backward compatibility.
