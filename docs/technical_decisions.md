# Technical Decisions

## Core Stack

- Backend: FastAPI
- Workflow: LangGraph
- Database: PostgreSQL
- Vector search: pgvector
- Keyword search: PostgreSQL full-text search / BM25-compatible minimal implementation
- Fusion: RRF
- Structured output: Pydantic
- Review UI: Streamlit for MVP
- Dependency management: uv
- Runtime environment: WSL Ubuntu
- Deployment: Docker Compose

## Development Rules

- Use spec-driven development for non-trivial changes.
- Do not hardcode secrets.
- Keep prompts centralized with prompt_version.
- Use Pydantic schemas for critical outputs.
- Update docs/changelog.md after meaningful changes.
