# Proposal: Add Evidence Draft Generation

## Executive Summary

TicketPilot currently processes a raw Chinese ticket through intake normalization, intent classification, risk assessment, and evidence retrieval, producing a `TicketOutput` with evidence candidates but no actionable reply draft. A customer service agent reviewing the output must manually read each evidence chunk and compose a response from scratch. This change adds a fifth pipeline stage -- draft generation -- that produces an evidence-grounded customer service reply draft in Chinese, with every substantive claim explicitly linked to its supporting evidence chunk.

The draft generation stage receives the `TicketOutput` (including `evidence_candidates`, `retrieval_trace`, `classification`, and `risk_assessment`) and produces a `DraftReply` containing the reply text, a list of `EvidenceCitation` objects mapping each claim to its source, and metadata about the generation. The MVP uses a deterministic fake draft provider -- no LLM API calls by default -- that constructs replies from evidence content using template-based composition. This ensures predictable, testable output without external dependencies while preserving the architecture for a future real provider swap.

High-risk tickets (flagged by the risk assessor) still receive a draft (the agent may find it useful as a starting point), but the draft is flagged with `human_review_required=True` and is preview-only — never auto-sendable. Tickets with insufficient evidence produce a draft that explicitly states no policy promise can be made, rather than fabricating an answer. All drafts are human-review only; the system never auto-sends a reply. This change completes the core TicketPilot workflow: raw ticket in, actionable evidence-grounded draft out.

## Problem Statement

Without draft generation, the TicketPilot workflow has four gaps that prevent it from being a true Copilot:

1. **No actionable output for agents**: After retrieval, the agent sees a list of evidence chunks but must manually read, synthesize, and compose a reply. This negates the efficiency gain of automated triage -- the agent still spends time drafting from scratch.

2. **No structured evidence-to-claim traceability**: When an agent writes a reply, there is no machine-readable record of which evidence supported which claim. This makes audit, review, and quality checks manual and unreliable.

3. **No automated high-risk guard at the reply stage**: The risk assessor flags a ticket as `must_human_review`, but nothing in the pipeline enforces that high-risk tickets skip automated drafting. An agent could mistakenly use an AI-suggested reply for a legally sensitive ticket.

4. **No "no-evidence" communication protocol**: When `INSUFFICIENT_EVIDENCE` is raised, the pipeline has no standardized way to communicate to the agent that a reply must avoid making policy promises. Each agent handles this case inconsistently, creating compliance risk.

## Proposed Solution

Add a fifth stage to the processing pipeline -- `generate_draft` -- placed after `retrieve_evidence`. The stage is called only when the risk assessment does not require pure human review; otherwise the draft field is left empty and the `must_human_review` flag is honored.

### Stage 5: Evidence Draft Generation

```
TicketOutput (from pipeline)
  -> Call generate_draft(ticket_output)
  -> FakeDraftProvider generates evidence-grounded draft
  -> CitationValidator checks for unsupported claims
  -> Return DraftReply with citations and flags
```

### DraftReply Schema

A new Pydantic model `DraftReply` is added to the schema layer:

```
DraftReply:
  - reply_text: str                      # Generated reply in Chinese
  - evidence_citations: list[EvidenceCitation]
  - draft_provider: str                  # "fake" for MVP
  - generated_at: datetime
```

### EvidenceCitation Schema

A new Pydantic model `EvidenceCitation` linking each substantive claim to its evidence:

```
EvidenceCitation:
  - claim: str                           # The specific claim made in the reply
  - chunk_id: UUID                       # FK to the evidence chunk
  - doc_id: UUID
  - doc_type: DocType
  - content_snippet: str                 # The portion of evidence supporting this claim
```

### DraftProvider Interface

An abstract `DraftProvider` base class with a single method `generate(ticket: TicketOutput) -> DraftReply`. The MVP ships with exactly one implementation:

- **FakeDraftProvider**: Deterministic, zero-LLM provider. Constructs replies by concatenating the top-N evidence candidate titles and content snippets into a templated Chinese reply. Each evidence citation maps to its source chunk. Always returns output within 1 ms. Used for development, CI, and testing.

Future implementors (out of scope for this change) would swap in a real LLM provider by implementing the same interface.

### Evidence Grounding Rules

The draft generator enforces three grounding rules at the architectural level:

