# Agent Harness 调研报告

> 为 TicketPilot 项目提供 Agent 管理基础设施方案
> 日期: 2026-06-02

---

## 一、什么是 Agent Harness？

Agent Harness 是包裹 AI Agent 的运营基础设施——类似于测试包裹被测软件的测试工具。它提供 Agent 生命周期管理、测试评估、监控观测、部署发布等能力。

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Harness                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Lifecycle │ │ Testing  │ │ Monitor  │ │ Deploy   │  │
│  │ Manager  │ │ & Eval   │ │ & Observe│ │ & CI/CD  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Guardrails & Safety                  │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Your AI Agent (DraftAgent)           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 二、6 大核心组件

### 1. 生命周期管理 (Lifecycle Management)
- 启动/停止/暂停/恢复
- 版本管理 (v1, v2, v3...)
- 回滚能力 (发现问题快速回退)
- 配置热更新

### 2. 测试与评估 (Testing & Evaluation)
- 自动化测试套件
- 基准测试 (Benchmark)
- 回归测试 (新版本 vs 旧版本)
- A/B 测试

### 3. 监控与观测 (Monitoring & Observability)
- 追踪 (Trace) - 每次调用的完整链路
- 指标 (Metrics) - 延迟、成功率、成本
- 日志 (Logging) - 结构化日志
- 告警 (Alerting) - 异常自动通知

### 4. 编排 (Orchestration)
- 多 Agent 协调
- 任务路由
- 并行执行

### 5. 部署 (Deployment)
- CI/CD 集成
- 渐进式发布 (1% → 10% → 100%)
- Canary 部署

### 6. 护栏 (Guardrails)
- 输入验证 (PII 检测、毒性过滤)
- 输出验证 (幻觉检测、引用检查)
- 速率限制
- 成本控制

---

## 三、10 个行业案例

| 项目 | 类型 | 核心能力 | 开源 |
|------|------|----------|------|
| LangSmith | SaaS | 追踪、评估、Prompt 版本管理 | ✗ |
| Helicone | SaaS | LLM 网关、零代码观测、成本追踪 | ✗ |
| BrainTrust | SaaS | 自动评分、回归测试、实验追踪 | ✗ |
| Arize Phoenix | 开源 | OpenTelemetry 追踪、Embedding 可视化 | ✓ |
| Weights & Biases | SaaS | ML 实验追踪、Agent 指标对比 | ✗ |
| LlamaTrace | 开源 | LlamaIndex Agent 追踪和分析 | ✓ |
| AutoGen | 开源 | 多 Agent 编排、对话模式 | ✓ |
| CrewAI | 开源 | 角色扮演 Agent、任务委派 | ✓ |
| Guardrails AI | 开源 | 输入/输出验证、重试逻辑 | ✓ |
| Predibase | SaaS | Agent 部署、容器编排、自动扩缩 | ✗ |

---

## 四、5 种实现模式

### 模式 1: 基于插桩 (Instrumentation-Based)
在 Agent 代码中添加回调/追踪点。

```
Agent 代码 → 添加 trace 回调 → 发送到观测平台
```

**代表**: LangSmith, Arize Phoenix
**优点**: 细粒度控制，可追踪每个步骤
**缺点**: 需要修改 Agent 代码

### 模式 2: 基于代理 (Proxy-Based)
LLM 调用通过网关代理，自动收集指标。

```
Agent → LLM Gateway (Helicone) → LLM API
         ↓
    自动收集延迟、成本、token 数
```

**代表**: Helicone
**优点**: 零代码修改
**缺点**: 只能观测 LLM 调用，无法追踪 Agent 内部逻辑

### 模式 3: 评估优先 (Evaluation-First)
构建评估数据集，运行 Agent，评分，对比版本。

```
评估数据集 → Agent 运行 → 评分 → 版本对比
```

**代表**: BrainTrust
**优点**: 科学的质量度量
**缺点**: 需要构建评估数据集

### 模式 4: 多 Agent 编排 (Multi-Agent Orchestration)
定义 Agent 角色，协调任务执行。

```
Orchestrator → 路由任务 → 专用 Agent 1/2/3 → 汇总结果
```

**代表**: AutoGen, CrewAI
**优点**: 专业化处理，易于扩展
**缺点**: 架构复杂度高

### 模式 5: 护栏优先 (Guardrails-First)
用输入/输出验证器包裹 Agent。

```
输入 → [PII 检测] → [毒性过滤] → Agent → [幻觉检测] → [引用检查] → 输出
```

