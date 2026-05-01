# Proposal: Add Layered Knowledge Retrieval Foundation

## Executive Summary

TicketPilot requires a retrieval foundation that can find relevant knowledge to ground reply generation. This change builds a layered knowledge architecture (FAQ / Policy / Case) with hybrid retrieval combining PostgreSQL full-text keyword search and pgvector HNSW vector search, fused using Reciprocal Rank Fusion (RRF). The retrieval system produces traceable evidence for human review.

## Problem Statement

TicketPilot cannot generate evidence-grounded replies without reliable knowledge retrieval. Current gaps:

1. **No layered knowledge separation**: FAQ, policy, and case knowledge are mixed, reducing retrieval precision
2. **No hybrid retrieval**: Vector-only search misses exact keyword matches (e.g., policy clause numbers)
3. **No parent-child chunking**: Small chunks lack sufficient context; large chunks dilute relevance
4. **No retrieval traces**: Cannot debug why certain results were returned or how they were ranked

## Proposed Solution

### Layered Knowledge Architecture

Three physically separated knowledge sources:
- **FAQ**: Frequently asked questions for intent routing and common issue resolution
- **Policy**: Rules, terms, compensation guidelines, escalation procedures
- **Case**: Historical ticket summaries with outcomes for precedent matching

### Parent-Child Chunking

Each document is chunked hierarchically:
- **Parent chunks** (level=1): Full context, 500-1000 tokens
- **Child chunks** (level=2): Specific passages, 100-300 tokens

Child chunks reference parent via `parent_chunk_id` for context retrieval.

### Hybrid Retrieval

Combine keyword and vector retrieval:
- **Keyword retrieval**: PostgreSQL full-text search with `to_tsvector` / `to_tsquery`
- **Vector retrieval**: pgvector with HNSW index for approximate nearest neighbor search
- **Fusion**: RRF with k=60 to combine rank-based scores

### Retrieval Traces

Every retrieval query produces a trace containing:
- Original query
- Keyword results with scores
- Vector results with scores
- Fused results with RRF scores
- Final evidence list with source attribution

## Why This Matters for Ticket Triage Workflow

1. **FAQ lookup** for intent routing: "How do I return an item?" returns FAQ articles
2. **Policy lookup** for compliance: "Can I get a refund after 30 days?" returns policy sections
3. **Case lookup** for precedent: Similar tickets and their resolutions
4. **Hybrid for accuracy**: Keyword matches (e.g., policy clause "7.3.2") combined with semantic similarity

## Scope

### In Scope

- FAQ / Policy / Case schema and physical separation
- Parent-child chunking with `parent_chunk_id` linkage
- PostgreSQL full-text keyword retrieval
- pgvector HNSW vector retrieval
- RRF fusion (k=60)
- Retrieval trace structure
- Seed data: 10+ FAQ, 10+ Policy, 10+ Case documents
- 6 retrieval golden cases for smoke testing

### Out of Scope

- Reply generation (handled in later vertical slice)
- Reranker integration (placeholder only)
- Langfuse or Ragas integration (placeholder only)
- Streamlit review UI (handled in later vertical slice)
- Embedding fine-tuning (NOT YET)
- BM25 scoring (PostgreSQL full-text is sufficient for MVP)

## Success Metrics

| Metric | Target |
|--------|--------|
| Knowledge source separation | 3 distinct tables (FAQ, Policy, Case) |
| Parent-child linkage | 100% of child chunks have valid parent_chunk_id |
| Keyword retrieval latency | < 50ms for top-10 results |
| Vector retrieval latency | < 100ms for top-10 results with HNSW |
| RRF fusion | Produces combined ranking from both retrieval modes |
| Retrieval trace completeness | 100% of queries produce trace with all required fields |
| Seed data volume | 10+ FAQ, 10+ Policy, 10+ Case documents |
| Golden case coverage | 6 scenarios: FAQ lookup, Policy lookup, Case lookup, Hybrid, Parent-child, Multi-source fusion |
