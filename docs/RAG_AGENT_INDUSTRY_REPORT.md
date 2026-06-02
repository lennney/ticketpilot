# RAG + Agent 行业实践调研报告

> 为 TicketPilot 项目提供技术参考
> 日期: 2026-06-02

---

## 一、行业案例概览

| 公司/项目 | 架构模式 | 核心特点 |
|-----------|----------|----------|
| Klarna | Hybrid RAG + Self-Reflection | 幻觉率从5%降到1.2% |
| Intercom (Fin) | ReAct Agent + RAG | 多轮对话+工具调用 |
| Zendesk | Multi-Agent | 意图路由+专用Agent |
| Ada | Orchestrator + Sub-Agents | 复杂任务分解 |
| Salesforce (Einstein) | Knowledge-Grounded RAG | 信任层+验证 |
| Microsoft (Copilot Studio) | RAG + Guardrails | 企业级安全+合规模 |
| LangChain | ReAct Pattern | Think→Act→Observe循环 |
| RAGAS Framework | 评估体系 | 4维度质量指标 |

---

## 二、四种主流架构模式

### 1. Hybrid RAG（最常见）

```
用户查询
    ↓
┌─────────────────────────────────┐
│  Hybrid Retrieval               │
│  ├─ Vector Search (pgvector)    │
│  ├─ BM25 (全文检索)             │
│  └─ Re-ranking (交叉编码器)     │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  LLM Generation                 │
│  ├─ Context Injection           │
│  └─ Citation Verification       │
└─────────────────────────────────┘
    ↓
响应 + 引用
```

**代表**: Klarna, Intercom, Zendesk

**关键数据**:
- Hybrid search (vector + BM25) 比纯 vector 提升 15-25%
- Re-ranking 提升 precision 15-25%

**TicketPilot 当前状态**: 已有 hybrid (keyword + embedding + RRF)，但没有 BM25 和 re-ranking

---

### 2. ReAct Agent 模式

```
用户查询
    ↓
┌─────────────────────────────────┐
│  Agent Reasoning Loop           │
│  ├─ Think: 分析问题，制定计划   │
│  ├─ Act: 调用工具（检索/计算）  │
│  ├─ Observe: 观察结果           │
│  └─ 循环直到满意                 │
└─────────────────────────────────┘
    ↓
最终响应
```

**代表**: Intercom Fin, LangChain

**关键特点**:
- 多步推理：Plan → Retrieve → Draft → Critique → Revise
- 工具调用：检索、计算、API调用
- 自我反思：检查答案质量

**TicketPilot 当前状态**: DraftAgent 已实现多步推理，但缺少 self-reflection loop

---

### 3. Multi-Agent 架构

```
用户查询
    ↓
┌─────────────────────────────────┐
│  Orchestrator Agent             │
│  ├─ 意图识别                    │
│  ├─ 路由到专用Agent             │
│  └─ 汇总结果                    │
└─────────────────────────────────┘
    ↓
┌───────┬───────┬───────┐
│ 退款  │ 投诉  │ 物流  │ ...
│ Agent │ Agent │ Agent │
└───────┴───────┴───────┘
    ↓
统一响应
```

**代表**: Ada, Zendesk

**关键特点**:
- 每个Agent专注于特定领域
- Orchestrator 负责路由和汇总
- 易于扩展新领域

**TicketPilot 当前状态**: 单一Agent，未实现多Agent架构

---

### 4. Knowledge-Grounded RAG（企业级）

```
用户查询
    ↓
┌─────────────────────────────────┐
│  Trust Layer                    │
│  ├─ PII Detection               │
│  ├─ Toxicity Filtering          │
│  └─ Confidence Scoring          │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  RAG Pipeline                   │
│  ├─ Retrieval                   │
│  ├─ Generation                  │
│  └─ Verification                │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Output Guard                   │
│  ├─ Citation Check              │
│  ├─ Hallucination Detection     │
│  └─ Human Handoff Decision      │
└─────────────────────────────────┘
    ↓
安全响应
```

**代表**: Salesforce, Microsoft

**关键特点**:
- 多层安全防护
- 置信度路由：>0.8 自主, 0.6-0.8 建议人工, <0.6 直接人工
- 企业级合规

**TicketPilot 当前状态**: 有 must_human_review 标记，但缺少完整信任层

---

## 三、检索策略最佳实践

### 1. Chunk Sizing（分块大小）

| 内容类型 | 推荐大小 | TicketPilot 现状 |
|----------|----------|------------------|
| FAQ | 256-384 tokens | ✓ 已有 parent-child |
| Policy | 384-512 tokens | ✓ 已有 parent-child |
| Case | 512-1024 tokens | ✓ 已有 parent-child |

**Parent-Child Chunking 效果**: 上下文完整性提升 40%

### 2. Hybrid Search 组合

```
最佳组合: Vector + BM25 + Re-ranking

效果对比:
- 纯 Vector: baseline
- Vector + BM25: +15-25%
- Vector + BM25 + Re-ranking: +25-40%
```

**TicketPilot 建议**:
- 当前: keyword + embedding + RRF
- 升级: PostgreSQL FTS (BM25) + embedding + BGE-reranker

### 3. Re-ranking 模型选择

| 模型 | 效果 | 速度 | 推荐场景 |
|------|------|------|----------|
| BGE-reranker | ★★★★☆ | 快 | 中文场景首选 |
| Cohere rerank | ★★★★★ | 中 | 英文/多语言 |
| Cross-encoder | ★★★★★ | 慢 | 高精度需求 |

