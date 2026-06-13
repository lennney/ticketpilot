# Changelog

> **格式**: 基于 [Keep a Changelog](https://keepachangelog.com/)，按阶段组织。
> **维护规则**: 见 `docs/MAINTENANCE.md#changelog`。每个阶段合并前必须更新本文件。
> **版本**: 语义化版本，阶段作为次版本。

---

## [Unreleased]

### Added
- tradeoff.py: 关键词候选混淆簇模拟（TP/FP/Net Gain 量化）
- llm_reviewer.py: OpenAI-compatible LLM 审批替代硬性回滚
- 54 个新测试（tradeoff + llm_reviewer + keyword_search + engine）
- `.gitleaks.toml`: gitleaks 项目级白名单（测试占位符豁免）

### Changed
- engine.py: 集成 tradeoff 分析 + llm_reviewer 到优化器循环
- diagnostics.py: jieba 因果特征分析增强
- evaluator.py: 支持扩展评测数据集 + 混淆分析
- 评测数据扩展: golden_expectations +503/-503

### Security
- **修复**: `run_optimizer_with_llm.py` 中硬编码 API key 移除，改为环境变量读取
- **新增**: CI secrets-scan job（gitleaks-action@v2，每个 push/PR 自动执行）
- **新增**: 全局 gitleaks pre-commit + pre-push hook（三层秘密防护）
- **更新**: AGENTS.md §6 — Secret Rules 重写（含防护层说明 + 事件响应流程）

### Docs
- AGENTS.md §6: Secret Rules 扩展为完整防护章节

---

## [0.16.0] — 2026-06-11 — Scoring Classifier + Keyword Trade-off Engine

> **Git:** `6bcbbfc` | **Tests:** 1,574 ✅ / 14 known | **Ruff:** clean

### Added
- `ScoringIntentClassifier`: 替代硬 first-match-wins，per-intent 关键词评分+阈值门控
- jieba FTS 分词 + 42 停用词过滤 + `%` SQL 转义
- 排除规则 (`IntentRule.exclusions`) — 解决 first-match-wins 误分类
- 编码安全防线（3 层 UTF-8 防御）
- 增量评测 (`run_partial_evaluation()` → 6min → 30s)
- 最佳状态追踪 + 3 轮无改进提前终止

### Fixed
- `UnicodeDecodeError` in keyword_search (psycopg3 LIKE)
- `submitted_at` 使用 `datetime.fromisoformat()` 确保可复现

### Metrics
| 指标 | 基线 | 备注 |
|------|------|------|
| Intent accuracy | 69.3% | v1 classifier |
| Severity accuracy | 57.4% | |
| Risk flag F1 | 34.7% | 瓶颈 (22 keywords, 6 flags) |
| Composite | 0.6125 | 加权综合分 |

---

## [0.15.0] — 2026-06-10 — Chat UI + Controller Harness + 跨境电商

> **Git:** `a7e473d` | **Tests:** ~1,700 | **Coverage:** 83%

### Added
- Streamlit Chat 演示 UI（multi-turn 上下文）
- Pipeline-to-chat 适配器（证据映射+上下文助手）
- Controller Harness master skill + OpenSpec 插件
- 风险升级显示、证据面板、复核队列链接
- 跨境电商 DraftAgent + Chunking + 知识库 144→340 chunks
- BM25 tsvector + ts_rank_cd 优化
- Re-ranking 框架（embedding tiebreaker，保留 RRF）
- Self-reflection loop（幻觉检测和修正）
- 置信度路由 — 分级审核
- DashScope text-embedding-v3 接入
- Agent Harness 三阶段：追踪+评估+护栏
- Docker 部署、Multi-Agent 架构
- 草稿质量门禁：`DraftQualityScorer` + 双重路由

### Changed
- 意图分类 80%→100%（强指示词+支付关键词优化）
- README metrics 更新：1,239 unit tests, 83% coverage
- 知识库 1,505 chunks / ~2,360 原始文档

---

## [0.14.0] — 2026-06-09 — Guard Architecture

> **Git:** `0ec8c67`

- `GuardFailureType` taxonomy（3 大类: hallucination, risk, escalation）
- 安全升级检测 + 人工复核确认 + per-failure-type pass rates

---

## [0.13.0] — 2026-06-08 — Extended Eval Metrics

> **Git:** `0e050d6`

- Extended draft evaluation metrics via comparison runner
- Real provider extended comparison
- Guard-aware provider prompting experiment

---

## [0.12.0] — 2026-06-07 — LLM Provider Comparison

> **Git:** `bb88d9a`

- OpenAI-compatible LLM provider for offline comparison
- Fake vs Real provider evaluation
- Agent error memory system

---

## [0.11.0] — 2026-06-06 — Evidence-Grounded LLM Draft

> **Git:** `ac1b01a`

- Draft schema + LLM provider interface + Fake provider
- Evidence-grounded prompt builder
- Citation validation + Unsupported-claim guard
- Offline draft generation metrics

---

## [0.10.0] — 2026-06-05 — Hybrid Retrieval Diagnosis

> **Git:** `199fbf2` | **Eval tickets:** 86 doc-level golden labels

- Retrieval trace readiness audit + P0 ranking diagnosis
- Doc-level golden metrics + real pipeline eval
- AI Development Harness + ChatGPT controller harness

---

## [0.9.0] — 2026-06-04 — Knowledge Coverage Expansion

> **Git:** `b9c2ed8`

- Wrong-case taxonomy + knowledge gap map
- 11 P0 records, evaluation rerun (knowledge coverage impact)
- Real embedding provider identity audit
- 54 修复 skipped integration tests (WSL DLL + dimension)

---

## [0.8.0] — 2026-06-03 — Real Retrieval Upgrade

> **Git:** `facbc1d`

- Embedding provider config + factory
- DashScope text-embedding-v3 (1024-dim)
- Retrieval comparison metrics (real vs fake)

---

## [0.7.0] — 2026-06-02 — Evidence Pack Scale-Up

> **Git:** `ef6a3b0`

- Evaluation dataset + knowledge base expansion
- 7 demo scenarios + limitations doc

---

## [0.6.0] — 2026-06-01 — Agent Kernel Runtime

> **Git:** `b99e5ec`

- Agent schemas + trace events + tool registry
- Deterministic agent planner + loop
- Runtime skill loader + full integration tests

---

## [0.5.0] — 2026-05-30 — Public GitHub Package

> **Git:** `c58c769`

- Public README + demo guide + release checklist + MIT License

---

## [0.4.0] — 2026-05-28 — Evaluation Pipeline

> **Git:** `165a279`

- 101 synthetic eval tickets + metric computation + offline CLI

---

## [0.3.0] — 2026-05-25 — Human Review Console

> **Git:** `def4afa`

- Review schema + JSONL store + Streamlit MVP

---

## [0.2.0] — 2026-05-20 — Evidence Drafting

> **Git:** `afa8885`

- Evidence-grounded drafting + pipeline entrypoint

---

## [0.1.0] — 2026-04-29 — Project Init + Audit

> **Git:** `9738f37`

- Project scaffold + OpenSpec workflow + audit fixes

---

## 关键指标演变

| 日期 | Tests | 知识库 Chunks | 评测工单 | 综合分 |
|------|-------|--------------|---------|--------|
| 2026-04 | ~50 | 0 | 0 | — |
| 2026-05 | ~400 | 0 | 101 | — |
| 2026-06-02 | ~700 | 340 | 101 | — |
| 2026-06-03 | ~800 | 1,505 | 101 | — |
| 2026-06-10 | 1,574 | 1,505 | 101 | 0.6125 |
| 2026-06-11 | 1,628 | 1,505 | ~400 | 0.6255 |
