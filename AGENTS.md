# TicketPilot — AI Agent Constitution

## 1. Project Identity

TicketPilot is a **local, deterministic, no-LLM, no-auto-send** human review workflow
for customer service ticket triage. It is a **portfolio / demo** project that demonstrates:

- Hybrid retrieval (keyword FTS + pgvector HNSW → RRF fusion)
- Deterministic intent classification and risk assessment
- Evidence-grounded draft generation (no LLM calls)
- Human review console (Streamlit MVP)
- Offline evaluation pipeline (101 synthetic eval tickets)

**It is NOT:**
- A production customer service system
- A replacement for human agents
- An auto-send / auto-reply system
- A generic RAG or chatbot

All knowledge data and eval tickets are synthetic. All embeddings use deterministic
providers (FakeEmbeddingProvider by default; real provider opt-in via `.env.local`).

## 2. Non-Negotiable Boundaries

| Rule | Enforcement |
|---|---|
| No auto-send | Architectural invariant — pipeline never sends replies automatically |
| No LLM calls in pipeline | Classification, risk, retrieval, drafting are all deterministic |
| No real customer data | All seed data and eval tickets are synthetic |
| No API keys in repo | `.env` and `.env.local` are gitignored; `.env.example` has placeholders |
| No `|| true` in quality gate | Every failure must be visible |
| No coverage threshold lowering | Minimum 70% coverage, enforced |
| No `# noqa` without justification | Only allowed for specific false positives |
| No Phase 7/8/9 baseline report modification | Baseline reports are immutable |
| No `openspec/` archived change modification | Archived changes are read-only |
| Integration skipped must = 0 for archive/push | DB-dependent tests must pass or be properly skipped |

## 3. Tech Stack

- **Runtime**: Python 3.11+, Windows WSL2 / native Linux / macOS
- **Package**: `uv` (not pip), `pyproject.toml` as single source of truth
- **Database**: PostgreSQL 16 + pgvector 0.8+ (Docker Compose)
- **Embedding**: FakeEmbeddingProvider (default, deterministic), openai_compatible (opt-in)
- **Testing**: pytest 9.x, pytest-cov 7.x
- **Linting**: ruff (all rules, no isort)
- **CI**: Full quality gate script at `scripts/run_quality_gate.sh`
- **Spec**: OpenSpec (`openspec validate` / `openspec archive`)

## 4. Development Environment

```bash
# Start database (required for integration tests)
docker compose up -d

# Install dependencies
uv sync

# Activate venv
source .venv/bin/activate  # Linux/WSL
.venv\Scripts\activate     # Windows

# Run seed data
uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"
```

**Windows WSL note**: Project runs from `\\wsl.localhost\Ubuntu\...` paths.
psycopg DLLs are copied to `C:\Users\<user>\AppData\Local\Temp\ticketpilot_dlls`
at import time by `connection.py` and `conftest.py` to work around WSL UNC path
limitations with native DLL loading.

## 5. Validation Levels

| Scope | OpenSpec | Tests | Quality Gate |
|---|---|---|---|
| Docs/portfolio only | Not required | Not required | Not required |
| Single OpenSpec change | `--strict` scoped | Module-level | Not required |
| Core pipeline / DB / data | `--all` | Full | Required (0 skip) |
| Pre-push / archive / phase close | `--all` | Full | Required (0 skip) |

See `docs/technical/validation_policy.md` for full details.

## 6. Secret Rules

- **No API keys** in source code, tests, or commit messages
- `.env.local` is gitignored — used for local embedding provider config
- `.env.example` has placeholder values only — never real secrets
- Secret scan runs in quality gate (detects `sk-` OpenAI-style keys)
- If a secret is committed, rotate it immediately and rewrite git history

## 7. OpenSpec Workflow

```
1. Create OpenSpec change:  proposal.md + design.md + tasks.md + specs/
2. Validate scoped:         openspec validate <change-id> --strict
3. Implement in batches:    follow tasks.md phase order
4. Run validation per batch: module tests → scoped openspec → quality gate (if core)
5. Archive on completion:   openspec archive <change-id>
6. Post-archive verify:     openspec validate --all
```

- Each change has its own directory under `openspec/changes/<change-id>/`
- Archived changes go to `openspec/changes/archive/<date>-<change-id>/`
- Specs promoted to `openspec/specs/<name>/spec.md` on archive
- Changing archived specs is forbidden — create a new OpenSpec change instead

## 8. Quality Gate Rules

```bash
# Full quality gate (7+ minutes)
bash scripts/run_quality_gate.sh

# Skip integration tests (no DB available)
TICKETPILOT_SKIP_DB_TESTS=1 bash scripts/run_quality_gate.sh
```

The gate checks, in order:
1. **Ruff** — all lint rules pass
2. **Unit tests** — all pass, coverage ≥ 70%
3. **Integration tests** — all pass, 0 skipped (unless `TICKETPILOT_SKIP_DB_TESTS=1`)
4. **OpenSpec validation** — `--all` passes
5. **Secret scan** — no OpenAI-style keys
6. **Quality gate PASSED** — all checks green

If any check fails, the gate exits non-zero. No `|| true` bypass.

## 9. Phase Artifact Rules

| Artifact type | Location | Example |
|---|---|---|
| Knowledge data | `data/knowledge/` | `faq_seed.json`, `policy_seed.json`, `case_seed.json` |
| Evaluation data | `data/eval/` | `tickets_eval.csv`, `golden_expectations.csv` |
| Reports | `reports/retrieval/` | `phase9_evaluation_rerun.md`, `phase10_trace_data_audit.md` |
| Reports (evaluation) | `reports/eval/` | `evaluation_report.json` |
| Technical docs | `docs/technical/` | `retrieval_architecture.md`, `validation_policy.md` |
| Portfolio docs | `docs/portfolio/` | Phase 8/9/10 snapshot docs |
| Development trace | `docs/development_trace/` | Stage-by-stage narrative |
| Prompt templates | `prompts/harness/` | Reusable batch prompts |

- Phase 7/8/9 baseline reports are immutable
- New phases write to namespaced paths (`phase10_*`, `phase11_*`, etc.)
- Portfolio docs are summary-facing — never overwrite prior phase portfolios

## 10. Portfolio Boundary Wording

All portfolio-facing documents, demo scripts, and README files must include
explicit boundary statements:

- **Fake embeddings**: "Pipeline verification only — no semantic retrieval quality"
- **Seed data**: "All knowledge and eval data are synthetic — not real enterprise data"
- **No auto-send**: "TicketPilot never sends customer replies automatically"
- **Human review**: "High-risk, unsupported, and no-evidence outputs require human review"
- **Evaluation**: "Offline evaluation on 101 synthetic tickets — not a production benchmark"
- **Phase findings**: "Diagnosis-oriented, not production-optimized"

See `docs/technical/validation_policy.md` for the full validation level matrix.
See `docs/technical/ai_development_harness.md` for the full harness design.
