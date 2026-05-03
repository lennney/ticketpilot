# TicketPilot

> 中文客服工单分类与证据驱动回复助手 — 本地演示 / 作品集项目
>
> **这不是生产级客服系统。不会自动发送回复。**

---

## 1. 这是什么？

TicketPilot 是一个面向中文客服场景的工单处理演示系统。它接收非结构化的中文客服消息，依次经过规范化、意图分类、风险评估、分层知识检索、证据驱动的草稿生成，最终通过人工审核控制台完成决策。

**核心定位：**
- 本地作品集 / 演示项目
- 架构优先（architecture-first）：注重模块边界、数据契约、可测试性
- 确定性的：使用种子数据和模板生成器，无需真实 LLM 或嵌入服务
- 安全约束明确：不自动发送回复（no auto-send 是架构级约束）

## 2. 这不是普通的 RAG 演示

TicketPilot 不是聊天机器人，也不是简单的文档 QA。它与常见 RAG 演示的关键区别：

| 维度 | 普通 RAG 演示 | TicketPilot |
|------|--------------|-------------|
| 输入 | 自由文本问答 | 结构化工单处理流程 |
| 分类 | 无 | 8 类意图 + 8 种风险标记 |
| 知识库 | 单一文档库 | 分层：FAQ / Policy / Case |
| 检索 | 语义搜索 | 关键词 + 向量 + RRF 融合 |
| 生成 | LLM 直接生成 | 模板化的证据引用草稿 |
| 审核 | 无 | 人工审核控制台 + 审计追踪 |
| 评估 | 主观判断 | 确定性离线评估流水线 |

**关键限制：**
- 使用 **fake embeddings**（384 维确定性的哈希向量）— 余弦相似度无语义含义，仅验证管道连通性
- 评估基于 **10 条种子数据**，不反映真实世界性能
- 系统是 **本地演示 / 作品集级别**，不适用于生产

## 3. 核心流程

```
RawTicket（原始消息）
    │
    ▼
标准化 + 实体提取（订单号、客户 ID）
    │
    ▼
意图分类（8 类：退款、换货、账号、投诉、物流、技术、咨询、其他）
    │
    ▼
风险评估（8 种标记 + 严重程度：LOW / MEDIUM / HIGH）
    │
    ▼
分层知识检索（关键词全文搜索 + 向量 HNSW + RRF 融合）
    │
    ├─ EvidenceCandidate（证据候选项）
    ├─ RetrievalTrace（检索追踪）
    │
    ▼
草稿生成（模板驱动，引用证据，不调用 LLM）
    │
    ├─ DraftReply + Citation（草稿回复 + 引用）
    ├─ fallback_reason（无证据时的降级说明）
    │
    ▼
Streamlit 人工审核控制台
    │
    ├─ 操作：批准 / 编辑 / 升级 / 拒绝
    ├─ 输出：ReviewDecision JSONL（审计追踪）
    │
    ▼
离线评估流水线
    ├─ CSV 预测模式：加载样本预测 → 计算指标
    ├─ Pipeline 预测模式：运行完整管道 → 计算指标
    └─ 输出：JSON + Markdown 评估报告
```

## 4. 功能概览

| 模块 | 功能 | 覆盖 |
|------|------|------|
| **工单接收** | 文本标准化、订单号提取 | 单元测试覆盖 |
| **意图分类** | 8 种工单类型（退款、换货、账号、投诉、物流、技术、咨询、其他） | 单元测试覆盖 |
| **风险评估** | 8 种风险标记（投诉、赔偿、法律、账号安全、隐私、政策冲突、低置信度、证据不足）+ 严重程度分级 | 单元测试覆盖 |
| **分层检索** | 关键词全文搜索 + pgvector HNSW + RRF 融合；支持 FAQ / Policy / Case 三种文档类型 | 单元 + 集成测试 |
| **草稿生成** | 模板驱动（零 LLM、零网络调用）；引用证据；无证据时自动降级；高风险标记强制人工审核 | 单元测试覆盖 |
| **人工审核** | Streamlit 控制台；批准 / 编辑 / 升级 / 拒绝操作；ReviewDecision JSONL 审计追踪 | 单元 + 集成测试 |
| **评估流水线** | CSV 预测模式；Pipeline 预测模式；7 项指标（意图准确率、严重度准确率、风险标记 F1、证据召回率等）；JSON + Markdown 报告 | 单元 + 集成测试 85 项 |
| **质量门禁** | Ruff + 单元测试 + 集成测试（跳过=失败）+ 覆盖率≥70% + OpenSpec 验证 | 全自动化 |

