# TicketPilot 改进计划

> 2026-06-07 | 基于深度审计，PM 视角优先级排序

---

## 现状总结

**16,050 行 Python | 40 模块 | 1,356 测试全通过 | 0 LLM 调用**

### 已有的差异化特性

| 特性 | 竞品通常怎么做 | TicketPilot 怎么做 |
|------|---------------|-------------------|
| 置信度评分 | 二元（有信心/没信心） | 4维加权：retrieval+classification+citation+evidence_density |
| 降级路由 | 全自动或全人工 | 4级：AUTO_SEND / AUTO_SEND_CAUTIOUS / HUMAN_REVIEW / HUMAN_ESCALATION |
| Claim Guard | 无或简单关键词 | 8类禁止承诺检测（退款金额、赔偿、法律威胁等） |
| 检索 | 简单向量检索 | keyword FTS + vector HNSW → RRF fusion，每步有 trace |
| 全链路追溯 | 无 | answer→citation→chunk→document，RetrievalTrace + ClaimProvenance |
| Agent Trace | 无 | append-only 事件流，TOOL_CALLED/TOOL_RETURNED 级别 |
| Multi-Agent | 单一 Agent | 意图路由到专业 Agent（退款/投诉/物流/技术） |
| Pipeline 确定性 | 依赖 LLM | 全流程规则驱动，无 LLM 调用 |

### 评估体系

| 模块 | 能力 |
|------|------|
| agent_eval.py | RAGAS-style: faithfulness, relevancy, intent accuracy |
| retrieval_metrics.py | Precision@K, Recall@K, MRR, NDCG |
| retrieval_comparison.py | 多检索策略 A/B 对比 |
| metrics.py | Pipeline 级指标 |
| reporting.py | JSON + Markdown 报告生成 |

---

## 短板分析

### 1. Multi-Agent 是假的多 Agent

**问题**：5 个 Specialist（RefundAgent, ComplaintAgent, LogisticsAgent, TechnicalAgent, DefaultAgent）全部调同一个 `_draft_agent.generate_draft()`，没有任何差异化。

**影响**：面试时被追问"你的多 Agent 有什么不同"会露馅。

**改进**：每个 Agent 用不同 prompt template + 不同 guard 规则：
- ComplaintAgent：加情绪安抚话术，强制 must_human_review=True（已有）
- RefundAgent：加退款流程引导，引用退款政策
- LogisticsAgent：加物流状态查询模板
- TechnicalAgent：加故障排查步骤模板

**工作量**：2-3 小时 | **面试价值**：高

### 2. 没有 Feedback Loop

**问题**：人工审后 accept/reject/edit 的结果没有回流到系统。置信度阈值是静态的（0.4/0.6/0.8），无法根据实际表现校准。

**影响**：无法讲"闭环优化"的故事。

**改进**：
- ReviewDecision 已有 accept/reject/edit action（review/schemas.py）
- 加 FeedbackCollector：统计每个置信度区间的实际 accept rate
- 加 CalibrationCurve：predicted confidence vs actual accuracy
- 用历史数据自动调整阈值

**工作量**：3-4 小时 | **面试价值**：极高（"数据驱动的闭环优化"）

### 3. 没有 A/B 实验框架

**问题**：有 retrieval comparison（检索策略对比），但没有 pipeline 级 A/B（不同 prompt / 不同 guard 规则 / 不同置信度阈值对比）。

**影响**：无法讲"科学实验驱动迭代"的故事。

**改进**：
- 加 ExperimentConfig：定义实验组和对照组的配置差异
- 加 ExperimentRunner：同一组 ticket 跑两套配置
- 加 ExperimentReport：输出对比表（accuracy, accept rate, avg confidence, latency）
- 支持 retrieval comparison 已有的 pattern 扩展到 pipeline 级

**工作量**：2-3 小时 | **面试价值**：高（"A/B 测试文化"）

### 4. 评估指标是 keyword overlap，不是真正的 RAGAS

**问题**：`compute_faithfulness()` 和 `compute_relevancy()` 用词重叠（set intersection）代替语义相似度。置信度区间被压缩到 0.5-1.0。

