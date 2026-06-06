# TicketPilot × 12-Factor Agents Gap Analysis & 实施计划

> 日期: 2026-06-06
> 基于: https://github.com/humanlayer/12-factor-agents (★23k)

## 12-Factor 对照评估

| # | Factor | 现状 | 差距 | 优先级 |
|---|--------|------|------|--------|
| 1 | Natural Language → Tool Calls | ✅ `planner.py` 关键词→AgentPlan→tools | 确定性匹配，合理 | - |
| 2 | Own Your Prompts | ⚠️ prompt 散落在 `prompt_builder.py` + `generate.py` | 无版本号，无 A/B 测试支持 | P1 |
| 3 | Own Your Context Window | ⚠️ `post_process` 控制置信度/降级，但 retrieval 上下文未显式管理 | 需要 context truncation 策略 | P2 |
| 4 | Tools Are Structured Outputs | ✅ 所有 tool 返回 `dict`（Pydantic `.model_dump()`） | 合理 | - |
| 5 | Unify Execution State | ⚠️ `WorkingMemory` + `AgentRun` 存在，但 pipeline 状态和 agent 状态分开 | 需要统一状态源 | P1 |
| 6 | Launch / Pause / Resume | ❌ 无持久化，无 pause/resume | **生产必须** | P0 |
| 7 | Contact Humans with Tools | ⚠️ `ReviewConsole` 是 UI，agent 没有 `request_human_input()` tool | 需要 tool 化 | P0 |
| 8 | Own Your Control Flow | ✅ `agent/loop.py` 显式控制流 | 合理 | - |
| 9 | Compact Errors into Context | ❌ try/except 降级到默认值，错误信息丢失 | **需要 error compaction** | P1 |
| 10 | Small, Focused Agents | ✅ 模块化：intake/classify/risk/retrieval/draft 各自独立 | 合理 | - |
| 11 | Trigger from Anywhere | ⚠️ 只有 HTTP API + Streamlit | 需要 webhook/queue/CLI 触发器 | P2 |
| 12 | Stateless Reducer | ⚠️ pipeline.py 是无状态函数，但 agent/loop.py 有副作用 | 需要确保 reducer 模式 | P1 |

**得分: 4/12 完全满足, 5/12 部分满足, 3/12 不满足**

---

## 实施计划（按优先级）

### P0-1: Factor 6 — Launch / Pause / Resume

**问题**: agent 运行到需要人工审核时，没有持久化状态，无法 pause 和 resume。

**方案**: 给 AgentRun 加 SQLite 持久化 + resume API。

```python
# agent/state_store.py (新文件)
class AgentStateStore:
    """SQLite-backed agent run state persistence."""
    
    def save_run(self, run: AgentRun) -> None:
        """Persist agent run state to SQLite."""
        ...
    
    def load_run(self, run_id: str) -> AgentRun | None:
        """Load agent run state from SQLite."""
        ...
    
    def pause_run(self, run_id: str, reason: str) -> None:
        """Mark run as paused (e.g., waiting for human review)."""
        ...
    
    def resume_run(self, run_id: str, human_input: dict) -> AgentRun:
        """Resume a paused run with human input."""
        ...
    
    def list_paused(self) -> list[AgentRun]:
        """List all runs waiting for human input."""
        ...
```

**集成点**:
- `agent/loop.py` 在 `HUMAN_REVIEW_REQUIRED` 事件时自动 pause
- Review Console 审批后调用 `resume_run()`
- API 端点: `POST /api/agent/{run_id}/pause`, `POST /api/agent/{run_id}/resume`

**文件**: `src/ticketpilot/agent/state_store.py` (~150 行)
**测试**: `tests/unit/test_agent_state_store.py` (~100 行)

---

### P0-2: Factor 7 — Contact Humans with Tools

**问题**: 人工审核是 UI 层的事，agent 没有 tool 可以主动请求人工输入。

**方案**: 新增 `request_human_input` tool，agent 可以在任何步骤调用。

```python
# agent/tools.py 中新增
def request_human_input_tool(input_data: dict) -> dict:
    """Agent tool: request human input for a decision.
    
    Input:
        question: str — what to ask the human
        context: dict — relevant context for the human
        options: list[str] — optional predefined choices
        urgency: str — "low" | "medium" | "high"
    
    Output:
        status: "paused" — run is now paused
        run_id: str — use this to resume later
    """
    # 1. Save current run state (Factor 6)
    # 2. Create human request record
    # 3. Return paused status
    ...
```

**集成点**:
- `agent/loop.py` 的 tool registry 注册此 tool
- agent 在 confidence < 0.4 时自动调用此 tool
- Review Console 显示待处理的人工请求队列

**文件**: 修改 `src/ticketpilot/agent/tools.py` (~60 行新增)
**测试**: `tests/unit/test_agent_tools.py` (新增测试)

---

### P1-1: Factor 9 — Compact Errors into Context

**问题**: pipeline.py 的 try/except 降级到默认值，错误信息不反馈给 agent。

**方案**: 错误压缩后注入 WorkingMemory，让 agent 的后续步骤能看到。

```python
# 新增 error compaction 函数
def compact_error(error: Exception, context: str, max_len: int = 200) -> str:
    """Compact an error into a short, actionable summary.
    
    Examples:
        ConnectionError("Connection refused by peer") 
        → "RETRIEVAL_FAILED: connection refused (context: evidence_retrieval)"
        
        ValueError("empty text after normalization")
        → "INTAKE_FAILED: empty text after normalization (context: intake)"
    """
    error_type = type(error).__name__
    msg = str(error)[:max_len]
    return f"{error_type}: {msg} (context: {context})"
```

