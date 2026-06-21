# TicketPilot — AI Agent Constitution

> **Bootstrap**: This file is loaded by `.claude/CLAUDE.md`. On new clones, see `.claude/CLAUDE.md` for harness overview. For phase execution workflow, see `docs/harness/PHASE_LOOP.md`.

## 0. Workflow Skills (必须加载)

**每次开始工作前，检查以下 skill 是否需要加载：**

| 场景 | 触发词 | 加载 Skill |
|------|--------|-----------|
| 写 PRD / 需求 / 验收标准 | "写PRD"、"写需求"、"验收钩子" | `pm-tech-verification-hooks` |
| 用 Claude Code 做编码任务 | "用Claude Code"、"claude -p" | `hermes-claude-code-workflow` |
| 委托子 agent 做审查/研究 | "delegate_task"、"委托任务" | `hermes-workflow-patterns` |
| 实现功能 / 修 bug | "实现"、"开发"、"写代码" | `code-with-review-hook` |
| PM 给 Tech 派任务 | "给Claude Code写任务" | `pm-tech-verification-hooks` + `hermes-claude-code-workflow` |
| 复杂任务需要监控进度 | "监控Claude Code"、"观察进度" | `claude-code-progress-monitor` |

**核心工作流:**
```
PM 写 PRD + 验收钩子 (pm-tech-verification-hooks)
    ↓
Claude Code 实现 (hermes-claude-code-workflow)
    ↓
PM 只看钩子输出 (不看代码)
```

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
- A generic RAG or chatbot

All knowledge data and eval tickets are synthetic. All embeddings use deterministic
providers (FakeEmbeddingProvider by default; real provider opt-in via `.env.local`).

## 2. Non-Negotiable Boundaries

| Rule | Enforcement |
|---|---|
| Tiered auto-send | HIGH/MEDIUM confidence → auto-send; LOW → human review; CRITICAL → escalate to human |
| No LLM calls in pipeline | Classification, risk, retrieval, drafting are all deterministic |
| No real customer data | All seed data and eval tickets are synthetic |
| No API keys in repo | `.env` and `.env.local` are gitignored; `.env.example` has placeholders |
| No `|| true` in quality gate | Every failure must be visible |
| No coverage threshold lowering | Minimum 70% coverage, enforced |
| No `# noqa` without justification | Only allowed for specific false positives |
| No Phase 7/8/9 baseline report modification | Baseline reports are immutable |
| No `openspec/` archived change modification | Archived changes are read-only |
| Integration skipped must = 0 for archive/push | DB-dependent tests must pass or be properly skipped |
| Rule changes require test sync | Changing keywords/thresholds/rules MUST update golden cases + data files in same commit |

## 2.1 Rule-Test Synchronization (规则变更同步规范)

**核心原则：改了规则就必须同步改测试，同一次提交完成。**

| 变更类型 | 必须同步的文件 | 示例 |
|----------|---------------|------|
| 关键词列表变更 | `risk/rules.py` + `test_intake_risk_triage.py` + `test_risk.py` | 添加/删除风险关键词 |
| 阈值变更 | `config.py` + `test_risk.py` + `test_pipeline.py` | 修改 CONFIDENCE_THRESHOLD |
| severity 映射变更 | `risk/assessor.py` + `test_risk.py` + `test_pipeline.py` | 修改 flag→severity 规则 |
| intent 分类变更 | `classification/` + `test_classification.py` | 添加/删除 intent 类别 |
| eval 数据变更 | `data/eval/` + `test_run_eval_cli.py` | 新增/修改 golden expectations |

**验证方法（提交前必跑）：**

```bash
# 1. 跑 golden case 测试
uv run pytest tests/unit/test_intake_risk_triage.py::TestGoldenCases -v

# 2. 跑 risk 测试
uv run pytest tests/unit/test_risk.py -v

# 3. 跑 pipeline 测试
uv run pytest tests/unit/test_pipeline.py -v

# 4. 如果改了 eval 数据
uv run pytest tests/unit/test_run_eval_cli.py -v
```

**反模式：**
- ❌ 改了 `rules.py` 但没跑 golden case 测试
- ❌ golden case 期望值和业务逻辑不一致
- ❌ eval 数据行数和 golden expectations 行数不匹配

**Why this matters：** 2026-06-21 CI 连续 5 次失败，根因是 "退款" 被加进 COMPENSATION_RISK 关键词但 golden case 没同步更新。如果提交前跑了 golden case 测试，这个问题在本地就会被捕获。

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

### 🔒 Automatic protection

| Layer | What | Where |
|-------|------|-------|
| Pre-commit hook | `gitleaks` scans staged changes before every `git commit` | Global `~/.git-hooks/pre-commit` (core.hooksPath) |
| Pre-push hook | `gitleaks` scans pushed commit range before every `git push` | Global `~/.git-hooks/pre-push` |
| CI | `gitleaks-action@v2` runs on every push/PR | `.github/workflows/ci.yml` → `secrets-scan` job |
| Skip | `git commit --no-verify` or `GITLEAKS_SKIP=1 git commit` | Emergency bypass only |

### 📋 `.gitleaks.toml`

Project-level allowlist at repo root (`./.gitleaks.toml`). Gitleaks auto-detects it. Currently covers test fixture placeholders (`sk-sec...2345`, `sk-tes...2345`).

### 🚨 Incident response

If a secret is committed and pushed:

1. **Rotate the key immediately** at the provider's website (OpenCode, OpenAI, etc.)
2. **Clean git history** with `git filter-repo` or BFG Repo-Cleaner
3. **Force push** the cleaned history
4. **Remove the file** (if applicable) and use env vars instead
5. **Update `.gitleaks.toml`** to prevent recurrence

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

## 17. 文档维护约定

> 见 `docs/MAINTENANCE.md` 完整版。以下是本文件的核心摘录。

### 17.1 不更新文档 = 没做完

任何阶段完成后，**必须**更新：
1. `CHANGELOG.md` — `[Unreleased]` 填写变更内容。**未更新 CHANGELOG 的 commit 不能标记 `[verified]`**
2. `docs/INDEX.md` — 如果新增/修改了文件
3. 受影响的技术文档 — 至少加过期标记

### 17.2 更新时机速查

| 时机 | 必须更新 |
|------|---------|
| 阶段 merge 时 | CHANGELOG.md + 受影响的 technical docs |
| 新增文件 | docs/INDEX.md |
| 评测数据/指标变化 | CHANGELOG.md |
| 淘汰旧功能 | 标记 deprecated + 更新 INDEX |

### 17.3 文档清理

| 类型 | 处理 |
|------|------|
| `docs/plans/` | 阶段归档后移入 `archive/` 或删除 |
| `docs/CHECKPOINT_*.md` | 归档到 CHANGELOG 后删除 |
| `docs/technical/` | 永久保留，修改时同步更新 |

### 17.4 一句话

> 每完成一件事，停下来更新一次文档。**不更新等于没做完**。