1. **Every substantive claim must cite evidence**: The `evidence_citations` field must contain at least one entry for each factual claim in `reply_text`. The fake provider satisfies this by construction (claims are derived from evidence). A real provider would need a post-generation grounding validation step.

2. **No evidence means no policy promise**: When `evidence_candidates` is empty, the draft must state that no policy commitment can be made based on available information (e.g., "根据现有知识库信息，无法确定相关政策的适用情况，建议转交人工客服处理"). This is enforced in the `FakeDraftProvider` as a hardcoded path.

3. **High-risk must skip automated drafting**: When `must_human_review` is `True` (whether from the risk assessor or from zero-evidence escalation), the pipeline skips draft generation entirely and leaves `DraftReply` as `None`. No automated reply is produced for high-risk tickets.

### Pipeline Integration

The `intake_risk_pipeline()` function in `pipeline.py` is extended with a conditional Stage 5 call. The `TicketOutput` model is NOT modified. Instead, a standalone `generate_draft(ticket_output: TicketOutput) -> DraftReply` function is provided. Callers compose it after the pipeline: `output = intake_risk_pipeline(raw_ticket); draft = generate_draft(output)`. The draft reply is always available (for low-risk tickets with evidence) or a safe fallback message (for high-risk or no-evidence tickets).

## Why This Matters

1. **Workflow completion**: The pipeline now produces an actionable Chinese reply draft from raw ticket input, closing the loop from triage to suggested response. This is the defining feature of an evidence-grounded reply Copilot rather than a classification dashboard.

2. **Evidence traceability through to the reply**: Every claim in the generated draft is linked to its source evidence chunk via `EvidenceCitation`. This enables human reviewers to verify any claim by inspecting its cited evidence, supporting the core principle of evidence-grounded customer service.

3. **Risk-aware generation**: The pipeline enforces that high-risk tickets never receive an automated draft, preserving human judgment for sensitive cases. This is a safety by design choice, not an afterthought.

4. **Clean architecture for future LLM integration**: The `DraftProvider` interface allows the fake provider to be replaced with a real LLM provider (e.g., via OpenAI-compatible API) without changing any pipeline code. The evidence grounding rules are enforced in the provider contract, not in ad-hoc post-processing.

5. **Testability and determinism**: The fake provider produces identical output for identical input, enabling reliable unit tests and deterministic CI behavior without network dependencies or API costs.

## Scope

### In Scope

- `DraftReply` and `EvidenceCitation` Pydantic schemas in `src/ticketpilot/schema/`
- `DraftProvider` abstract interface (base class) in a new `src/ticketpilot/draft/` module
- `FakeDraftProvider` implementation: deterministic, template-based Chinese reply generation from evidence candidates
- Evidence grounding rules: citations required, no-evidence protocol, high-risk skip
- Conditional Stage 5 integration into `intake_risk_pipeline()` in `pipeline.py`
- Optional `draft_reply` field on `TicketOutput`
- Unit tests for:
  - `FakeDraftProvider` normal generation path with evidence
  - `FakeDraftProvider` no-evidence path
  - `DraftReply` and `EvidenceCitation` schema validation
  - Pipeline integration: draft generated when conditions are met
  - Pipeline integration: draft skipped when `must_human_review` is True
  - Pipeline integration: draft skipped when evidence list is empty
  - No-regression: existing pipeline behavior unchanged when `draft_reply` is `None`
- Pipeline smoke test with evidence-rich ticket producing a valid `DraftReply`
- Documentation and changelog update

### Out of Scope

- Real LLM provider by default (MVP uses fake/deterministic provider only)
- LangGraph workflow orchestration
- Streamlit review UI
- Langfuse observability integration
- Ragas evaluation metrics
- Evaluation pipeline (held for separate change with golden-answer test set)
- Frontend of any kind
- Auto-send or one-click send behavior (all drafts are human-review only)
- Retrieval engine changes (no modifications to `retrieval/` pipeline, schema, or providers)
- `source_id` DB lookup for multi-chunk documents (maintains seed-only doc_id == source_id assumption)
- Persistent `retrieval_traces` DB table
- `map_intent_to_doc_types` configuration
- `enable_retrieval` feature flag
- Post-generation grounding validation for non-fake providers (out of scope until a real LLM provider is added)
- Reranker integration
- Embedding fine-tuning
