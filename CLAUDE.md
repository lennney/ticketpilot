# TicketPilot — AI Customer Service Copilot

Cross-border e-commerce AI customer service with hybrid retrieval, deterministic pipeline, confidence scoring, and tiered degradation.

## Architecture

```
RawTicket → Intake → Classification → Risk → Retrieval → Draft → PostProcess
                                                                    ↓
                                                          ConfidenceScorer (4D)
                                                                    ↓
                                                          DegradationRouter (4-tier)
                                                                    ↓
                                                    AUTO_SEND / HUMAN_REVIEW / ESCALATE
```

**Key principle**: Pipeline is deterministic (no LLM calls in pipeline). LLM is only used in draft generation (optional). All scoring/routing is rule-based.

## Tech Stack

- **Python 3.11+** with `uv` package manager
- **PostgreSQL 16 + pgvector 0.8+** (Docker Compose)
- **Pydantic v2** for all schemas (never use @dataclass)
- **FastAPI** for API, **Streamlit** for review console
- **pytest** for testing (coverage ≥ 70%)
- **ruff** for linting

## Key Commands

```bash
# Setup
docker compose up -d              # Start PostgreSQL + pgvector
uv sync                           # Install dependencies
source .venv/bin/activate         # Activate venv

# Run
uv run uvicorn ticketpilot.api:app --port 8000   # API server
uv run streamlit run ticketpilot/review/console.py  # Review console

# Test
uv run pytest tests/unit/ -v                                    # Unit tests
uv run pytest tests/ -v --cov=src/ticketpilot --cov-fail-under=70  # With coverage
TICKETPILOT_LLM_PROVIDER=fake uv run pytest tests/ -v           # All tests (fake LLM)
bash scripts/run_quality_gate.sh                                 # Full quality gate

# Lint
uv run ruff check src tests       # Lint
uv run ruff format src tests      # Format
```

## Project Structure

```
src/ticketpilot/
├── pipeline.py              # Core pipeline (intake_risk_pipeline, post_process)
├── schema/                  # Shared Pydantic models (TicketOutput, RawTicket, etc.)
├── intake/                  # Text normalization, entity extraction
├── classification/          # Intent classification (rule-based)
├── risk/                    # Risk assessment (rule-based)
├── retrieval/               # Hybrid retrieval (FTS + pgvector + RRF)
│   ├── traces.py            # Retrieval trace schema (KeywordResult, VectorResult, FusedResult)
│   └── schema/knowledge.py  # DocType enum, knowledge chunk schema
├── drafting/                # LLM draft generation + citation validation
│   ├── schemas.py           # DraftReply, Citation, DraftedTicketResult
│   ├── generate.py          # generate_draft()
│   └── citation_validator.py
├── confidence/              # Multi-dimensional confidence scoring
│   └── scorer.py            # ConfidenceScorer (retrieval 35% + classify 25% + citation 25% + evidence 15%)
├── degradation/             # Tiered degradation routing
│   └── router.py            # DegradationRouter (AUTO_SEND / CAUTIOUS / HUMAN_REVIEW / ESCALATION)
├── tracing/                 # Full-chain provenance + agent trace
│   ├── provenance.py        # ClaimProvenance, ResponseProvenance
│   └── store.py             # ProvenanceStore (in-memory)
├── guardrails/              # PII detection, hallucination detection
├── agent/                   # Agent kernel (loop, planner, registry, tools, memory)
│   ├── loop.py              # run_agent_pipeline() — 5-step deterministic agent
│   ├── state_store.py       # SQLite-backed AgentRun persistence (pause/resume)
│   ├── tools.py             # Tool wrappers (normalize, classify, risk, evidence, draft, human_input)
│   ├── error_compaction.py  # Error → compact summary for context injection
│   └── schemas.py           # AgentRun, AgentPlan, AgentStep, AgentEvent
├── prompts/                 # Version-managed prompt templates
│   └── manager.py           # PromptManager (register, get, render, list_versions)
├── review/                  # Human review console (Streamlit)
│   ├── console.py           # Main UI with confidence/degradation display
│   └── schemas.py           # ReviewDecision, ReviewAction
├── evaluation/              # RAGAS-style evaluation framework
│   └── agent_eval.py        # EvalCase, EvalResult, EvalReport
└── api/                     # FastAPI endpoints
    └── streaming.py         # SSE streaming chat
```

## Coding Standards

- **All schemas**: Pydantic BaseModel (never @dataclass)
- **UUID fields**: Use `uuid.UUID` type (not `str`) for chunk_id, doc_id
- **Imports**: Use `TYPE_CHECKING` to avoid circular imports
- **Tests**: Write test first (TDD), then implement
- **Module pattern**: Each module has `__init__.py` + main file + test file
- **Error handling**: Use `compact_error()` from `agent/error_compaction.py`
- **No LLM in pipeline**: Classification, risk, retrieval, routing are all deterministic

## 12-Factor Alignment

| Factor | Status | Implementation |
|--------|--------|----------------|
| ① NL→Tool Calls | ✅ | planner.py keyword→AgentPlan→tools |
| ② Own Prompts | ✅ | prompts/manager.py (version-managed) |
| ③ Context Window | ⚠️ | retrieval context not yet truncated |
| ④ Tools=Struct Output | ✅ | All tools return Pydantic dict |
| ⑤ Unify State | ✅ | WorkingMemory stores each step |
| ⑥ Pause/Resume | ✅ | agent/state_store.py (SQLite) |
| ⑦ Human as Tool | ✅ | request_human_input_tool |
| ⑧ Own Control Flow | ✅ | agent/loop.py explicit flow |
| ⑨ Compact Errors | ✅ | agent/error_compaction.py |
| ⑩ Small Agents | ✅ | Modular: intake/classify/risk/retrieval/draft |
| ⑪ Trigger Anywhere | ⚠️ | Only HTTP API + Streamlit |
| ⑫ Stateless Reducer | ✅ | pipeline idempotency tests |

## Confidence → Strategy Mapping

| Confidence | Level | Strategy | Behavior |
|------------|-------|----------|----------|
| > 0.8 | HIGH | AUTO_SEND | Auto-send, background audit |
| 0.6–0.8 | MEDIUM | AUTO_SEND_CAUTIOUS | Auto-send + disclaimer |
| 0.4–0.6 | LOW | HUMAN_REVIEW | Human review before send |
| < 0.4 | CRITICAL | HUMAN_ESCALATION | Escalate to human, no draft |

## Gotchas

- `FakeEmbeddingProvider` is the default (deterministic). Real embeddings via `.env.local`.
- Integration tests need Docker DB: `docker compose up -d`
- Skip DB tests: `TICKETPILOT_SKIP_DB_TESTS=1`
- LLM tests use fake provider: `TICKETPILOT_LLM_PROVIDER=fake`
- Windows WSL note: psycopg DLLs copied to temp dir for UNC path compatibility
