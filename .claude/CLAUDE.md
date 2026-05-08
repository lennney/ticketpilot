# TicketPilot — CLAUDE.md

## Controller Harness System

This project uses a **Controller Harness** — an AI orchestration system for managing development phases. When Claude Code starts in this repo, it can operate in two modes:

### Mode 1: Direct Development (Default)
Standard code changes, tests, and documentation. Uses this CLAUDE.md validation rules.

### Mode 2: Controller Mode (Long-running phases)
For complex multi-step features. Follows `AGENTS.md` Controller rules.

**How to enter Controller Mode:**
- Human requests a phase implementation from `tasks.md`
- Human says "start phase N" or "run controller harness"
- Human hands off a task marked `[CODE]` or `[AUTO]`

**Controller Mode reads these files (in order):**
1. `AGENTS.md` — Core rules (Sections 11-16 operationalize the harness)
2. `docs/harness/PHASE_LOOP.md` — 7-step phase execution workflow
3. `docs/harness/PROJECT_CONTEXT.md` — Current phase and state
4. `docs/harness/skills/` — Reusable patterns and error fixes

**Controller Mode rules:**
- Never implement code directly — always delegate to subagent
- Use subagent types: `backend-engineer` (code), `code-reviewer` (review)
- Commit after: subagent success + module tests green
- Escalate immediately: quality gate fails, coverage drops, 3 retries exhausted

**Quick reference for Controller Mode:**
```
Phase execution: docs/harness/PHASE_LOOP.md
Current state: docs/harness/PROJECT_CONTEXT.md
Error patterns: docs/harness/skills/
Fix procedures: reports/harness/repair_playbook.md
Handoff outputs: subagent_results/
```

---

## 验证策略选择

变更范围决定验证级别。详细规则见 `docs/technical/validation_policy.md`，摘要如下：

| 范围 | OpenSpec | 测试 | Quality Gate |
|---|---|---|---|
| Docs/portfolio only | 不要求 | 不要求 | 不要求 |
| 单 OpenSpec change | `--strict` scoped | 模块级 | 不要求 |
| Core pipeline / DB / data | `--all` | 全量 | 必须（0 skip） |
| Pre-push / archive / 阶段收口 | `--all` | 全量 | 必须（0 skip） |

## 测试选择指南

总则：改哪个模块就只跑对应测试文件。642 个测试全跑太慢，按模块精确测试。

### 源码 ↔ 测试文件映射