**集成点**:
- `pipeline.py` 的每个 try/except 块：catch 后 compact error 存入 result
- `agent/loop.py` 的 WorkingMemory：每个 step 的 error 自动存入
- ConfidenceScorer：如果有 error，降低对应维度的分数

**文件**: `src/ticketpilot/agent/error_compaction.py` (~60 行)
**测试**: `tests/unit/test_error_compaction.py` (~50 行)

---

### P1-2: Factor 2 — Own Your Prompts

**问题**: prompt 散落在代码里，没有版本管理。

**方案**: 集中到 `prompts/` 目录，Pydantic schema 管理版本。

```python
# prompts/manager.py
class PromptVersion(BaseModel):
    prompt_id: str
    version: str       # semver: "1.0.0"
    template: str      # Jinja2 template
    variables: list[str]
    created_at: datetime
    changelog: str

class PromptManager:
    """Version-managed prompt templates."""
    
    def get(self, prompt_id: str, version: str = "latest") -> PromptVersion: ...
    def render(self, prompt_id: str, variables: dict, version: str = "latest") -> str: ...
    def list_versions(self, prompt_id: str) -> list[PromptVersion]: ...
```

**文件**: `src/ticketpilot/prompts/manager.py` (~120 行) + `prompts/templates/` 目录
**测试**: `tests/unit/test_prompt_manager.py` (~80 行)

---

### P1-3: Factor 5 — Unify Execution State

**问题**: pipeline 状态（TicketOutput）和 agent 状态（AgentRun + WorkingMemory）分开管理。

**方案**: 统一到 AgentRun 的 WorkingMemory 中，pipeline 的每个阶段输出都存入。

```python
# agent/loop.py 中修改
def run_agent_pipeline(raw_ticket, ...) -> AgentRun:
    memory = WorkingMemory(run_id)
    
    # 每个 step 的输出都存入 WorkingMemory
    memory.set("normalized", normalize_result)
    memory.set("classification", classify_result)
    memory.set("risk", risk_result)
    memory.set("evidence", evidence_result)
    memory.set("draft", draft_result)
    memory.set("confidence", confidence_breakdown)  # 新增
    memory.set("degraded", degraded_response)        # 新增
    
    # 单一状态源
    return agent_run
```

**文件**: 修改 `src/ticketpilot/agent/loop.py`

---

### P1-4: Factor 12 — Stateless Reducer

**问题**: `pipeline.py` 的 `intake_risk_pipeline()` 是纯函数（无状态 reducer），但 `agent/loop.py` 有副作用（写 WorkingMemory）。

**方案**: 确保 pipeline 保持纯函数，副作用只在 agent loop 层。

```python
# pipeline.py — 保持纯函数
def intake_risk_pipeline(raw_ticket) -> TicketOutput:
    """Pure function: input → output, no side effects."""
    ...

def post_process(ticket_output, draft) -> tuple[Confidence, Degraded]:
    """Pure function: input → output, no side effects."""
    ...

# agent/loop.py — 副作用只在这里
def run_agent_pipeline(raw_ticket) -> AgentRun:
    memory = WorkingMemory(run_id)
    result = intake_risk_pipeline(raw_ticket)  # pure
    memory.set("pipeline_result", result)       # side effect here
    ...
```

**验证**: 给 pipeline 加 idempotency 测试（同样输入 → 同样输出）

**文件**: `tests/unit/test_pipeline_idempotency.py` (~50 行)

---

### P2: Factor 3 + Factor 11（低优先级）

**Factor 3 (Context Window)**: 加 retrieval context truncation — 当检索到的 chunks 太多时，按 score 排序截断。

**Factor 11 (Trigger from Anywhere)**: 加 CLI 触发器 + webhook 接收器。

---

## 依赖关系

```
P0-1 (State Store) ← P0-2 (Human Tool 依赖 State Store)
  ↓
P1-1 (Error Compaction)
  ↓
P1-3 (Unified State) ← 依赖 State Store + Error Compaction
  ↓
P1-4 (Stateless Reducer 验证)
  ↓
P1-2 (Prompt Manager) — 独立
  ↓
P2 (Context + Triggers) — 最后
```

## 预估工作量

| Task | 新增文件 | 修改文件 | 测试 | 行数 |
|------|---------|---------|------|------|
| P0-1 State Store | 1 | 1 | 1 | ~250 |
| P0-2 Human Tool | 0 | 1 | 1 | ~110 |
| P1-1 Error Compaction | 1 | 1 | 1 | ~110 |
| P1-2 Prompt Manager | 2 | 0 | 1 | ~200 |
| P1-3 Unified State | 0 | 1 | 0 | ~50 |
| P1-4 Stateless Reducer | 0 | 0 | 1 | ~50 |
| **合计** | **4** | **4** | **5** | **~770** |

## 验收标准

1. **Factor 6**: AgentRun 可以 save → pause → resume，Review Console 审批后自动 resume
2. **Factor 7**: agent 可以调用 `request_human_input` tool，run 自动 pause
3. **Factor 9**: pipeline 错误被 compact 后存入 WorkingMemory，后续步骤可见
4. **Factor 2**: prompt 有版本号，可以通过 PromptManager.get() 获取指定版本
5. **Factor 5**: pipeline 每阶段输出统一存入 WorkingMemory
6. **Factor 12**: pipeline 纯函数测试通过（幂等性）
7. **所有测试通过**: `pytest tests/unit/ -v`