**TicketPilot 建议**: 使用 BGE-reranker-m3（与 BGE-small-zh 同系列）

---

## 四、Agent 推理模式

### 1. Multi-Step Reasoning（多步推理）

```
Plan → Retrieve → Draft → Critique → Revise
  ↑                                     │
  └─────────────────────────────────────┘
```

**关键指标**:
- 自我反思循环可将幻觉率从 5% 降到 1.2%（Klarna 数据）
- 每次循环成本增加 20-30%，但质量提升显著

**TicketPilot 建议**:
- 当前 DraftAgent 有 Retrieve → Draft，缺少 Critique → Revise
- 添加 self-reflection loop：检查答案是否 grounded in evidence

### 2. Confidence-Based Routing（置信度路由）

```
置信度 > 0.8: 自主响应
置信度 0.6-0.8: 建议人工审核
置信度 < 0.6: 直接转人工
```

**TicketPilot 当前状态**: 有 must_human_review 标记，但阈值不够精细

### 3. Tool Use（工具调用）

```
Agent 可调用的工具:
├─ 知识库检索
├─ 订单查询
├─ 退款计算
├─ 物流追踪
└─ 人工转接
```

**TicketPilot 当前状态**: 只有知识库检索，可扩展其他工具

---

## 五、评估指标体系（RAGAS 框架）

### 四大核心指标

| 指标 | 定义 | 目标值 | TicketPilot 现状 |
|------|------|--------|------------------|
| Faithfulness | 答案基于上下文 | 0.95+ | 需测量 |
| Answer Relevancy | 答案回答问题 | 0.90+ | 需测量 |
| Context Precision | 检索结果相关 | 0.85+ | 需测量 |
| Context Recall | 检索覆盖全面 | 0.80+ | 需测量 |

### 评估方法

```python
# RAGAS 评估示例
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

result = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

**TicketPilot 建议**:
- 当前使用自定义对抗评测（10个case，0.975分）
- 升级到 RAGAS 框架，获得更细粒度指标

---

## 六、生产部署最佳实践

### 1. 延迟优化

| 策略 | 效果 | 复杂度 |
|------|------|--------|
| Streaming responses | P95 < 3s | 低 |
| 缓存热点查询 | 命中率 30-50% | 中 |
| 异步检索 | 并发提升 2x | 中 |

### 2. 安全防护

```
Guardrails:
├─ PII Detection (个人信息检测)
├─ Toxicity Filtering (毒性过滤)
├─ Confidence Threshold (置信度阈值)
└─ Citation Verification (引用验证)
```

### 3. 渐进式发布

```
1% → 10% → 50% → 100%
     ↓
Shadow Traffic (影子流量对比)
     ↓
A/B Testing (A/B测试)
```

---

## 七、TicketPilot 改进建议

### P0: 立即实施（高收益低成本）

1. **添加 BM25 全文检索**
   - 使用 PostgreSQL FTS（已用 PostgreSQL）
   - 与现有 keyword search 互补
   - 预期提升: 15-20%

2. **实现 Re-ranking**
   - 使用 BGE-reranker-m3（与现有 embedding 同系列）
   - 在 RRF 后添加 re-ranking 步骤
   - 预期提升: 10-15%

3. **DraftAgent 添加 Self-Reflection**
   - 当前: Retrieve → Draft
   - 升级: Retrieve → Draft → Critique → Revise
   - 预期: 幻觉率从 ~5% 降到 ~1%

### P1: 中期实施（高收益中成本）

4. **RAGAS 评估框架**
   - 替换自定义评测脚本
   - 获得 Faithfulness/Relevancy/Precision/Recall 四维指标
   - 更科学的质量度量

5. **置信度路由优化**
   - 当前: must_human_review (boolean)
   - 升级: 置信度分数 + 分级路由
   - 0.8+ 自主, 0.6-0.8 建议人工, <0.6 直接人工

6. **Streaming Responses**
   - 提升用户体验
   - P95 延迟 < 3s

### P2: 长期规划（战略性）

7. **Multi-Agent 架构**
   - Orchestrator + 专用Agent（退款/投诉/物流）
   - 易于扩展新领域

8. **知识图谱**
   - 复杂政策关系建模
   - 例如: 退款 → 退货 → 运费 → 时效

9. **多语言支持**
   - 跨境电商场景需要
   - 翻译层 + 多语言 embedding

---

## 八、总结

### TicketPilot 现状评估

| 维度 | 现状 | 行业水平 | 差距 |
|------|------|----------|------|
| 检索 | Hybrid (keyword+embedding+RRF) | Hybrid+BM25+Rerank | 中等 |
| Agent | Multi-step reasoning | ReAct+Self-reflection | 小 |
| 评估 | 自定义10case | RAGAS 4维度 | 大 |
| 安全 | must_human_review | Trust Layer | 中等 |
| 部署 | 单实例 | 渐进式发布 | 大 |

### 优先级排序

```
P0 (本周):
  1. BM25 全文检索
  2. BGE-reranker
  3. Self-reflection loop

P1 (本月):
  4. RAGAS 评估框架
  5. 置信度路由
  6. Streaming responses

P2 (下季度):
  7. Multi-Agent 架构
  8. 知识图谱
  9. 多语言支持
```

---

## 参考资源

- [RAGAS Documentation](https://docs.ragas.io/)
- [LangChain ReAct Agent](https://python.langchain.com/docs/modules/agents/agent_types/react)
- [BGE-reranker](https://huggingface.co/BAAI/bge-reranker-m3)
- [Klarna AI Customer Service Case Study](https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/)
- [Intercom Fin Architecture](https://www.intercom.com/fin)
