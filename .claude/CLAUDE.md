# TicketPilot — CLAUDE.md

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
| `src/ticketpilot/review/` | `tests/unit/test_review_*.py` |
| `src/ticketpilot/retrieval/db/seeding.py` | `tests/unit/test_seed_data.py` |
| `scripts/run_eval.py` | `tests/unit/test_run_eval_cli.py` |

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
