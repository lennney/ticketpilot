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
- 确定性的：使用种子数据和模板生成器，无需真实 LLM 或嵌入服务（嵌入层可通过环境变量 opt-in 切换至真实 provider）
- 安全约束明确：不自动发送回复（no auto-send 是架构级约束）

**项目阶段：** Phase 7（MVP 数据与评估）→ Phase 8（混合检索升级）→ Phase 9（评估驱动知识优化）→ Phase 10（排名诊断与细粒度评测）→ Phase 11（证据驱动 LLM 草稿生成）→ Phase 12（Provider 对比）→ Phase 13（Guard-Aware Prompting）→ Phase 14（Guard Taxonomy）→ Phase 15（Chat Support Alignment，已完成）

**新增 Phase 15：** Chat-style AI copilot 多轮对话界面——聊天式 AI 助手 UI，集成 pipeline-to-chat adapter，支持证据面板、风险升级通知、人工审核流程。

**评测指标：** Doc-ID Recall@10 = 91.9%（Phase 10 细粒度诊断）| Provider 对比：Fake/Real 双 Provider 25/25 成功（Phase 12）| 质量门禁：1239 单元 + 146 集成测试，83% 覆盖率

## 2. 这不是普通的 RAG 演示

TicketPilot 不是聊天机器人，也不是简单的文档 QA。它与常见 RAG 演示的关键区别：

| 维度 | 普通 RAG 演示 | TicketPilot |
|------|--------------|-------------|
| 输入 | 自由文本问答 | 结构化工单处理流程 |
| 分类 | 无 | 8 类意图 + 8 种风险标记 |
| 知识库 | 单一文档库 | 分层：FAQ / Policy / Case |
| 检索 | 语义搜索 | 关键词 + 向量 + RRF 融合 |
| 生成 | LLM 直接生成 | 模板化 / 证据约束 LLM 草稿 |
| 审核 | 无 | 人工审核控制台 + 审计追踪 |
| 评估 | 主观判断 | 确定性离线评估流水线 |

**关键限制：**
- 默认使用 **fake embeddings**（384 维确定性的哈希向量）— 余弦相似度无语义含义，仅验证管道连通性。可通过 `EMBEDDING_PROVIDER=openai_compatible` 切换至 DashScope text-embedding-v4 等真实中文嵌入服务
- 评估基于 **101 条合成工单**和 **106 条知识记录**（FAQ=41, Policy=34, Case=31），不反映真实世界性能
- 系统是 **本地演示 / 作品集级别**，不适用于生产
- 当前 intent accuracy (~53%) 和 severity accuracy (~54%) 反映规则组件的确定性行为，不是生产级效果指标

## 3. 核心流程

**两条入口：** Chat-style AI Copilot（多轮对话 UI）或 Pipeline API。

**Chat-style AI Copilot 流程：**
```
用户发送客服消息（Chat UI）
    │
    ▼
多轮对话上下文管理（保持会话历史）
    │
    ▼
Pipeline-to-Chat Adapter（管道输出 → Chat 消息渲染）
    │
    ▼
AI 草稿回复（证据引用 + ClaimGuard 状态）
    │
    ├─ 证据面板（Sidebar 显示引用来源）
    ├─ 风险升级通知（高风险时突出显示）
    │
    ▼
人工审核流程（内嵌于 Chat）
    │ 批准 / 编辑 / 升级 / 拒绝
    │
    ▼
ReviewDecision JSONL（审计追踪）
```

**Pipeline 流程：**
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
    ├─ RetrievalTrace（完整检索追踪）
    │
    ▼
