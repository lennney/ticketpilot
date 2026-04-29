# Technical Decisions

## Core Stack

- Backend: FastAPI (planned, no server code implemented)
- Workflow: LangGraph (planned, no workflow code implemented)
- Database: PostgreSQL
- Vector search: pgvector
- Keyword search: PostgreSQL full-text search
- Fusion: RRF
- Structured output: Pydantic
- Review UI: Streamlit for MVP (planned, no UI implemented)
- Dependency management: uv
- Runtime environment: WSL Ubuntu
- Deployment: Docker Compose

## Development Rules

- Use spec-driven development for non-trivial changes.
- Do not hardcode secrets.
- Keep prompts centralized with prompt_version.
- Use Pydantic schemas for critical outputs.
- Update docs/changelog.md after meaningful changes.

## Retrieval Architecture (Stage 1B Batch 2 — Implemented)

These values reflect the current implementation in `src/ticketpilot/retrieval/`.
If code values differ from this document, the code is authoritative.

### Vector Search (pgvector HNSW)

| Parameter | Value |
|-----------|-------|
| Index type | HNSW |
| m | 16 |
| ef_construction | 200 |
| ef_search | 100 |
| Distance operator | `<=>` (cosine distance) |
| Score formula | `1 - (embedding <=> query_vector)` |

### Fake Embedding Provider

| Parameter | Value |
|-----------|-------|
| Dimension | 384 |
| Seed mechanism | SHA-256 hash of text → first 8 hex chars → random seed |
| Value range | [-1, 1] |
| Status | PIPELINE VERIFICATION ONLY — no semantic meaning |

Note: Real embedding provider (small 384-d, quality 768-d) is planned but not implemented.

### Keyword Search

| Parameter | Value |
|-----------|-------|
| FTS config | `simple` (not `chinese`) |
| Index | GIN on `to_tsvector('simple', content)` |
| Fallback | LIKE on 8 Chinese business terms when FTS returns no results |

### RRF Fusion

| Parameter | Value |
|-----------|-------|
| k | 60 |
| Per-ranker contributions | Tracked in trace |

### Knowledge Base Design (Pending Resolution)

The FAQ/Policy/Case physical separation design is under review (BLOCK-2 audit finding).
Current implementation: single `knowledge_chunks` table with `doc_type` discriminator.
Proposed design: 3 source tables (`knowledge_faq`, `knowledge_policy`, `knowledge_case`) + 1 unified `knowledge_chunks` table with `source_table`/`source_id` references.
See `openspec/changes/close-project-audit-blockers/design.md` for the current decision.

### SourceRouter

Documented in earlier design drafts but NOT implemented. Intent-to-source routing will be added
as part of the `connect-retrieval-to-intake-risk-pipeline` change (deferred, not in current scope).

## Embedding Model Tiers (Planned, Not Implemented)

| Tier | Dimension | Status |
|------|-----------|--------|
| Fake (testing) | 384 | Implemented |
| Small (real) | 384 | Planned |
| Quality (real) | 768 | Planned |

## Unimplemented Components

The following are in pyproject.toml dependencies but have zero code:
- FastAPI, Uvicorn — web server (planned)
- LangGraph — workflow orchestration (planned)
- Streamlit — review UI (planned)
- Alembic, SQLAlchemy — ORM/migration framework (planned)
- HTTPx — HTTP client (planned)
- Pydantic-settings — config management (planned)