**安全约束：**
- **No auto-send**：系统不连接任何发送通道。人工审核的 ReviewDecision 仅写入本地 JSONL 文件。
- **No LLM 依赖**：草稿生成使用确定性模板，不调用任何 LLM API。
- **No 真实嵌入**：向量检索使用 fake embeddings，无语义检索质量。

## 5. 架构概要

```
分层模块架构（自底向上）：

┌─────────────────────────────────────────────┐
│                  入口 / CLI                    │
│  scripts/run_eval.py, streamlit console      │
├─────────────────────────────────────────────┤
│              应用层（Pydantic 数据契约）          │
│  RawTicket → NormalizedTicket → TicketOutput │
│  → DraftReply → ReviewDecision               │
├─────────┬─────────┬──────────┬───────────────┤
│ 接收    │ 分类    │ 风险     │ 检索           │
│ intake/ │ class-  │ risk/    │ retrieval/    │
│         │ ifica-  │          │               │
│         │ tion/   │          │               │
├─────────┴─────────┴──────────┴───────────────┤
│              草稿生成                         │
│  drafting/（模板 + 引用验证器）                 │
├─────────────────────────────────────────────┤
│              审核控制台                       │
│  review/（Streamlit + JSONL 持久化）          │
├─────────────────────────────────────────────┤
│              评估流水线                       │
│  evaluation/（加载器 + 指标 + 报告）           │
├─────────────────────────────────────────────┤
│              存储层                           │
│  PostgreSQL + pgvector + 全文搜索             │
│  Docker Compose（本地开发）                   │
└─────────────────────────────────────────────┘

关键设计决策：
- Fake provider 边界：所有外部依赖（嵌入、LLM）都有 fake 实现，
  确保管道可离线验证
- OpenSpec 变更管理：每个功能变更都有 proposal → design →
  spec → tasks → 验收 → 归档的完整流程
- 质量门禁：自动化验证，不允许跳过集成测试
```

## 6. 快速开始

### 前置依赖

- Python 3.11+
- PostgreSQL 16 + pgvector（可选，仅运行集成测试时需要）
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- Docker（可选，用于启动 PostgreSQL）

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/ticketpilot.git
cd ticketpilot

# 安装依赖（包括开发依赖）
uv sync
```

### 运行测试

```bash
# 运行质量门禁（Ruff + 单元测试 + 集成测试 + 覆盖率 + OpenSpec）
./scripts/run_quality_gate.sh

# 或分步运行：
uv run ruff check .
uv run python -m pytest tests/unit -q
uv run python -m pytest tests/integration/ -v --strict-markers
```

### 运行离线评估

```bash
# CSV 预测模式（加载样本预测文件）
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --predictions data/eval/sample_predictions.csv \
  --out-json reports/eval/evaluation_report.json \
  --out-md reports/eval/evaluation_report.md

# Pipeline 预测模式（运行完整管道生成预测）
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --prediction-mode pipeline \
  --out-json reports/eval/current_pipeline_report.json \
  --out-md reports/eval/current_pipeline_report.md
```

### 运行人工审核控制台

> 需要先启动 PostgreSQL（参见下方）。

```bash
# 启动 PostgreSQL（需要 Docker）
docker compose up -d

# 初始化数据库
alembic upgrade head

# 导入种子知识数据
uv run python scripts/ingest_knowledge.py

# 启动 Streamlit 控制台
uv run streamlit run src/ticketpilot/review/console.py
```

浏览器打开 http://localhost:8501。

### 运行完整管道

```bash
# 需要 PostgreSQL 运行中
uv run python -c "
from ticketpilot.pipeline import run_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(original_text='我要退款，订单号：123456', submitted_at=datetime.utcnow())
output = run_pipeline(ticket)
print(f'意图: {output.classification.intent.value}')
print(f'风险: {[f.value for f in output.risk_assessment.flags]}')
print(f'严重程度: {output.risk_assessment.severity.value}')
"
```

---

> 完整文档导航详见 [docs/README.md](docs/README.md)（后续批次添加）。
> 英文版请见 [README.en.md](README.en.md)。
