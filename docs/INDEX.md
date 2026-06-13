# TicketPilot 文档索引

> 给 AI Agent 和人共同使用的导航。每个目录下的文件按"新来者友好"排序——优先读前面的。

---

## 根目录文档

| 文件 | 阅读优先级 | 说明 |
|------|-----------|------|
| `README.md` | ⭐⭐⭐⭐⭐ | 项目入口、功能概览、快速开始 |
| `AGENTS.md` | ⭐⭐⭐⭐⭐ | AI Agent 工作准则。**每次启动本项目前必须读取** |
| `CHANGELOG.md` | ⭐⭐⭐⭐ | 迭代日志，按阶段记录每个版本的功能变更和指标 |
| `.gitleaks.toml` | ⭐⭐⭐ | gitleaks 项目级白名单（测试占位符豁免） |
| `pyproject.toml` | ⭐⭐ | 依赖管理唯一来源。`uv sync` 即用 |

---

## docs/technical/ — 技术文档

| 文件 | 阅读优先级 | 说明 | 最后更新 |
|------|-----------|------|---------|
| `retrieval_architecture.md` | ⭐⭐⭐⭐⭐ | **检索架构** — FTS/HNSW/RRF/Re-ranker 端到端链路 | 2026-06-11 ✅ |
| `ARCHITECTURE.md` | ⭐⭐⭐⭐ | **整体架构概览** — 全部模块文档（含 chat、agent、optimizer 等） | 2026-06-12 ✅ |
| `data_contracts.md` | ⭐⭐⭐ | 数据模型、知识库 schema、chunk schema | Pre-06 ⚠️ |
| `quality_gate.md` | ⭐⭐⭐ | 质量门禁配置 | Pre-06 ⚠️ |
| `evaluation_pipeline_performance_analysis.md` | ⭐⭐ | 评测流水线性能分析 | 2026-06-10 ✅ |
| `validation_policy.md` | ⭐⭐ | OpenSpec 验证策略 | ✅ |
| `ai_development_harness.md` | ⭐⭐ | AI 开发 Harness | ✅ |

> ⚠️ **Stale**: 标注 ⚠️ 的文档在 Scoring Classifier / Phase 16 后未更新。修改相关代码时优先更新。

---

## docs/product/ — 产品设计文档

| 文件 | 说明 |
|------|------|
| `2026-06-10-draft-quality-gate.md` | 草稿质量门禁设计（双重路由） |
| `2026-06-11-optimizer-analysis.md` | 自迭代优化器首次运行分析报告 |

---

## docs/plans/ — 实施计划

每个阶段执行前编写，格式为 `YYYY-MM-DD-feature-name.md`。

> **过期清理**: 已归档阶段（`CHANGELOG.md` 中有记录的）的计划文件可以删除或归档到 `plans/archive/`。

---

## docs/portfolio/ — 作品集材料

| 文件 | 说明 |
|------|------|
| `index.md` | 作品集主页 |
| `ITERATION_SUMMARY.md` | 迭代总结（面试用） |
| `METRICS.md` | 指标演变 |
| `DEMO.md` | 演示指南 |
| `interview_talking_points.md` | 面试话术 |
| `product_portfolio_material_pack.md` | 完整材料包 |

---

## docs/harness/ — Harness 工作流

| 文件 | 说明 |
|------|------|
| `PHASE_LOOP.md` | 阶段执行工作流（Phase Loop） |
| `PROJECT_CONTEXT.md` | 项目上下文 |
| `CONTROLLER_HARNESS_PRACTICE.md` | Controller 实践 |
| `skills/` | 可复用的 skill 模板 |

---

## 文档更新约定

