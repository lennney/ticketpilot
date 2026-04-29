# TicketPilot

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot.

It is not a generic chatbot or a simple document QA demo. The system is designed around a customer support workflow:

> **Note**: This is the target workflow. Not all stages are implemented yet. See [Current Status](#current-status) below.

Ticket input
→ normalization
→ intent classification
→ risk assessment
→ rule gate
→ FAQ / Policy / Case retrieval
→ hybrid recall
→ RRF fusion
→ rerank
→ evidence-grounded draft reply
→ human review
→ finalization
→ trace and evaluation

## Current Status

### Implemented

| Stage | Status | Notes |
|-------|--------|-------|
| Stage 1A: Intake + Risk Triage | **ACCEPTED** | Normalization, entity extraction, 8-class classification, risk gate (8 flags + severity). 69 unit tests pass. |
| Stage 1B Batch 1: Knowledge Schema + Chunking | **ACCEPTED** | DocType/ChunkLevel/BusinessDomain enums, FAQ/Policy/Case Pydantic models, KnowledgeChunk schema, parent-child chunker, seed data (36 documents). |
| Stage 1B Batch 2: Hybrid Retrieval | **ACCEPTED_WITH_DB_GAP** | Keyword search (FTS + LIKE), vector search (HNSW), RRF fusion (k=60), retrieval traces, fake embedding provider (384-d). Unit tests pass. Integration tests (26) require PostgreSQL + pgvector — not yet verified against real DB. |

### Implemented but Not Verified

- **PostgreSQL + pgvector integration**: DB migrations exist, seeding code exists, Docker Compose configured. 26 integration tests are conditionally skipped pending a live pgvector instance.
- **Fake embedding**: A deterministic 384-dimensional fake embedding provider is in place. It verifies pipeline mechanics (wiring, RRF, trace capture) but does NOT provide semantic retrieval quality. Real embeddings will replace this in a future phase.

### Planned (Not Started)

- Stage 2: Evidence-grounded draft reply
- Stage 3: Human review routing + Streamlit review UI
- Stage 4: LangGraph full workflow
- Stage 5: Trace persistence and evaluation (Langfuse, Ragas)
- Real embedding provider
- Reranker

For detailed phase tracking, see [docs/phase_status.md](docs/phase_status.md).

## Limitations

- **Chinese-only keyword recognition**: Classification and risk rules are trained on Chinese keywords. English tickets will classify as `OTHER`.
- **Fake embeddings**: Vector search uses deterministic fake embeddings. Cosine similarity scores between fake embeddings have no semantic meaning — they verify pipeline wiring, not retrieval quality.
- **No DB verification**: The retrieval pipeline has never been run end-to-end against a real PostgreSQL + pgvector database.
- **No web server**: FastAPI is in dependencies but zero server code exists.
- **No LangGraph workflow**: LangGraph is planned but zero workflow code exists.

## MVP Stack

- FastAPI (planned)
- LangGraph (planned)
- PostgreSQL + pgvector
- PostgreSQL full-text search
- RRF
- Pydantic
- Streamlit review UI (planned)
- Docker Compose
- uv

## Development

This project uses spec-driven and AI-assisted development.

Development rules:
- Use OpenSpec for non-trivial changes.
- Use project-level Claude agents and skills for planning, implementation, review, and evaluation.
- Do not commit secrets.
- Update docs/changelog.md after meaningful changes.
