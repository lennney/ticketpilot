# AI Development Harness for TicketPilot

## Why TicketPilot Needs a Development Harness

TicketPilot began as a spec-driven, AI-assisted project. Over 10 phases, the
collaboration pattern between human and AI evolved organically. The result:
a rich set of conventions, rules, and workflows scattered across CLAUDE.md,
OpenSpec specs, changelog entries, and agent memories.

This harness formalizes those patterns into a **reusable, project-level AI
development framework** — inspired by OpenAI Codex's "constitution" approach,
where the AI agent operates within explicit guardrails, test-backed validation,
and traceable commit discipline.

The harness addresses these recurring failure modes:
- **Scope creep**: AI agent adds features beyond the current phase
- **Silent skips**: Integration tests skipped without detection (Phase 9.7.1)
- **Baseline overwrite**: Phase 7/8/9 reports accidentally modified
- **Untested changes**: Code modified without running corresponding tests
- **Unsafe iteration**: AI continues autonomously past a failing checkpoint

## OpenAI Codex-Style Principles

### Persistent Repo Instructions
The project's `AGENTS.md` serves as a constitution file that every AI agent
reads at session start. It defines identity, boundaries, stack, validation
rules, and artifact conventions. No secret, no API key, no env-specific
path lives in `AGENTS.md` — only universal project rules.

### Sandboxed Tasks
Each task (OpenSpec phase or batch) has an explicit scope declaration:
- Allowed files (e.g., `openspec/changes/<id>/`, `docs/`)
- Forbidden files (e.g., `src/`, `tests/`, `pyproject.toml`)
- Stop conditions (e.g., "working tree dirty, stop and report")

The AI agent stops and waits for human approval when a stop condition triggers.

### Approval / Stop Conditions
Every batch prompt template includes a `## Stop Conditions` section:
- Working tree not clean
- Validation command fails
- Forbidden file modified
- Coverage below threshold
- Integration skipped > 0 (for core changes)

### Test-Backed Changes
Every code change must:
1. Be traceable to a specific OpenSpec task
2. Have corresponding tests (unit, integration, or both)
3. Pass module-level tests before commit
4. Pass full quality gate before archive

Documentation-only changes skip testing but still run `ruff` and `openspec validate --strict`.

### Traceable Commits
Every commit message includes:
- What changed (scope + module)
- Why (the problem or requirement)
- Validation result (tests passed, quality gate status)

Format:
```
<type>: <short description>

<context and motivation>

<validation summary>
```

### PR / Commit-Style Summaries
At the end of each batch, the AI agent returns a structured summary:
1. Files added/modified
2. Key decisions
3. Validation results
4. Remaining risks
5. Whether stop conditions were triggered

## TicketPilot Harness Layers

### 1. Project Constitution Harness

**File**: `AGENTS.md` (project root)

Read by every AI agent at session start. Contains:
- Project identity and what it is NOT
- Non-negotiable boundaries (10 rules)
- Tech stack summary
- Development environment setup
- Validation level matrix
- Secret rules
- OpenSpec workflow
- Quality gate rules
- Phase artifact rules
- Portfolio boundary wording

**Enforcement**: Human review catches violations; automated checks in quality gate
catch some (secret scan, coverage, integration skips).

### 2. Task Harness

**File**: `prompts/harness/*.md` (one template per batch type)

Provides reusable prompt templates for common batch types:
- Phase planning (OpenSpec proposal/design/tasks)
- Documentation-only changes
- Data changes (knowledge records, eval data)
- Code changes (src/ or tests/ modifications)
- Evaluation rerun
- OpenSpec archive
- Post-failure repair

Each template enforces:
- Allowed / forbidden files
- Stop conditions
- Validation commands per batch type
- Commit/push rules
- Structured return format

### 3. Validation Harness

**File**: `scripts/run_quality_gate.sh` + `pyproject.toml` (pytest, ruff config)

Multi-layered validation:
| Layer | Command | When |
|---|---|---|
| Lint | `ruff check .` | Every batch |
| Unit tests | `uv run pytest tests/unit/` | Code changes |
| Integration tests | `uv run pytest tests/integration/` | Core pipeline, DB |
| Coverage | `--cov=src/ticketpilot --cov-fail-under=70` | Core changes |
| OpenSpec scoped | `openspec validate <id> --strict` | Active change |
| OpenSpec full | `openspec validate --all` | Pre-archive, pre-push |
| Secret scan | grep for `sk-` patterns | Pre-commit, pre-push |
| Full quality gate | `bash scripts/run_quality_gate.sh` | Pre-archive, pre-push |

### 4. Role Harness