见 `MAINTENANCE.md` → [文档维护规则](MAINTENANCE.md#文档维护)。

---

## 常用路径速查

```bash
# ═══════════════════════════════════════════════════════
# 数据目录
# ═══════════════════════════════════════════════════════
data/knowledge/              # 原始种子数据 (JSON)
data/eval/                   # 评测数据集 (CSV)
data/skills/                 # 技能库 (library.json)

# ═══════════════════════════════════════════════════════
# 核心数据模型
# ═══════════════════════════════════════════════════════
src/ticketpilot/schema/              # 核心数据模型 (Ticket, Evidence)
src/ticketpilot/schema/ticket.py     #   RawTicket, NormalizedTicket, ClassificationResult, RiskAssessment, TicketOutput
src/ticketpilot/schema/evidence.py   #   EvidenceCandidate (检索结果 → 管道输出的桥梁)

# ═══════════════════════════════════════════════════════
# 核心管道 (6 层)
# ═══════════════════════════════════════════════════════
src/ticketpilot/intake/              # Layer 1: 文本规范化 + 实体抽取
src/ticketpilot/classification/      # Layer 2: 意图分类 (8 类)
src/ticketpilot/risk/                # Layer 3: 风险评估 (8 标记)
src/ticketpilot/retrieval/           # Layer 4: 混合检索 (FTS + Vector + RRF)
src/ticketpilot/drafting/            # Layer 5: 草稿生成 (DraftAgent + FakeLLM + CitationValidator)
src/ticketpilot/review/              # Layer 6: 人工审核控制台

# ═══════════════════════════════════════════════════════
# Chat 模块 (多轮对话)
# ═══════════════════════════════════════════════════════
src/ticketpilot/chat/                # 多轮对话界面
src/ticketpilot/chat/schemas.py      #   ChatSession, ChatContext, ChatMessage, ChatState, ChatDisplay
src/ticketpilot/chat/adapter.py      #   ticket_output_to_chat_display() — 管道输出 → 聊天 UI
src/ticketpilot/chat/app.py          #   Streamlit 多轮聊天 UI
src/ticketpilot/chat/pages/          #   多页面路由

# ═══════════════════════════════════════════════════════
# Agent 模块 (确定性执行框架)
# ═══════════════════════════════════════════════════════
src/ticketpilot/agent/               # Agent 基础设施
src/ticketpilot/agent/planner.py     #   确定性任务规划器 (关键词模板匹配)
src/ticketpilot/agent/loop.py        #   执行循环 (plan → tools → trace)
src/ticketpilot/agent/tools.py       #   5 个工具包装器 + request_human_input
src/ticketpilot/agent/registry.py    #   工具注册表 (ToolRegistry)
src/ticketpilot/agent/memory.py      #   WorkingMemory + EpisodicMemory
src/ticketpilot/agent/trace.py       #   AgentTrace (追加式事件记录)
src/ticketpilot/agent/state_store.py #   AgentStateStore (SQLite 持久化, 支持 pause/resume)
src/ticketpilot/agent/skill_loader.py#   业务技能加载器 (skills/runtime/)
src/ticketpilot/agent/error_compaction.py # 异常压缩为简短摘要
src/ticketpilot/agent/schemas.py     #   AgentRun, AgentPlan, AgentEvent 等数据合约

# ═══════════════════════════════════════════════════════
# 置信度 / 降级 / 质量
# ═══════════════════════════════════════════════════════
src/ticketpilot/confidence/          # 多维度置信度评分 (4 信号加权)
src/ticketpilot/confidence/scorer.py #   ConfidenceScorer — 输出 ConfidenceBreakdown (HIGH/MEDIUM/LOW/CRITICAL)
src/ticketpilot/degradation/         # 响应路由 (置信度 + 质量双重门控)
src/ticketpilot/degradation/router.py#   DegradationRouter — AUTO_SEND / CAUTIOUS / REVIEW / ESCALATION
src/ticketpilot/quality/             # 草稿质量评分 (4 维度)
src/ticketpilot/quality/scorer.py    #   compute_draft_quality() — forbidden_promise + citation + claim_guard + evidence_coverage

# ═══════════════════════════════════════════════════════
# 反馈 / 校准
# ═══════════════════════════════════════════════════════
src/ticketpilot/feedback/            # 人工反馈收集 + 校准
src/ticketpilot/feedback/collector.py#   FeedbackCollector — 记录审核结果到 JSONL
src/ticketpilot/feedback/calibrator.py # CalibrationCurve + IsotonicCalibrator (PAV 算法) + ReliabilityDiagram
src/ticketpilot/feedback/threshold_advisor.py # ThresholdAdvisor — 建议最优置信度阈值

# ═══════════════════════════════════════════════════════
# 自迭代优化器
# ═══════════════════════════════════════════════════════
src/ticketpilot/optimizer/           # 自迭代优化引擎 (自我改进提示和规则)
src/ticketpilot/optimizer/engine.py  #   OptimizationEngine — evaluate → diagnose → fix → verify → commit
src/ticketpilot/optimizer/diagnostics.py # DiagnosticsEngine — 分析评测结果找失败模式
src/ticketpilot/optimizer/evaluator.py   # OptimizerEvaluator — 跑管道并计算指标
src/ticketpilot/optimizer/fixer.py   #   Fixer — 应用修复 + 回滚
src/ticketpilot/optimizer/verifier.py    # 增量验证 (只重评受影响用例)
src/ticketpilot/optimizer/llm_reviewer.py # LLM 审核关键词变更
src/ticketpilot/optimizer/tradeoff.py    # 关键词变更的跨用例影响分析
src/ticketpilot/optimizer/git_ops.py #   Git 提交 (接受的修复)
src/ticketpilot/optimizer/history.py #   优化历史记录 (JSONL)
src/ticketpilot/optimizer/reporter.py    # 优化报告生成

# ═══════════════════════════════════════════════════════
# 实验 / 评测
# ═══════════════════════════════════════════════════════
src/ticketpilot/experiment/          # A/B 实验框架
src/ticketpilot/experiment/config.py #   ExperimentConfig (control/treatment 配置)
src/ticketpilot/experiment/runner.py #   ExperimentRunner — 对比两组配置的指标
src/ticketpilot/experiment/reporter.py # ExperimentReport — Markdown 对比表

src/ticketpilot/evaluation/          # 离线评测流水线
src/ticketpilot/evaluation/schemas.py #  EvalTicket, GoldenExpectation, EvalPrediction, EvaluationMetrics
src/ticketpilot/evaluation/metrics.py #  指标计算 (intent accuracy, risk flag F1 等)
src/ticketpilot/evaluation/draft_metrics.py # 草稿评测指标 (citation precision, evidence coverage)
src/ticketpilot/evaluation/nli_scorer.py   # NLI 断言验证
src/ticketpilot/evaluation/pipeline_predictions.py # 管道预测运行器
src/ticketpilot/evaluation/agent_eval.py   # Agent 评测
src/ticketpilot/evaluation/loaders.py      # CSV 加载器
src/ticketpilot/evaluation/reporting.py    # 报告生成

# ═══════════════════════════════════════════════════════
# 提示词 / 技能
# ═══════════════════════════════════════════════════════
src/ticketpilot/prompts/             # 版本管理的提示词模板
src/ticketpilot/prompts/manager.py   #   PromptManager — 注册、获取、渲染、版本列表
src/ticketpilot/prompts/templates/   #   Markdown 模板 (refund/technical/logistics/complaint/default)

src/ticketpilot/skills/              # 技能库 + 生成器 + 反思器
src/ticketpilot/skills/schema.py     #   SkillPattern, SkillLibrary
src/ticketpilot/skills/loader.py     #   load_skill_library(), select_relevant_skills()
src/ticketpilot/skills/generator.py  #   generate_skill_from_success() — 从成功案例自动生成技能
src/ticketpilot/skills/reflector.py  #   reflect_on_draft() — 草稿 vs 技能最佳实践检查

# ═══════════════════════════════════════════════════════
# 追踪 / 来源
# ═══════════════════════════════════════════════════════
src/ticketpilot/tracing/             # 全链路可追溯性
src/ticketpilot/tracing/provenance.py #  ClaimProvenance, ResponseProvenance — 答案 → 引用 → 知识块 → 文档
src/ticketpilot/tracing/store.py     #   ProvenanceStore — 按 response_id 或 chunk_id 查询

# ═══════════════════════════════════════════════════════
# API / 触发器 / 仪表板
# ═══════════════════════════════════════════════════════
src/ticketpilot/api/                 # API 层
src/ticketpilot/api/streaming.py     #   SSE 流式端点 (FastAPI, /api/chat/stream)

src/ticketpilot/triggers/            # 管道触发器
src/ticketpilot/triggers/webhook.py  #   HTTP Webhook 接收器 (POST /webhook/ticket)
src/ticketpilot/triggers/cli.py      #   命令行触发器

src/ticketpilot/dashboard/           # Streamlit 仪表板
src/ticketpilot/dashboard/app.py     #   入口
src/ticketpilot/dashboard/metrics_page.py # 指标可视化页面

src/ticketpilot/pipeline.py          # 管道组合入口 (intake_risk_pipeline, post_process)

# ═══════════════════════════════════════════════════════
# 检索子模块 (详细)
# ═══════════════════════════════════════════════════════
src/ticketpilot/retrieval/pipeline.py      # 混合检索主流程
src/ticketpilot/retrieval/keyword_search.py # PostgreSQL FTS + LIKE 回退
src/ticketpilot/retrieval/vector_search.py  # pgvector HNSW 向量搜索
src/ticketpilot/retrieval/rrf.py            # Reciprocal Rank Fusion
src/ticketpilot/retrieval/reranker.py       # 重排序器
src/ticketpilot/retrieval/hybrid_reranker.py # 混合重排序
src/ticketpilot/retrieval/query_builder.py  # 查询构建 (中文意图 + 风险标记)
src/ticketpilot/retrieval/query_expander.py # 查询扩展
src/ticketpilot/retrieval/result_merger.py  # 结果合并
src/ticketpilot/retrieval/retrieve_evidence.py # 证据检索入口
src/ticketpilot/retrieval/traces.py         # RetrievalTrace 数据模型
src/ticketpilot/retrieval/truncation.py     # 文本截断
src/ticketpilot/retrieval/embedding_config.py # 嵌入配置
src/ticketpilot/retrieval/embedding_metadata.py # 嵌入元数据
src/ticketpilot/retrieval/schema/           # 检索数据模型
src/ticketpilot/retrieval/schema/knowledge.py # DocType, KnowledgeChunk
src/ticketpilot/retrieval/schema/retrieval.py # FusedResult, RetrievalTrace
src/ticketpilot/retrieval/schema/seeds.py   # 种子数据 schema
src/ticketpilot/retrieval/providers/        # 嵌入提供商
src/ticketpilot/retrieval/providers/fake_embedding.py    # FakeEmbeddingProvider (确定性伪随机)
src/ticketpilot/retrieval/providers/local_embedding.py   # LocalEmbeddingProvider
src/ticketpilot/retrieval/providers/openai_compatible.py # OpenAICompatibleProvider (可选)
src/ticketpilot/retrieval/db/               # 数据库操作
src/ticketpilot/retrieval/db/connection.py  # PostgreSQL 连接
src/ticketpilot/retrieval/db/seeding.py     # 种子数据加载

# ═══════════════════════════════════════════════════════
# 配置 / 守卫
# ═══════════════════════════════════════════════════════
src/ticketpilot/config/              # 全局配置 (CONFIDENCE_HIGH/MEDIUM/LOW 等阈值)
src/ticketpilot/guardrails/          # 守卫模块

# ═══════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════
tests/unit/                  # 单元测试 (核心)
tests/integration/           # 集成测试 (需要 PostgreSQL)
tests/fixtures/              # 测试夹具

# ═══════════════════════════════════════════════════════
# 报告 / 脚本
# ═══════════════════════════════════════════════════════
reports/                     # 评测报告、优化日志
reports/optimization/        # 优化器 debug_log.jsonl
scripts/                     # 脚本 (质量门禁等)
```
