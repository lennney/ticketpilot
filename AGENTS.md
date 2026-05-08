# TicketPilot — AI Agent Constitution

> **Bootstrap**: This file is loaded by `.claude/CLAUDE.md`. On new clones, see `.claude/CLAUDE.md` for harness overview. For phase execution workflow, see `docs/harness/PHASE_LOOP.md`.


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
| ChatGPT controller context | `docs/harness/` | Session handoff, decisions, next actions |

## 11. Controller Autonomy Rules

### Default: Act First, Ask Only When Blocked

As Controller, default to **acting autonomously**. Only interrupt the human when:
- You are genuinely blocked (cannot determine next step)
- A non-negotiable rule is at risk of violation
- The human explicitly requests a confirmation

### Decisions I Can Make Without Asking

| Category | What I Can Do | Constraints |
|----------|--------------|-------------|
| **Task execution** | Execute tasks from tasks.md | Use subagent for code tasks; can do myself for doc-only tasks |
| **Code changes** | Approve subagent implementation of B/C-class tech debt | NEVER implement code directly; always delegate to subagent |
| **Documentation** | Update docs to reflect code changes | No overclaiming, accurate claims only |
| **Error handling** | Apply fixes from repair_playbook.md | Follow documented procedures |
| **OpenSpec updates** | Update tasks.md status, commit | Follow commit message conventions |
| **Subagent dispatch** | Any task that can be delegated | Set clear scope and acceptance criteria |

### Decisions That Require Human Confirmation

| Category | Why | When to Ask |
|----------|-----|-------------|
| **A-class changes** | Architecture-level, irreversible | Before starting |
| **Breaking changes** | May affect tests or API | Before committing |
| **New OpenSpec creation** | Changes project scope | Before creating |
| **Deletion of files** | Data loss risk | Before committing |
| **Safety constraint overrides** | No-auto-send, no-LLM invariants | Never override |

### Escalation Triggers (Ask Immediately)

```
1. Quality gate fails (fail fast, no retries — escalate immediately)
2. Test coverage drops below 70%
3. OpenSpec validation fails repeatedly
4. Unexpected breaking changes discovered
5. Security issue detected (secrets, keys)
6. Subagent output contradicts task acceptance criteria
7. Human overrides prior decision mid-batch
8. You are blocked for > 10 minutes trying to resolve an issue
```

### How to Escalate

When escalating, provide:
1. **What I tried** — what approach was taken
2. **What happened** — the specific failure or block
3. **What I need** — specific decision or action from human
4. **Options considered** — alternatives already ruled out

### Subagent Principle

Always use subagent for code implementation:
- **backend-engineer** for feature/bug implementation
- **code-reviewer** for architecture/security review
- **Explore** for investigation before planning

I do not implement code directly. I delegate and verify.

---

## 12. Controller Context Rules

Every harness batch must follow these rules:

1. **Update `docs/harness/PROJECT_CONTEXT.md`** — update current phase and tasks when they change.
2. **Commit trigger: subagent returns success + module tests green.** Never commit with failing tests. Never hold uncommitted work after subagent completion.
3. **Controller context is NOT a chat transcript** — never store full conversation logs, API keys, secrets, or raw private communication.
4. **Store only structured handoff summaries**: phase changes, key decisions, validation results, next actions.
5. **Subagent results** go to `subagent_results/` — I read these, not the human.
6. **Error memory** is written to `reports/harness/error_memory.jsonl` — I maintain this.
7. **Subagent verification scope**: run tests for the modified module only (per CLAUDE.md test mapping), not full suite. Full quality gate only at pre-push / archive.

## 13. Portfolio Boundary Wording

All portfolio-facing documents, demo scripts, and README files must include
explicit boundary statements:

- **Fake embeddings**: "Pipeline verification only — no semantic retrieval quality"
- **Seed data**: "All knowledge and eval data are synthetic — not real enterprise data"
- **No auto-send**: "TicketPilot never sends customer replies automatically"
- **Human review**: "High-risk, unsupported, and no-evidence outputs require human review"
- **Evaluation**: "Offline evaluation on 101 synthetic tickets — not a production benchmark"
- **Phase findings**: "Diagnosis-oriented, not production-optimized"

## 14. Error Memory and Learning System

After any failed validation:
- Write to `reports/harness/error_memory.jsonl` — structured error log
- Apply fix from `reports/harness/repair_playbook.md` if available
- Update `repair_playbook.md` if a new pattern is found

Error memory entries record:
- What failed (symptom, error type)
- Root cause (if identified)
- How it was fixed
- Prevention rule

**Do not bloat AGENTS.md with raw logs.** Promote only stable, high-risk, cross-phase rules after confirmation.
**Do not store full chat transcripts** in any harness documentation.
**Do not store secrets, API keys, or Authorization headers** in error memory.

## 15. Context Compression Handoff Rules

Context compression is automatic (system-triggered at ~80% context limit). When triggered:

1. **Check subagent status before compression**:
   - If subagent is in-flight: wait for completion OR commit partial state before compression
   - Never compress with in-flight subagent tasks (results may be partial)

2. **Write structured handoff** to `reports/harness/compression_handoff_<timestamp>.md`
   - Trigger reason: "context compression, system automatic"
   - Current state: phase, active tasks, completion status
   - Subagent status: "completed" / "in-flight (committed)" / "in-flight (not committed)"
   - Next actions
   - Key files

3. **Update PROJECT_CONTEXT.md** — sync current state before compression

4. **NO automatic commit** — commit only when work is complete (atomic per task)

5. **On resume from compression**:
   - Read the latest `compression_handoff_*.md` in `reports/harness/`
   - Read `PROJECT_CONTEXT.md` for full state
   - If subagent was in-flight: check subagent_results/ for final output
   - Resume from where handoff says "待做" (todo)

**Anti-pattern to avoid**: Treating compression as a handoff point. Compression is for state recovery only. Real handoffs happen at task boundaries with commits.

## 16. Phase Loop Workflow

Each phase (logical unit from tasks.md) follows a 7-step loop. See `docs/harness/PHASE_LOOP.md` for full workflow:

| Step | Role | What it does |
|------|------|--------------|
| 1 | Planner | Create step-by-step plan with acceptance criteria |
| 2 | Requirements Analysis | Convert plan to specific requirements |
| 3 | Implementation | Execute based on requirements (via subagent) |
| 4 | Review | Verify against requirements (code-reviewer) |
| 5 | Doc Review | Verify documentation accuracy |
| 6 | Experience Consolidation | Extract learnings, update rules/playbook |
| 7 | Controller Coordination | Orchestrate handoffs, check exit criteria, commit |

**Key rules**:
- Loop back: Review/Doc fails → back to Implementation (max 3 retries, then escalate)
- Phase done: All steps pass → commit + push → next phase
- Controller never implements code directly (always delegate to subagent)