**影响**：评估结果不够准确，无法区分"换了一种说法但意思一样"和"完全跑题"。

**改进**：
- 短期：加 NLI-based faithfulness（用 sentence-transformers 做 entailment 检测）
- 中期：加 LLM-based faithfulness（可选，用 MIMO API）
- 保持 keyword overlap 作为 fallback（离线可用）

**工作量**：3-4 小时 | **面试价值**：中（技术深度）

### 5. 没有置信度校准（Calibrator）

**问题**：置信度分数是原始加权值，没有校准。predicted confidence = 0.7 不代表实际 70% 的准确率。

**影响**：降级路由的阈值不可靠。

**改进**：
- 加 CalibrationCurve：收集 (predicted_confidence, actual_correct) 对
- 加 ReliabilityDiagram：可视化校准效果
- 加 IsotonicRegression：用历史数据拟合校准函数
- 集成到 ConfidenceScorer：校准后再输出

**工作量**：2-3 小时 | **面试价值**：高（"置信度校准"是 ML 系统标配）

### 6. RetrievalTrace 有但没可视化

**问题**：RetrievalTrace 存了 keyword_results, vector_results, fused_results 每步的 rank/score/contribution，但没有 UI 展示。

**影响**：调试时只能看 JSON，不直观。

**改进**：
- Streamlit 新页面：展示检索链路
- 桑基图：keyword contribution vs vector contribution
- 表格：每个 chunk 的 RRF 分解（keyword_rank, vector_rank, rrf_score）
- 对比视图：同一 query 不同检索策略的结果差异

**工作量**：2-3 小时 | **面试价值**：中（demo 效果好）

---

## 优先级排序

按 PM 视角：面试价值 × 执行难度

| 优先级 | 改进项 | 面试价值 | 工作量 | 一句话故事 |
|--------|--------|---------|--------|-----------|
| **P0** | Feedback Loop | ⭐⭐⭐⭐⭐ | 3-4h | "人工审后数据回流，自动校准置信度阈值" |
| **P0** | Multi-Agent 真实化 | ⭐⭐⭐⭐ | 2-3h | "不同意图用不同 prompt 和 guard 规则" |
| **P1** | A/B 实验框架 | ⭐⭐⭐⭐ | 2-3h | "同一组 ticket 跑不同配置，数据驱动决策" |
| **P1** | 置信度校准 | ⭐⭐⭐⭐ | 2-3h | "predicted confidence = actual accuracy" |
| **P2** | 评估指标升级 | ⭐⭐⭐ | 3-4h | "NLI-based faithfulness，不只是词重叠" |
| **P2** | RetrievalTrace 可视化 | ⭐⭐⭐ | 2-3h | "检索链路桑基图，调试一目了然" |

**总工作量**：14-20 小时

---

## 建议执行顺序

```
Phase 1: P0（5-7h）
  ├── Multi-Agent 真实化（不同 prompt + guard）
  └── Feedback Loop（accept/reject 回流 + 阈值校准）

Phase 2: P1（4-6h）
  ├── A/B 实验框架（ExperimentRunner + 对比报告）
  └── 置信度校准（CalibrationCurve + ReliabilityDiagram）

Phase 3: P2（5-7h）
  ├── 评估指标升级（NLI-based faithfulness）
  └── RetrievalTrace 可视化（Streamlit 桑基图）
```

---

## 面试话术框架

每个改进对应一个 PM 故事：

| 改进 | 机会发现 | 产品决策 | 业务指标 |
|------|---------|---------|---------|
| Feedback Loop | "人工审后数据没回流，置信度阈值靠拍脑袋" | "加 accept/reject 回流，自动校准" | "accept rate 从 X% 提升到 Y%" |
| Multi-Agent | "5个Agent用同一套逻辑，没有差异化价值" | "按意图定制 prompt 和 guard 规则" | "投诉场景人工干预率降低 Z%" |
| A/B 实验 | "改了 prompt 不知道好不好，靠感觉" | "加实验框架，同组 ticket 跑两套配置" | "实验组 accuracy 提升 N%" |
| 置信度校准 | "0.7 置信度不代表 70% 准确率" | "加 isotonic regression 校准" | "降级路由误判率降低 M%" |