| 源码路径 | 测试文件 |
|---|---|
| `src/ticketpilot/agent/loop.py` | `tests/unit/test_agent_loop.py` |
| `src/ticketpilot/agent/memory.py` | `tests/unit/test_agent_memory.py` |
| `src/ticketpilot/agent/planner.py` | `tests/unit/test_agent_planner.py` |
| `src/ticketpilot/agent/registry.py` | `tests/unit/test_agent_registry.py` |
| `src/ticketpilot/agent/schemas.py` | `tests/unit/test_agent_schemas.py` |
| `src/ticketpilot/agent/skill_loader.py` | `tests/unit/test_agent_skill_loader.py` |
| `src/ticketpilot/agent/tools.py` | `tests/unit/test_agent_tools.py` |
| `src/ticketpilot/agent/trace.py` | `tests/unit/test_agent_trace.py` |
| `src/ticketpilot/classification/` | `tests/unit/test_classification.py` |
| `src/ticketpilot/drafting/generate.py` | `tests/unit/test_drafting_generate.py` |
| `src/ticketpilot/drafting/pipeline.py` | `tests/unit/test_drafting_pipeline.py` |
| `src/ticketpilot/drafting/provider.py` | `tests/unit/test_drafting_provider.py` |
| `src/ticketpilot/drafting/schemas.py` | `tests/unit/test_drafting_schemas.py` |
| `src/ticketpilot/intake/` | `tests/unit/test_intake.py` |
| `src/ticketpilot/risk/` | `tests/unit/test_risk.py` |
| `src/ticketpilot/schema/ticket.py` | `tests/unit/test_schema_validation.py` |
| `src/ticketpilot/schema/evidence.py` | `tests/unit/test_evidence_schema.py` |
| `src/ticketpilot/pipeline.py` | `tests/unit/test_pipeline.py` |
| `src/ticketpilot/intake/risk_triage.py` | `tests/unit/test_intake_risk_triage.py` |
| `src/ticketpilot/retrieval/chunker.py` | `tests/unit/test_chunking.py` |
| `src/ticketpilot/retrieval/citation_validator.py` | `tests/unit/test_citation_validator.py` |
| `src/ticketpilot/retrieval/evidence_mapper.py` | `tests/unit/test_evidence_mapper.py` |
| `src/ticketpilot/retrieval/rrf.py` | `tests/unit/test_rrf.py` |
| `src/ticketpilot/retrieval/query_builder.py` | `tests/unit/test_query_builder.py` |
| `src/ticketpilot/retrieval/retrieve_evidence.py` | `tests/unit/test_retrieve_evidence.py` |
| `src/ticketpilot/retrieval/providers/fake_embedding.py` | `tests/unit/test_fake_embedding.py` |
| `src/ticketpilot/retrieval/schema/knowledge.py` | `tests/unit/test_knowledge_schema.py` |
| `src/ticketpilot/retrieval/pipeline.py` | `tests/unit/test_pipeline_retrieval.py` |
| `src/ticketpilot/evaluation/` | `tests/unit/test_evaluation_*.py` |
| `src/ticketpilot/evaluation/retrieval_metrics.py` | `tests/unit/test_retrieval_metrics.py` |
| `src/ticketpilot/evaluation/retrieval_comparison.py` | `tests/unit/test_retrieval_comparison.py` |
| `src/ticketpilot/review/` | `tests/unit/test_review_*.py` |
| `src/ticketpilot/retrieval/db/seeding.py` | `tests/unit/test_seed_data.py` |
| `scripts/run_eval.py` | `tests/unit/test_run_eval_cli.py` |
| `scripts/run_retrieval_comparison.py` | `tests/unit/test_retrieval_metrics.py` |

### 测试策略分级

**Level 1 — 开发中快速验证**（改完后立即跑）
```
uv run pytest tests/unit/test_xxx.py -v --tb=short
```
耗时 1-30 秒。覆盖单个模块的改动。

**Level 2 — 跨模块影响检查**（改了 agent 或多模块时）
```
# Agent 全模块
uv run pytest tests/unit/test_agent_*.py -v --tb=short

# 检索全模块
uv run pytest tests/unit/test_retrieval*.py tests/unit/test_chunking.py tests/unit/test_evidence_mapper.py -v --tb=short

# 评估全模块
uv run pytest tests/unit/test_evaluation_*.py tests/unit/test_run_eval_cli.py -v --tb=short
```
耗时 30s-2 分钟。

**Level 3 — 提交前 Quality Gate**（最终检查）
```
bash scripts/run_quality_gate.sh
# 或跳过集成测试（无数据库时）：
TICKETPILOT_SKIP_DB_TESTS=1 bash scripts/run_quality_gate.sh
```
耗时 ~7 分钟。全量 642 测试 + ruff + coverage(≥70%) + OpenSpec 校验 + 密钥扫描。

### 集成测试注意事项

集成测试需要运行中的 PostgreSQL 数据库。无数据库时：
- `test_evaluation_pipeline.py` — 使用 `pytest.skip()`，设置 `TICKETPILOT_SKIP_DB_TESTS=1` 可跳过
- `test_agent_runtime.py` — 使用 `pytest.fail()`，数据库不可用时直接报错失败

### 例外情况

修改底层模块（schema、classification、retrieval/pipeline）后，最好也跑一下 `test_evaluation_*.py`，因为这些模块被评估链路依赖。