草稿生成（模板驱动 / LLM 证据约束，引用证据）
    │
    ├─ DraftReply + Citation（草稿回复 + 引用）
    ├─ ClaimGuard（声明校验 + 禁止承诺检测）
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
| **Chat UI（新增）** | Chat-style AI Copilot 多轮对话界面；Streamlit 聊天式 UI；证据面板侧边栏；风险升级通知；内嵌人工审核流程 | 单元测试覆盖 |
| **工单接收** | 文本标准化、订单号提取 | 单元测试覆盖 |
| **意图分类** | 8 种工单类型（退款、换货、账号、投诉、物流、技术、咨询、其他） | 单元测试覆盖 |
| **风险评估** | 8 种风险标记（投诉、赔偿、法律、账号安全、隐私、政策冲突、低置信度、证据不足）+ 严重程度分级 | 单元测试覆盖 |
| **分层检索** | 关键词全文搜索 + pgvector HNSW + RRF 融合；支持 FAQ / Policy / Case 三种文档类型；支持 DashScope text-embedding-v4 等真实嵌入 provider opt-in | 单元 + 集成测试 |
| **真实嵌入对比** | Fake 384-d vs Real 1024-d 离线检索对比：Top-1 31.7% → 42.6%，MRR 0.4114 → 0.4913 | 完整评测覆盖 |
| **评估驱动优化** | 错例 8 类分类法 → 24 个知识缺口 → 11 条定向补充 → Provider Identity Gate | 完整评测覆盖 |
| **细粒度检索评测** | Doc-ID 证据粒度评测：Recall@10 达 91.9%，确认 78% wrong cases 为评测粒度问题 | 86 用例标注 |
| **草稿生成** | 模板驱动 / LLM 证据约束（FakeLLMProvider + PromptBuilder + ClaimGuard）；无证据时自动降级；高风险标记强制人工审核 | 单元测试覆盖 |
| **人工审核** | Streamlit 控制台；批准 / 编辑 / 升级 / 拒绝操作；ReviewDecision JSONL 审计追踪；Chat 内嵌审核流程 | 单元 + 集成测试 |
| **评估流水线** | CSV 预测模式；Pipeline 预测模式；7 项指标（意图准确率、严重度准确率、风险标记 F1、证据召回率等）；JSON + Markdown 报告 | 101 条工单评估覆盖 |
| **质量门禁** | Ruff + 单元测试 + 集成测试（跳过=失败）+ 覆盖率≥70% + OpenSpec 验证 | 全自动化 |

**安全约束：**
- **No auto-send**：系统不连接任何发送通道。人工审核的 ReviewDecision 仅写入本地 JSONL 文件。
- **No LLM 依赖**：草稿生成使用确定性模板，不调用任何 LLM API（LLM provider 接口已定义，仅用于离线管道验证）。
- **Fake embedding 默认**：向量检索默认使用 fake embeddings。真实嵌入需通过 `.env.local` 环境变量显式 opt-in。

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
│  drafting/（模板 + LLM provider + 引用验证器）  │
├─────────────────────────────────────────────┤
│              审核控制台                       │
│  review/（Streamlit + JSONL 持久化）          │
├─────────────────────────────────────────────┤
│              评估流水线                       │
│  evaluation/（加载器 + 指标 + 报告 + 检索对比） │
├─────────────────────────────────────────────┤
│              存储层                           │
│  PostgreSQL + pgvector + 全文搜索             │
│  Docker Compose（本地开发）                   │
└─────────────────────────────────────────────┘

关键设计决策：
- Fake provider 边界：所有外部依赖（嵌入、LLM）都有 fake 实现，
  确保管道可离线验证。真实 provider 通过环境变量 opt-in
- OpenSpec 变更管理：每个功能变更都有 proposal → design →
  spec → tasks → 验收 → 归档的完整流程
- Provider Identity Gate：运行时验证实际使用的 provider 身份，
  防止配置静默回退导致指标误导
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
git clone https://github.com/lennney/ticketpilot.git
cd ticketpilot

# 安装依赖（包括开发依赖）
uv sync
```

### 运行测试

```bash
# 运行质量门禁（Ruff + 单元测试 + 集成测试 + 覆盖率 + OpenSpec）
bash scripts/run_quality_gate.sh

# 或分步运行：
uv run ruff check .
uv run pytest tests/unit -q
uv run pytest tests/integration/ -v --strict-markers
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

### 使用真实嵌入（可选）

```bash
# 编辑 .env.local 配置
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
EMBEDDING_API_KEY=your_key_here

# 重建嵌入索引
uv run python scripts/rebuild_embeddings.py --confirm
```

### 运行人工审核控制台

> 需要先启动 PostgreSQL（参见下方）。

