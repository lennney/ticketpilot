# Stage 0: Project Origin

## Stage Goal

Initialize the TicketPilot project structure, establish the spec-driven development workflow, and prepare the development toolchain (Python, PostgreSQL, pgvector, Docker Compose, quality gate).

## Business Problem Addressed

No project existed. Before any feature code could be written, the project needed:
- A reproducible Python environment with `uv` and `pyproject.toml`
- A local PostgreSQL + pgvector database via Docker Compose for vector retrieval
- A quality gate script to enforce code quality, test coverage, and spec compliance
- An OpenSpec-driven change management process with design docs, specs, tasks, and archive workflow
- Claude Code agent configurations for supervised, spec-driven development

## Key Design Decisions

### 1. uv-based Python project setup
- **Decision**: Use `uv` for dependency management (not pip, poetry, or pipenv).
- **Rationale**: Fast, deterministic resolution; native `pyproject.toml` support; lockfile generation.
- **Alternatives**: pip (slow, no lockfile), poetry (heavier, slower resolution).

### 2. Docker Compose for PostgreSQL + pgvector
- **Decision**: Single `docker-compose.yml` with PostgreSQL 16 + pgvector.
- **Rationale**: Reproducible local development; mirrors production-adjacent infrastructure without cloud dependency.
- **Volume path note**: Initially set to `./db/seed` — corrected to `./db/migrations` in audit remediation (Stage 04).

### 3. OpenSpec spec-driven development
- **Decision**: Every non-trivial change follows: proposal -> design -> spec -> tasks -> implementation -> quality gate -> archive.
- **Rationale**: Prevents uncontrolled code generation and requirement drift; provides full traceability.

### 4. Quality gate script
- **Decision**: Single `bash scripts/run_quality_gate.sh` that runs ruff, pytest, openspec validate, and secret detection.
- **Initial limitation**: Used `|| true` on every check, making it impossible to detect failures (fixed in Stage 04).

## Implementation Scope

- Created `src/ticketpilot/` package structure with `src/ticketpilot/__init__.py`
- Created `pyproject.toml` with dependencies: FastAPI, LangGraph, psycopg, pgvector, Pydantic, Streamlit, etc.
- Created `docker-compose.yml` with PostgreSQL 16 + pgvector service
- Created `.env.example` for environment configuration (no secrets)
- Created `scripts/run_quality_gate.sh` (initial version with `|| true`)
- Created `scripts/run_checks.sh` for pre-commit validation
- Created `.claude/` agent configurations for supervised development
- Created initial project documentation (`docs/architecture.md`, `docs/ai_development_workflow.md`)
- Created `docs/evaluation_plan.md` with 5-layer evaluation taxonomy
- Added `.gitkeep` files for empty directories, `db/migrations/`, `data/knowledge/`
- Created `.gitignore` for Python, Docker, IDE artifacts

## Forbidden Scope

- No product code (no pipeline, no retrieval, no UI)
- No database schema migrations yet
- No evaluation scripts (only a plan document)
- No real API integrations

## Tests and Quality Gate Result

- No product code yet — quality gate passes by default (no real checks).
- Quality gate script exists but uses `|| true` on every check, making it a no-op gate.

## Major Risks

| Risk | Handling |
|------|----------|
| `|| true` in quality gate makes it impossible to detect failures | Identified in the initial design; fixed in Stage 04 audit remediation |
| Many dependencies declared but unused | Accepted for MVP; no code yet uses FastAPI, LangGraph, Streamlit, etc. |
| OpenSpec workflow has overhead for small changes | Accepted by design; lightweight changes can use direct commits |

## Deferred Items

- Working quality gate (see Stage 04)
- Any product feature (intake, classification, risk, retrieval, UI)
- Evaluation scripts
- Docker production configuration

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `91f388f` | 2026-04-29 | chore: initialize TicketPilot development workflow |
| `0c52f5e` | 2026-04-29 | chore: add dev dependencies, .gitkeep dirs, fix quality gate secret pattern |
| `089c5ba` | 2026-04-29 | chore: update local development ignores |
| `ecd1de6` | 2026-04-29 | spec: add ticket intake risk triage change |
| `ee513a2` | 2026-04-29 | spec: add layered knowledge retrieval foundation |
| `dbec010` | 2026-04-29 | chore: add AI-assisted development supervision workflow |
| `69de63e` | 2026-04-29 | chore: add project audit agent and skill |
| `09bd8ea` | 2026-04-29 | audit: project plan audit 2026-04-29 — HOLD_NEW_FEATURES |

## Reusable Patterns

1. **OpenSpec change workflow** — The proposal/design/spec/tasks/archive pattern is reusable for any spec-driven project. Each change is self-contained with design rationale, task breakdown, and acceptance criteria.
2. **Docker Compose + pgvector setup** — Reproducible local PostgreSQL with vector extension, immediately usable for any RAG project.
3. **Gitignore patterns** — Python, Docker, IDE, and WSL-specific patterns applicable to any Python project on WSL.
4. **Quality gate template** — The script structure (ruff -> unit tests -> integration tests -> openspec validation -> secret detection) is reusable, though the initial implementation needed fixes.
