# Proposal: Connect Retrieval to Intake-Risk Pipeline

## Executive Summary

TicketPilot's intake-risk pipeline currently stops at risk assessment. The hybrid retrieval engine (keyword + vector + RRF fusion) is fully built and verified with 49 integration tests, but it is disconnected from the main workflow. This change wires the verified retrieval engine into the pipeline as Stage 4 (retrieve_evidence), producing an extended `TicketOutput` that includes evidence candidates for downstream human review and reply generation.

## Problem Statement

The current `intake_risk_pipeline()` in `src/ticketpilot/pipeline.py` processes a ticket through three stages and then stops:

1. **Intake**: Normalize text, extract entities
2. **Classification**: Determine intent (8 categories)
3. **Risk assessment**: Evaluate risk flags and severity

After Stage 3, the pipeline returns a `TicketOutput` but does not retrieve any supporting evidence. Meanwhile, `hybrid_retrieval()` in `src/ticketpilot/retrieval/pipeline.py` is fully functional but never called from the main pipeline.

**The gap**: A customer support agent reviewing a ticket sees classification and risk flags, but has no evidence candidates to ground their reply. They must manually search for policy clauses, FAQ articles, or similar case precedents.

## Proposed Solution

Wire the retrieval engine into the pipeline as Stage 4 with a clean connection layer:

1. **Query construction**: Build a retrieval query from normalized ticket text, intent classification, and risk flag business terms
2. **Evidence retrieval**: Call `hybrid_retrieval()` with the constructed query (filterable by `doc_types`)
3. **Result mapping**: Map `FusedResult` objects from `RetrievalTrace` into `EvidenceCandidate` objects with all required fields
4. **Edge case handling**: When no evidence is found, emit the existing `INSUFFICIENT_EVIDENCE` risk flag
5. **Trace preservation**: Include the full `RetrievalTrace` in the pipeline output for audit and debugging

### Architecture

```
RawTicket
  -> Stage 1: intake (normalize)
  -> Stage 2: classify (intent)
  -> Stage 3: assess_risk (flags + severity)
  -> Stage 4: retrieve_evidence (NEW)
     -> build_query(text, intent, risk_flags)
     -> hybrid_retrieval(query)
     -> map_fused_to_evidence(trace.fused_results)
     -> handle_empty_results()
  -> ExtendedTicketOutput (with evidence_candidates + retrieval_trace)
```

### EvidenceCandidate Schema

```
EvidenceCandidate:
  - doc_id: UUID
  - doc_type: DocType (FAQ/POLICY/CASE)
  - source_id: UUID          # from knowledge_chunks.source_id
  - source_table: str         # from knowledge_chunks.source_table
  - chunk_id: UUID
  - content: str
  - score: float              # RRF fusion score
  - rank: int                 # position in fused results (1-based)
```

### Query Construction Strategy

The retrieval query is built by combining:
- **Normalized ticket text** (primary content)
- **Intent-derived business terms** (e.g., REFUND -> "refund, return policy")
- **Risk-flag-derived terms** (e.g., COMPENSATION_RISK -> "compensation, refund amount, settlement")

This produces a richer query than raw ticket text alone, improving retrieval recall.

## Why This Matters for Ticket Triage Workflow

1. **Evidence-grounded review**: Agents see classification, risk flags, AND relevant knowledge chunks in one output
2. **Faster triage**: No manual search for policy clauses or FAQ articles
3. **Risk-aware retrieval**: High-risk tickets can be filtered to retrieve policy/compliance documents
4. **Audit trail**: Every retrieval produces a trace showing exactly how evidence was found and ranked
5. **No-evidence case handling**: Pipeline explicitly flags when no supporting knowledge exists

## Scope

### In Scope

- A `retrieve_evidence` step that builds a retrieval query from normalized ticket text, intent, and risk flags
- Calling `hybrid_retrieval()` from the main pipeline
- Extending `TicketOutput` with `evidence_candidates` and `retrieval_trace` fields
- Mapping `FusedResult` to `EvidenceCandidate` with `source_id`/`source_table` lookup
- Handling "no usable evidence" case by emitting `INSUFFICIENT_EVIDENCE` flag
- Propagating `must_human_review` from risk assessment regardless of retrieval outcome
- Query construction: ticket text + intent class + business terms from risk flags
- Unit tests for the connection layer (query builder, evidence mapper)
- Integration tests using live DB (happy path, no-evidence case, high-risk case)

### Out of Scope

- Reply generation / drafting (separate vertical slice)
- LLM API calls (separate vertical slice)
- Streamlit UI (separate vertical slice)
- LangGraph workflow (separate vertical slice)
- Langfuse / Ragas evaluation (separate vertical slice)
- Real embedding provider (separate vertical slice)
- Reranker (separate vertical slice)
- Auto-send behavior (NOT YET)

## Success Metrics

| Metric | Target |
|--------|--------|
| Pipeline stage count | 4 stages (intake + classify + risk + retrieve) |
| EvidenceCandidate fields | 8 required fields (doc_id, doc_type, source_id, source_table, chunk_id, content, score, rank) |
| RetrievalTrace in output | Present in 100% of pipeline outputs (even empty retrieval) |
| No-evidence handling | INSUFFICIENT_EVIDENCE flag added when fused results are empty |
| must_human_review preservation | Unchanged by retrieval stage (never downgraded) |
| Query construction | Always includes normalized text + intent label + intent-derived terms |
| Unit test coverage | All connection-layer functions tested with mocked retrieval |
| Integration test coverage | Happy path, no-evidence, and high-risk scenarios against live DB |