**Project Director** — Creates OpenSpec proposals, design docs, task breakdowns.
Evaluates scope creep, validates non-goals, selects next phase.

**System Architect** — Reviews architecture constraints, data flow, module
boundaries, schema contracts. Ensures design.md matches current architecture.

**QA Evaluator** — Designs test strategy, golden cases, acceptance criteria.
Detects skipped integration tests, coverage gaps, regression risks.

**Phase Supervisor** — Reviews batch output against tasks.md. Decides:
ACCEPTED, ACCEPTED_WITH_GAPS, or REJECTED. Blocks continuation on failure.

**Backend Engineer** — Implements code changes within OpenSpec scope.
Runs module-level tests, writes new tests, follows existing patterns.

**Code Reviewer** — Audits architecture drift, secret leaks, schema mismatch,
weak tests, duplicated logic, maintainability problems.

### 5. Trace / Evidence Harness

All changes are traceable through:
- **OpenSpec change directory**: `openspec/changes/<change-id>/` contains
  proposal, design, tasks, and spec deltas
- **Changelog**: `docs/changelog.md` records every batch with file list,
  validation results, and design notes
- **Commit messages**: Structured format linking to phase context
- **Retrieval trace**: `RetrievalTrace` captures keyword/vector/fused per-ranker
  results for debugging
- **Reports**: `reports/retrieval/phase*` contain evaluation results, gap maps,
  hit audits, and diagnosis findings

### 6. Portfolio Harness

Portfolio documents are generated at **phase boundaries only**, not per-batch.
Rules:
- Each phase creates its own snapshot (`phase10_*`, `phase11_*`, etc.)
- Prior phase portfolios are immutable
- All portfolio docs carry explicit boundary wording (see AGENTS.md §10)
- No production-ready claims, no deployment claims, no real-data claims

## How to Use with Claude Code

1. **Session start**: Claude reads `AGENTS.md` as project constitution
2. **Task prompt**: User provides task with allowed/forbidden file scope
3. **Plan**: Claude reads relevant OpenSpec change, existing code, tests
4. **Implement**: Claude follows task harness template for the batch type
5. **Validate**: Claude runs appropriate validation layer
6. **Report**: Claude returns structured summary (files, decisions, validation, risks)
7. **Human review**: User reviews, approves or requests changes
8. **Commit/push**: Only on human approval

## How to Use with OpenAI Codex / Codex CLI

1. **Set constitution**: `export CODEX_CONSTITUTION=AGENTS.md`
2. **Provide task**: Pass the batch prompt template with specific parameters
3. **Set boundaries**: Use `--allowed-paths` and `--forbidden-paths` flags
4. **Run**: Codex executes within the harness, stopping on condition triggers
5. **Review**: Human review before any merge or push

The prompt templates in `prompts/harness/` are Codex-compatible — they use
the same structure (context, goal, allowed/forbidden files, stop conditions,
validation commands, return format).

## How to Avoid Unsafe Autonomous Iteration

| Risk | Mitigation |
|---|---|
| Agent continues after failure | Stop conditions: validation failure = STOP, report to human |
| Agent modifies forbidden files | Explicit forbidden list in every prompt; git diff check |
| Agent skips tests | Each batch template has mandatory test commands |
| Agent lowers standards | No `--no-verify`, no `|| true`, no coverage threshold changes |
| Agent overwrites history | Phase 7/8/9 baselines are immutable; archived specs are read-only |
| Agent commits without review | All commits require human approval |
| Agent introduces secrets | Secret scan in quality gate; git diff check before commit |

## Recommended Workflow for Phase 10+

1. **Planning** (`prompts/harness/phase_planning.md`):
   - Create OpenSpec proposal/design/tasks spec deltas
   - Validate `--strict`
   - No code changes
2. **Implementation** (`prompts/harness/code_change_batch.md` or `data_change_batch.md`):
   - Follow tasks.md phase order
   - Run module-level tests after each sub-task
   - Stop on failure, report to human
3. **Evaluation** (`prompts/harness/evaluation_rerun.md`):
   - Run pipeline-backed evaluation
   - Output to `reports/retrieval/phase10_*`
   - Do not overwrite prior phase reports
4. **Validation**:
   - Module tests → integration tests → coverage
   - OpenSpec scoped validation
   - Full quality gate before archive
5. **Archive** (`prompts/harness/archive_change.md`):
   - Verify integration skipped = 0
   - Run full quality gate
   - `openspec archive`
   - Post-archive verify
6. **Portfolio**:
   - Create compact snapshot at phase close
   - Carry boundary wording
   - Do not overwrite prior phase portfolios
