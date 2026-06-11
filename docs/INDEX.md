# TicketPilot 文档索引

> 给 AI Agent 和人共同使用的导航。每个目录下的文件按"新来者友好"排序——优先读前面的。

---

## 根目录文档

| 文件 | 阅读优先级 | 说明 |
|------|-----------|------|
| `README.md` | ⭐⭐⭐⭐⭐ | 项目入口、功能概览、快速开始 |
| `AGENTS.md` | ⭐⭐⭐⭐⭐ | AI Agent 工作准则。**每次启动本项目前必须读取** |
| `CHANGELOG.md` | ⭐⭐⭐⭐ | 迭代日志，按阶段记录每个版本的功能变更和指标 |
| `pyproject.toml` | ⭐⭐ | 依赖管理唯一来源。`uv sync` 即用 |

---

## docs/technical/ — 技术文档

| 文件 | 阅读优先级 | 说明 | 最后更新 |
|------|-----------|------|---------|
| `retrieval_architecture.md` | ⭐⭐⭐⭐⭐ | **检索架构** — FTS/HNSW/RRF/Re-ranker 端到端链路 | 2026-06-11 ✅ |
| `ARCHITECTURE.md` | ⭐⭐⭐⭐ | 整体架构概览 | Pre-06 ⚠️ 可能陈旧 |
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
# 知识库数据
data/knowledge/           # 原始种子数据 (JSON)
data/eval/                # 评测数据集 (CSV)

# 核心源码
src/ticketpilot/classification/    # 意图分类
src/ticketpilot/retrieval/         # 检索 (FTS + Vector + RRF)
src/ticketpilot/drafting/          # 草稿生成
src/ticketpilot/evaluation/        # 评测流水线
src/ticketpilot/optimizer/         # 自迭代优化器
src/ticketpilot/quality/           # 质量评分别器
src/ticketpilot/confidence/        # 置信度路由

# 测试
tests/unit/               # 单元测试 (核心)
```