```bash
# 启动 PostgreSQL（需要 Docker）
docker compose up -d
# 数据库迁移会在首次启动时通过 db/migrations/ 自动执行

# 验证种子知识数据（本地 chunking，无需数据库）
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

> 完整文档导航详见下文第 7 节。
> 英文版请见 [README.en.md](README.en.md)。

---

## 7. 文档导航

| 目录 | 说明 |
|------|------|
| `docs/technical/` | 技术设计文档：系统架构、数据契约、检索设计、风险规则、质量门禁、评估流水线、Provider Identity Gate 等 |
| `docs/demo/` | 演示指南：三条演示线的分步说明和示例工单；三个强 demo 场景文档（退款投诉、隐私/账号异常、发票/支付争议） |
| `docs/limitations.md` | 当前版本已知限制（数据、嵌入、评估、UI 等） |
| `docs/github_release_checklist.md` | GitHub 发布前检查清单 |
| `docs/development_trace/` | 各阶段开发过程记录和项目复盘 |
| `docs/portfolio/` | 作品集材料：项目案例（中/英）、演示脚本、面试要点、限制与路线图、Phase 7–10 阶段快照 |
| `docs/skills/` | Claude Code 技能文档：批量实施、质量门禁验收、检索评估、安全开发等 |
| `docs/prompts/` | 可复用的提示词模板 |
| `docs/audits/` | 项目审计报告 |
| `docs/changelog.md` | 变更日志 |
| `openspec/` | OpenSpec 规范驱动开发：所有变更的 proposal、design、spec、tasks |
| `reports/eval/` | 评估报告输出（JSON + Markdown） |
| `reports/retrieval/` | 检索对比评测报告（Fake vs Real，Phase 9–10 诊断报告） |

## 8. 项目演进

### Phase 7 — MVP Evidence Pack（已完成）
- 评测数据集从 10 条扩展到 **101 条合成工单**
- 知识库从 36 条扩展到 **95 条记录**（FAQ=40, Policy=30, Case=25）
- 新增发票/支付领域、7 条多意图工单、5 条边界工单
- 建立确定性离线评测流水线（CSV + Pipeline 双模式）
- 3 个强 demo 场景文档

### Phase 8 — Real Retrieval Upgrade（已完成）
- 接入 DashScope text-embedding-v4（1024-d），保留 FakeEmbeddingProvider 作为默认
- 建立 EmbeddingConfig + provider factory 切换机制
- 在固定数据集下完成 Fake 384-d vs Real 1024-d 对比
  - Top-1 hit rate: 31.7% → 42.6%（+10.9%）
  - MRR: 0.4114 → 0.4913（+0.0799）
- Wrong-case analysis 发现 41 个错例均为 missing_doc_type，瓶颈在知识覆盖而非 embedding 质量

### Phase 9 — Evaluation-Driven Knowledge Optimization（已完成）
- 41 个 wrong cases → 8 类故障分类法 → 24 个知识缺口
- 定向补充 **11 条 P0 知识记录**（总记录从 95→106）
- 发现 **Provider Identity Gate** 问题：`load_dotenv()` 未被调用导致所有评测静默回退到 fake provider
- 修复后真实评测 P0 hit rate 达 75.0%，Top-1 提升 2.0%
- 错例数不变（仍为 41），瓶颈从知识覆盖迁移至检索排序

### Phase 10 — Hybrid Retrieval Ranking Diagnosis（已完成）
- 设计 8 类检索瓶颈分类法，三层分层诊断（keyword / vector / fused）
- 将 doc-level golden labels 从 14 扩展到 **86 个评测用例**
- 评测单位从 doc_type 细化为 doc_id
- **Doc-ID Recall@10 达 91.9%**，较 doc-type 指标提升 32.5 个百分点
- 32/41 个 doc-type wrong cases 被重新归类为 doc_id-found
- 识别 7 个 zero-hit 案例（query expansion 候选）和 32 个 partial-hit 案例（fusion ranking 候选）

### Phase 11 — Evidence-Grounded LLM Draft Generation（已完成）
- LLM provider 抽象接口 + FakeLLMProvider 确定性实现（无 API 依赖）
- Evidence-grounded prompt builder（证据约束 + 安全规则 + 输出格式规范）
- DraftCitationValidationResult 和 validate_draft_citations()（引用 ID 结构校验）
- ClaimGuard（5 层检查：声明覆盖率、无证据声明、禁止承诺、证据充足性、风险感知）
- DraftGenerationResult + generate_draft() 管线串联所有组件
- Human review console 更新（15 个审计字段 + guard 状态展示）
- 离线草稿评估指标（8 项确定性指标，引用精确度=100%，claim guard 通过率=0%，FakeLLMProvider 仅测工作流机制）
- 8 层安全架构：prompt 约束 → 引用验证 → ClaimGuard → 风险感知 → 人审传播 → no-auto-send → fake 默认 → provider 追踪

### Phase 12 — Provider Comparison（已完成）
- 运行 FakeLLMProvider vs OpenAICompatibleProvider (DeepSeek) 离线对比
- 25 个 fixture cases 对比结果：两 provider 产生完全相同的人审触发模式
- 证实安全规则（CitationValidator, ClaimGuard）与 provider 无关

### Phase 13 — Guard-Aware Prompting（已完成）
- Guard-aware structured prompt 指导 LLM 在引用中包含 `[chunk_id]` 标记
- Real provider (deepseek-v4-pro) guard pass rate: **84%**（vs baseline 4%）
- Citation validation pass rate: 76%（vs baseline 12%）
- Safe fallback rate: 84%（当缺乏证据时保守引用）

### Phase 14 — Guard Taxonomy（已完成）
- 建立安全护栏分类体系：safety foundation, escalation acknowledgment, evidence grounding
- 8 层安全架构文档化，明确各层护栏职责边界
- 暂停迭代以现固安全基础

### Phase 15 — Chat Support Alignment（已完成）
- Chat-style AI Copilot 多轮对话界面
- Pipeline-to-Chat Adapter（管道输出 → Chat 消息渲染）
- Evidence panel（证据面板侧边栏）
- Risk escalation notification（风险升级通知）
- Human review flow embedded in chat（人工审核流程内嵌于 Chat）
- 产品叙事从 "guard architecture" 转向 "chat-style AI copilot"（电商客服场景）

## 9. 当前限制

- **本地演示 / 作品集级别**：本项目是架构优先的功能演示，不是生产级客服系统。
- **种子数据**：知识库含 106 条种子记录（FAQ=41, Policy=34, Case=31），评估含 101 条合成工单。不反映真实企业数据规模和多样性。
- **Pipeline 指标说明**：当前 intent accuracy (~53%) 和 severity accuracy (~54%) 反映规则组件的确定性行为。这些指标说明了评测体系已建立，不能被包装为生产级效果。no-auto-send compliance=100% 是架构约束，不是自动回复质量。详见 [docs/limitations.md](docs/limitations.md)。
- **默认 Fake embeddings**：向量检索默认使用确定性 fake embeddings（384 维 SHA-256 哈希向量），余弦相似度无语义含义。真实嵌入（DashScope text-embedding-v4）需通过环境变量 opt-in。
- **检索语义质量未验证**：Doc-ID Recall@10 = 91.9% 仅验证管道连通性，Pipeline verification only — no semantic retrieval quality。
- **Phase 11 草稿生成进行中**：LLM provider 接口和 FakeLLMProvider 已完成，真实 provider 集成和离线草稿评估指标待完成。
- **不自动发送回复（no auto-send）**：详见第 10 节。
- **Chat UI MVP 状态**：Chat-style AI Copilot 是 MVP 级别的多轮对话 UI，集成 pipeline-to-chat adapter、证据面板、风险升级通知和内嵌人工审核。功能在迭代完善中。
- **Streamlit 控制台**：是 MVP 级别的人工审核 UI，非生产前端。
- **评估报告**：基于本地确定性种子数据，不反映真实世界基准性能。
- **无多用户支持**：当前无身份验证或权限模型。

## 10. 路线图

| 方向 | 说明 | 状态 |
|------|------|------|
| **Phase 11 收尾** | 完成 LLM provider 实现、ClaimGuard、离线草稿评估 | 已完成 |
| **Phase 12** | Provider 对比，证实安全规则 provider-agnostic | 已完成 |
| **Phase 13** | Guard-Aware Prompting，84% pass rate | 已完成 |
| **Phase 14** | Guard Taxonomy，安全基础现固 | 已完成 |
| **Phase 15** | Chat Support Alignment，Chat UI MVP | 已完成 |
| **检索排序优化** | 基于 Phase 10 诊断结果优化 RRF 权重、query expansion | 待规划 |
| **真实数据包** | 扩展知识库和评估数据集至数百条真实风格数据 | 待规划 |
| **扩展评估数据集** | 50+ 条工单，覆盖边缘情况和组合场景 | 待规划 |
| **追踪持久化** | Langfuse 或其他追踪系统的可选集成 | 待规划 |
| **认证 / 多用户** | Review 控制台的登录和角色模型 | 待规划 |
| **生产部署** | Docker 化部署、CI/CD、监控 | 待规划 |

## 11. 安全边界：不自动发送回复（No Auto-Send）

**这是架构级约束，不是可配置选项。**

- 管道生成的回复草稿是 **待审核的建议**，不是已发送的客服回复。
- 人工审核控制台的操作（批准/编辑/升级/拒绝）仅写入本地 `ReviewDecision` JSONL 文件，**不连接任何发送通道**。
- 以下情况**必须**经过人工审核：
  - 高风险标记（法律风险、赔偿要求、隐私泄露等）
  - 检索无证据（fallback 模式）
  - 草稿含未支持的声明（根据政策规则的检测）
  - ClaimGuard 校验失败
- 当前版本中不存在任何自动发送客户回复的 API、消息队列或 Webhook。

---

*TicketPilot — 本地演示 / 作品集项目*