**代表**: Guardrails AI
**优点**: 安全性高
**缺点**: 可能增加延迟

---

## 五、TicketPilot 应用方案

### 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Agent | ✓ DraftAgent | 多步推理 + Self-reflection |
| 检索 | ✓ BM25 + Vector | 1024 维 DashScope embedding |
| 评估 | ⚠️ 自定义 10 case | 缺 RAGAS 框架 |
| 监控 | ✗ 无 | 缺追踪和指标 |
| 部署 | ⚠️ 手动 | 缺 CI/CD |
| 护栏 | ⚠️ 基础 | 有置信度路由，缺 PII 检测 |

### 推荐实施路线

```
Phase 1 (本周): 可观测性
  → 添加追踪到 DraftAgent
  → 记录每次调用的完整链路
  → 输出结构化日志

Phase 2 (下周): 评估框架
  → 构建 50+ 评估数据集
  → 实现 RAGAS 指标
  → 版本对比能力

Phase 3 (第 3 周): 护栏
  → PII 检测
  → 幻觉检测
  → 引用验证

Phase 4 (第 4 周): 部署
  → Docker 容器化
  → CI/CD 流水线
  → 渐进式发布

Phase 5 (未来): 多 Agent
  → 专用 Agent (退款/投诉/物流)
  → Orchestrator 路由
```

### 推荐技术栈

| 组件 | 推荐 | 理由 |
|------|------|------|
| 追踪 | 自定义 trace + JSON 日志 | 轻量级，无需额外依赖 |
| 评估 | 自定义 RAGAS | 已有 deepeval 缓存 |
| 护栏 | 自定义验证器 | 无需 Guardrails AI 依赖 |
| 部署 | Docker + docker-compose | 简单可靠 |
| 监控 | 自定义指标 + Prometheus | 可选，后期再加 |

---

## 六、快速实施：可观测性 (Phase 1)

### 目标
为 DraftAgent 添加追踪能力，记录每次调用的完整链路。

### 实现方案

```python
# 1. 定义追踪数据结构
@dataclass
class AgentTrace:
    trace_id: str
    timestamp: datetime
    input: dict
    steps: list[dict]  # 每个步骤的输入/输出/耗时
    output: dict
    metrics: dict  # 延迟、token 数、成本
    
# 2. 在 DraftAgent 中添加追踪
class DraftAgent:
    def generate_draft(self, ...):
        trace = AgentTrace(...)
        
        # Step 1: 检索
        with trace.step("retrieve"):
            evidence = self._retrieve(query)
        
        # Step 2: 生成
        with trace.step("generate"):
            draft = self._generate(evidence)
        
        # Step 3: 验证
        with trace.step("verify"):
            verified = self._verify(draft)
        
        trace.finish()
        return verified, trace
```

### 输出格式

```json
{
  "trace_id": "abc-123",
  "timestamp": "2026-06-02T10:00:00Z",
  "input": {"message": "我要退款", "intent": "refund"},
  "steps": [
    {"name": "retrieve", "duration_ms": 150, "evidence_count": 10},
    {"name": "generate", "duration_ms": 2000, "tokens": 500},
    {"name": "verify", "duration_ms": 100, "passed": true}
  ],
  "output": {"draft_text": "...", "confidence": 0.9},
  "metrics": {"total_ms": 2250, "tokens": 500, "cost": 0.001}
}
```

---

## 七、总结

### Agent Harness 的价值

| 价值 | 说明 |
|------|------|
| 可观测 | 知道 Agent 在做什么，为什么这么做 |
| 可测试 | 科学评估 Agent 质量，版本对比 |
| 可控制 | 安全护栏，防止危险操作 |
| 可部署 | 自动化发布，快速回滚 |
| 可扩展 | 多 Agent 协调，专业化处理 |

### TicketPilot 下一步

1. **本周**: 实现 Phase 1 (可观测性)
2. **下周**: 实现 Phase 2 (评估框架)
3. **第 3 周**: 实现 Phase 3 (护栏)
4. **第 4 周**: 实现 Phase 4 (部署)

### 参考资源

- [Arize Phoenix](https://github.com/Arize-ai/phoenix) - 开源可观测性
- [Guardrails AI](https://github.com/guardrails-ai/guardrails) - 安全护栏
- [AutoGen](https://github.com/microsoft/autogen) - 多 Agent 编排
- [CrewAI](https://github.com/joaomdmoura/crewAI) - 角色扮演 Agent
